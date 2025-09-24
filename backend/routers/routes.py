from typing import List, Optional, Dict, Tuple
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select
import networkx as nx

from backend.core.db import engine
from backend.models.entities import Map, Node, Alias
from backend.services.graph import build_graph_for_map
from backend.utils.geo import (
    merge_polylines,
    polyline_length,
    angle_signed,
    signed_turn_angle_screen,
    polyline_length,
    merge_polys_with_tol,
    orient_polyline_to_uv,
    initial_heading_text_from_angle,
    heading_angle_from_polyline,
    dedupe_polyline,
)
from backend.utils.nlp import extract_a_b
from backend.utils.norm import normalize_name
from rapidfuzz import process, fuzz
import math

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


# ------- Models -------


class RouteRequest(BaseModel):
    map_id: int
    start_id: Optional[int] = None
    end_id: Optional[int] = None
    # Nếu không có start/end, có thể truyền câu q + (cx, cy) để xác định "điểm của tôi"
    q: Optional[str] = None
    cx: Optional[float] = None
    cy: Optional[float] = None


class Instruction(BaseModel):
    kind: str  # "straight" | "left" | "right"
    text: str
    at_index: int  # index trong polyline hợp nhất (điểm "rẽ")
    distance_px: float


class RouteResponse(BaseModel):
    path_node_ids: List[int]
    polyline: List[List[float]]
    length_px: float
    instructions: List[Instruction]


# ------- Helpers -------


def best_alias_for_node(session: Session, node_id: int) -> str:
    als = session.exec(select(Alias).where(Alias.node_id == node_id)).all()
    if not als:
        return f"điểm #{node_id}"
    als.sort(key=lambda a: (-a.weight, a.id))
    return als[0].name


def find_best_alias_node(
    session: Session,
    map_id: int,
    query: str,
    cx: Optional[float] = None,
    cy: Optional[float] = None,
) -> Optional[int]:
    """Tìm node_id theo tên (alias) gần đúng. Nếu trùng nhiều node, ưu tiên gần (cx,cy)."""
    norm_q = normalize_name(query)
    aliases = session.exec(
        select(Alias, Node).where(Alias.node_id == Node.id).where(Node.map_id == map_id)
    ).all()
    if not aliases:
        return None

    # id -> tên chuẩn hoá; và map id -> (Alias, Node)
    choices = {a.id: normalize_name(a.name) for (a, _n) in aliases}
    by_id = {a.id: (a, n) for (a, n) in aliases}

    # RapidFuzz tuple: (choice_value, score, choice_key)
    best = process.extract(norm_q, choices, scorer=fuzz.token_set_ratio, limit=5)
    cand = []
    for choice_value, score, choice_key in best:
        pair = by_id.get(choice_key)
        if pair:
            _a, n = pair
            cand.append((n, score))

    if not cand:
        return None

    # Nếu có vị trí (cx,cy), ưu tiên node gần nhất
    import math as _math

    if cx is not None and cy is not None:
        cand.sort(key=lambda t: _math.hypot(t[0].x - cx, t[0].y - cy))
        return cand[0][0].id

    # Ngược lại chọn score cao nhất
    cand.sort(key=lambda t: (-t[1], t[0].id))
    return cand[0][0].id


def turn_text(angle: float, thresh: float = 25.0):
    if angle > +thresh:
        return ("right", "rẽ phải")
    elif angle < -thresh:
        return ("left", "rẽ trái")
    else:
        return ("straight", "đi thẳng")


def nearest_landmark_name(
    session: Session, map_id: int, x: float, y: float, radius: float = 80.0
) -> Optional[str]:
    """Tìm landmark gần 1 điểm. Trả tên alias 'đẹp' nhất nếu có."""
    nodes = session.exec(
        select(Node).where(Node.map_id == map_id).where(Node.is_landmark == True)
    ).all()
    best = None
    best_d = None
    for n in nodes:
        d = math.hypot(n.x - x, n.y - y)
        if d <= radius and (best is None or d < best_d):
            best = n
            best_d = d
    if not best:
        return None
    # lấy alias có weight cao nhất
    aliases = session.exec(select(Alias).where(Alias.node_id == best.id)).all()
    if not aliases:
        return f"điểm {best.id}"
    aliases.sort(key=lambda a: (-a.weight, a.id))
    return aliases[0].name


