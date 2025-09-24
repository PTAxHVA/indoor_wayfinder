from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from rapidfuzz import fuzz, process
from backend.core.db import engine
from backend.models.entities import Alias, Node
from backend.utils.norm import normalize_name

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


class AliasIn(BaseModel):
    node_id: int
    name: str
    lang: str = "vi"
    weight: float = 1.0
    generated: bool = False


class AliasOut(BaseModel):
    id: int
    node_id: int
    name: str
    norm_name: str
    lang: str
    weight: float
    generated: bool


@router.post("", response_model=AliasOut)
def create_alias(payload: AliasIn, session: Session = Depends(get_session)):
    n = session.get(Node, payload.node_id)
    if not n:
        raise HTTPException(status_code=404, detail="Node không tồn tại.")
    norm = normalize_name(payload.name)
    a = Alias(
        node_id=payload.node_id,
        name=payload.name,
        norm_name=norm,
        lang=payload.lang,
        weight=payload.weight,
        generated=payload.generated,
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return AliasOut(**a.dict())


@router.get("", response_model=List[AliasOut])
def list_aliases(node_id: Optional[int] = None, session: Session = Depends(get_session)):
    q = select(Alias)
    if node_id:
        q = q.where(Alias.node_id == node_id)
    items = session.exec(q).all()
    return [AliasOut(**a.dict()) for a in items]


@router.delete("/{alias_id}", response_model=dict)
def delete_alias(alias_id: int, session: Session = Depends(get_session)):
    a = session.get(Alias, alias_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alias không tồn tại.")
    session.delete(a)
    session.commit()
    return {"ok": True}


# ---- SEARCH ----


class AliasSearchOut(BaseModel):
    node_id: int
    alias_id: int
    name: str
    score: float


@router.get("/search", response_model=List[AliasSearchOut])
def search_alias(
    q: str = Query(..., description="Tên cần tìm"),
    limit: int = 5,
    session: Session = Depends(get_session),
):
    # guard
    if not q or not q.strip():
        return []
    norm_q = normalize_name(q)
    if not norm_q:
        return []

    items: List[Alias] = session.exec(select(Alias)).all()
    if not items:
        return []

    # Chuẩn bị map id -> tên đã chuẩn hoá để fuzzy
    norm_map = {a.id: normalize_name(a.name) for a in items}
    items_by_id = {a.id: a for a in items}

    # RapidFuzz trả (choice_value, score, choice_key) khi choices là dict
    results = process.extract(norm_q, norm_map, scorer=fuzz.token_set_ratio, limit=limit)

    out: List[AliasSearchOut] = []
    for choice_value, score, choice_key in results:
        a = items_by_id.get(choice_key)
        if a is None:
            # fallback cực đoan (đề phòng lib khác version) — bỏ qua nếu không khớp
            continue
        out.append(
            AliasSearchOut(
                node_id=a.node_id, alias_id=a.id, name=a.name, score=float(score)
            )
        )
    return out
