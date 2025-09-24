from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from backend.core.db import engine
from backend.models.entities import Node, Map

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


class NodeIn(BaseModel):
    map_id: int
    x: float
    y: float
    is_landmark: bool = False
    floor: int
    meta: Optional[str] = None  # JSON string nếu muốn


class NodeOut(BaseModel):
    id: int
    map_id: int
    x: float
    y: float
    is_landmark: bool
    floor: int
    meta: Optional[str]


@router.post("", response_model=NodeOut)
def create_node(payload: NodeIn, session: Session = Depends(get_session)):
    m = session.get(Map, payload.map_id)
    if not m:
        raise HTTPException(status_code=404, detail="Map không tồn tại.")
    n = Node(**payload.dict())
    session.add(n)
    session.commit()
    session.refresh(n)
    return NodeOut(**n.dict())


@router.get("", response_model=List[NodeOut])
def list_nodes(
    map_id: int, floor: Optional[int] = None, session: Session = Depends(get_session)
):
    stmt = select(Node).where(Node.map_id == map_id)
    if floor is not None:
        stmt = stmt.where(Node.floor == floor)
    return session.exec(stmt).all()


@router.get("/{node_id}", response_model=NodeOut)
def get_node(node_id: int, session: Session = Depends(get_session)):
    n = session.get(Node, node_id)
    if not n:
        raise HTTPException(status_code=404, detail="Node không tồn tại.")
    return NodeOut(**n.dict())


class NodeUpdate(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None
    is_landmark: Optional[bool] = None
    floor: Optional[str] = None
    meta: Optional[str] = None


@router.patch("/{node_id}", response_model=NodeOut)
def update_node(
    node_id: int, payload: NodeUpdate, session: Session = Depends(get_session)
):
    n = session.get(Node, node_id)
    if not n:
        raise HTTPException(status_code=404, detail="Node không tồn tại.")
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(n, k, v)
    session.add(n)
    session.commit()
    session.refresh(n)
    return NodeOut(**n.dict())


@router.delete("/{node_id}", response_model=dict)
def delete_node(node_id: int, session: Session = Depends(get_session)):
    n = session.get(Node, node_id)
    if not n:
        raise HTTPException(status_code=404, detail="Node không tồn tại.")
    session.delete(n)
    session.commit()
    return {"ok": True}