def build_instructions(
    session: Session,
    map_id: int,
    merged: List[List[float]],
    start_id: Optional[int] = None,
    end_id: Optional[int] = None,
) -> List[Instruction]:
    instr: List[Instruction] = []

    # --- Start ---
    if start_id is not None:
        start_name = best_alias_for_node(session, start_id)
        instr.append(
            Instruction(
                kind="start",
                text=f"Bắt đầu tại {start_name}",
                at_index=0,
                distance_px=0.0,
            )
        )
    else:
        instr.append(
            Instruction(kind="start", text="Bắt đầu", at_index=0, distance_px=0.0)
        )

    # Không đủ điểm để xác định hướng
    if len(merged) < 2:
        # Arrive luôn nếu có
        if end_id is not None:
            dest_name = best_alias_for_node(session, end_id)
            instr.append(
                Instruction(
                    kind="arrive", text=f"Đã đến {dest_name}", at_index=0, distance_px=0.0
                )
            )
        else:
            instr.append(
                Instruction(
                    kind="arrive", text="Đã đến điểm đích", at_index=0, distance_px=0.0
                )
            )
        return instr

    # --- Initial heading (mượt, tích lũy >= 25 px) ---
    ang = heading_angle_from_polyline(
        [(float(x), float(y)) for x, y in merged], min_dist=25.0
    )
    heading_txt = initial_heading_text_from_angle(ang)
    instr.append(
        Instruction(
            kind="heading",
            text=f"Hướng ban đầu của bạn là {heading_txt}",
            at_index=1,
            distance_px=0.0,
        )
    )

    # Nếu chỉ có 2 điểm => đi thẳng là xong
    if len(merged) == 2:
        total = polyline_length(merged)
        instr.append(
            Instruction(
                kind="straight",
                text=f"Đi thẳng {int(total)} px",
                at_index=1,
                distance_px=total,
            )
        )
        dest_name = (
            best_alias_for_node(session, end_id) if end_id is not None else "điểm đích"
        )
        instr.append(
            Instruction(
                kind="arrive", text=f"Đã đến {dest_name}", at_index=1, distance_px=0.0
            )
        )
        return instr

    # ---- Tuyến bình thường: tính rẽ trái/phải dựa trên hướng đang đi (giữa 2 đoạn liên tiếp) ----
    seg_len = [0.0]
    for i in range(1, len(merged)):
        d = math.hypot(merged[i][0] - merged[i - 1][0], merged[i][1] - merged[i - 1][1])
        seg_len.append(d)

    turns = []  # [{i, kind, phrase, lm}]
    for i in range(1, len(merged) - 1):
        a = signed_turn_angle_screen(
            tuple(merged[i - 1]), tuple(merged[i]), tuple(merged[i + 1])
        )
        kind, phrase = turn_text(a, thresh=25.0)  # dương = rẽ phải; âm = rẽ trái
        if kind == "straight":
            continue
        lm = nearest_landmark_name(session, map_id, merged[i][0], merged[i][1])
        turns.append({"i": i, "kind": kind, "phrase": phrase, "lm": lm})

    prev_idx = 0
    for t in turns:
        i = t["i"]
        dist_before = sum(seg_len[prev_idx + 1 : i + 1])
        lm_txt = f"gần {t['lm']}, " if t["lm"] else ""
        text = f"Đi thẳng {int(dist_before)} px, {lm_txt}{t['phrase']}".replace(
            ",  ", ", "
        )
        instr.append(
            Instruction(kind=t["kind"], text=text, at_index=i, distance_px=dist_before)
        )
        prev_idx = i

    # Đoạn thẳng cuối
    tail_dist = sum(seg_len[prev_idx + 1 : len(merged)])
    if tail_dist > 1e-6:
        instr.append(
            Instruction(
                kind="straight",
                text=f"Đi thẳng {int(tail_dist)} px",
                at_index=len(merged) - 1,
                distance_px=tail_dist,
            )
        )

    # --- Arrive ---
    dest_name = (
        best_alias_for_node(session, end_id) if end_id is not None else "điểm đích"
    )
    instr.append(
        Instruction(
            kind="arrive",
            text=f"Đã đến {dest_name}",
            at_index=len(merged) - 1,
            distance_px=0.0,
        )
    )

    return instr


