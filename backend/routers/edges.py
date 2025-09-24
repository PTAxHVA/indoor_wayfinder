from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session, select
import json

from backend.core.db import engine
from backend.models.entities import Edge, Map, Node, EdgeBase
from backend.utils.geo import polyline_length

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


class EdgeIn(EdgeBase):
    pass


class EdgeOut(EdgeBase):
    id: int
    floor: int
    polyline: List[List[float]]
    weight: float


@router.post("", response_model=EdgeOut)
def create_edge(payload: EdgeIn, session: Session = Depends(get_session)):
    # validate map & nodes
    m = session.get(Map, payload.map_id)
    if not m:
        raise HTTPException(status_code=404, detail="Map không tồn tại.")
    s = session.get(Node, payload.start_node_id)
    e = session.get(Node, payload.end_node_id)
    if not s or not e or s.map_id != m.id or e.map_id != m.id:
        raise HTTPException(status_code=400, detail="Node không hợp lệ hoặc khác map.")

    # Xác định floor:
    # - Nếu payload.floor có -> phải khớp với cả 2 node
    # - Nếu không -> lấy theo node start, và kiểm tra end cùng tầng
    if payload.floor is not None:
        floor = int(payload.floor)
        if s.floor != floor or e.floor != floor:
            raise HTTPException(
                status_code=400,
                detail=f"Floor không khớp: start({s.floor})/end({e.floor}) ≠ payload({floor}).",
            )
    else:
        if s.floor != e.floor:
            raise HTTPException(
                status_code=400,
                detail=f"Hai node không cùng tầng: start({s.floor}) vs end({e.floor}).",
            )
        floor = int(s.floor)

    # Nếu polyline rỗng, tự tạo đoạn thẳng từ (s) tới (e)
    poly = payload.polyline or []
    if len(poly) < 2:
        poly = [[s.x, s.y], [e.x, e.y]]

    # tính trọng số theo pixel
    w = polyline_length(poly)

    edge = Edge(
        map_id=m.id,
        start_node_id=s.id,
        end_node_id=e.id,
        floor=floor,
        polyline=json.dumps(poly),
        weight=w,
        bidirectional=payload.bidirectional,
        meta=payload.meta,
    )
    session.add(edge)
    session.commit()
    session.refresh(edge)

    return EdgeOut(
        id=edge.id,
        map_id=edge.map_id,
        start_node_id=edge.start_node_id,
        end_node_id=edge.end_node_id,
        floor=edge.floor,  # <<<<<< THÊM
        polyline=json.loads(edge.polyline),
        weight=edge.weight,
        bidirectional=edge.bidirectional,
        meta=edge.meta,
    )


@router.get("", response_model=List[EdgeOut])
def list_edges(
    map_id: int, floor: Optional[int] = None, session: Session = Depends(get_session)
):
    stmt = select(Edge).where(Edge.map_id == map_id)
    if floor is not None:
        stmt = stmt.where(Edge.floor == floor)
    edges = session.exec(stmt).all()

    return [
        EdgeOut(
            id=edge.id,
            map_id=edge.map_id,
            start_node_id=edge.start_node_id,
            end_node_id=edge.end_node_id,
            floor=edge.floor,
            polyline=json.loads(edge.polyline),
            weight=edge.weight,
            bidirectional=edge.bidirectional,
            meta=edge.meta,
        )
        for edge in edges
    ]


class EdgeUpdate(BaseModel):
    polyline: Optional[List[List[float]]] = None
    bidirectional: Optional[bool] = None
    meta: Optional[str] = None


@router.patch("/{edge_id}", response_model=EdgeOut)
def update_edge(
    edge_id: int, payload: EdgeUpdate, session: Session = Depends(get_session)
):
    ed = session.get(Edge, edge_id)
    if not ed:
        raise HTTPException(status_code=404, detail="Edge không tồn tại.")

    changed = False
    if payload.polyline is not None:
        if len(payload.polyline) < 2:
            raise HTTPException(status_code=400, detail="Polyline cần >= 2 điểm.")
        ed.polyline = json.dumps(payload.polyline)
        ed.weight = polyline_length(payload.polyline)
        changed = True
    if payload.bidirectional is not None:
        ed.bidirectional = payload.bidirectional
        changed = True
    if payload.meta is not None:
        ed.meta = payload.meta
        changed = True

    if changed:
        session.add(ed)
        session.commit()
        session.refresh(ed)

    return EdgeOut(
        id=ed.id,
        map_id=ed.map_id,
        start_node_id=ed.start_node_id,
        end_node_id=ed.end_node_id,
        floor=ed.floor,
        polyline=json.loads(ed.polyline),
        weight=ed.weight,
        bidirectional=ed.bidirectional,
        meta=ed.meta,
    )


@router.delete("/{edge_id}", response_model=dict)
def delete_edge(edge_id: int, session: Session = Depends(get_session)):
    ed = session.get(Edge, edge_id)
    if not ed:
        raise HTTPException(status_code=404, detail="Edge không tồn tại.")
    session.delete(ed)
    session.commit()
    return {"ok": True}