def compute_route(
    session: Session, map_id: int, start_id: int, end_id: int
) -> RouteResponse:
    G, node_pos = build_graph_for_map(session, map_id)
    if start_id not in G.nodes or end_id not in G.nodes:
        raise HTTPException(
            status_code=400,
            detail="start_id hoặc end_id không thuộc map hoặc không tồn tại.",
        )

    try:
        path_nodes: List[int] = nx.shortest_path(
            G, source=start_id, target=end_id, weight="weight"
        )
    except nx.NetworkXNoPath:
        raise HTTPException(status_code=404, detail="Không có đường đi giữa hai điểm.")

    # Lấy polyline theo từng cạnh và ORIENT theo chiều u->v
    oriented_polys: List[List[List[float]]] = []
    for i in range(1, len(path_nodes)):
        u, v = path_nodes[i - 1], path_nodes[i]
        data = G.get_edge_data(u, v)
        if not data or "polyline" not in data:
            raise HTTPException(status_code=500, detail="Thiếu polyline trên cạnh.")
        raw = data["polyline"]  # [[x,y], ...]
        # Định hướng polyline theo node_pos[u] -> node_pos[v]
        u_pos = (float(node_pos[u][0]), float(node_pos[u][1]))
        v_pos = (float(node_pos[v][0]), float(node_pos[v][1]))
        oriented = orient_polyline_to_uv(
            [(float(x), float(y)) for x, y in raw], u_pos, v_pos
        )
        oriented_polys.append([[p[0], p[1]] for p in oriented])

    # Ghép có tolerance (tránh lệch 1-2 px)
    merged = merge_polys_with_tol(
        [[(x, y) for x, y in poly] for poly in oriented_polys], tol=1.5
    )
    merged = [[float(x), float(y)] for (x, y) in merged]

    merged = dedupe_polyline([(x, y) for x, y in merged], tol=1.0)
    merged = [[float(x), float(y)] for (x, y) in merged]

    total_len = polyline_length([(x, y) for x, y in merged])
    directions = build_instructions(
        session, map_id, merged, start_id=start_id, end_id=end_id
    )

    return RouteResponse(
        path_node_ids=path_nodes,
        polyline=merged,
        length_px=total_len,
        instructions=directions,
    )


# ------- Endpoints -------


@router.post("/route", response_model=RouteResponse)
def route_api(payload: RouteRequest, session: Session = Depends(get_session)):
    m = session.get(Map, payload.map_id)
    if not m:
        raise HTTPException(status_code=404, detail="Map không tồn tại.")

    # Nếu đã có start/end id => đi thẳng
    if payload.start_id and payload.end_id:
        return compute_route(session, payload.map_id, payload.start_id, payload.end_id)

    # Nếu không có, cho phép q + (cx,cy)
    if not payload.q:
        raise HTTPException(status_code=400, detail="Thiếu q hoặc start_id/end_id.")
    a_txt, b_txt = extract_a_b(payload.q)
    if b_txt is None and a_txt is None:
        raise HTTPException(
            status_code=400, detail="Không trích xuất được điểm đầu/cuối từ câu hỏi."
        )

    # Tìm node bắt đầu
    start_id = payload.start_id
    end_id = payload.end_id

    if start_id is None and a_txt:
        start_id = find_best_alias_node(
            session, payload.map_id, a_txt, payload.cx, payload.cy
        )
    if end_id is None and b_txt:
        end_id = find_best_alias_node(
            session, payload.map_id, b_txt, payload.cx, payload.cy
        )

    # Nếu chỉ có 'đến B' => cần cx,cy để chọn điểm gần nhất làm 'điểm của tôi'
    if start_id is None and a_txt is None:
        if payload.cx is None or payload.cy is None:
            raise HTTPException(
                status_code=400,
                detail="Cần cx,cy (vị trí của bạn) khi chỉ cung cấp điểm đích.",
            )
        # tạo node giả lập gần nhất (chọn node thật gần nhất làm start)
        nodes = session.exec(select(Node).where(Node.map_id == payload.map_id)).all()
        if not nodes:
            raise HTTPException(status_code=400, detail="Map chưa có node.")
        nodes.sort(key=lambda n: math.hypot(n.x - payload.cx, n.y - payload.cy))
        start_id = nodes[0].id

    if start_id is None or end_id is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm được node tương ứng với tên (có thể quá mơ hồ).",
        )

    return compute_route(session, payload.map_id, start_id, end_id)


@router.get("/nl-route", response_model=RouteResponse)
def nl_route(
    map_id: int = Query(...),
    q: str = Query(..., description="Câu hỏi: 'từ A đến B'..."),
    cx: Optional[float] = Query(None),
    cy: Optional[float] = Query(None),
    session: Session = Depends(get_session),
):
    payload = RouteRequest(map_id=map_id, q=q, cx=cx, cy=cy)
    return route_api(payload, session)
