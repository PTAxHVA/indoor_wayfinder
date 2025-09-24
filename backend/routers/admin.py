from typing import Optional
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import delete as sa_delete

from backend.core.db import engine
from backend.models.entities import Map, Node, Alias, Edge

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


class ClearMapIn(BaseModel):
    map_id: int
    delete_map: bool = False  # nếu True: xóa luôn bản ghi Map
    delete_upload: bool = False  # nếu True: xóa luôn file ảnh map trên đĩa


@router.post("/clear-map", response_model=dict)
def clear_map(payload: ClearMapIn, session: Session = Depends(get_session)):
    m = session.get(Map, payload.map_id)
    if not m:
        raise HTTPException(status_code=404, detail="Map không tồn tại.")

    # lấy danh sách node_id thuộc map
    nodes = session.exec(select(Node).where(Node.map_id == m.id)).all()
    node_ids = [n.id for n in nodes]

    # 1) delete aliases theo node_ids (nếu có)
    deleted_aliases = 0
    if node_ids:
        res = session.exec(sa_delete(Alias).where(Alias.node_id.in_(node_ids)))
        deleted_aliases = res.rowcount or 0

    # 2) delete edges theo map_id
    res_e = session.exec(sa_delete(Edge).where(Edge.map_id == m.id))
    deleted_edges = res_e.rowcount or 0

    # 3) delete nodes theo map_id
    res_n = session.exec(sa_delete(Node).where(Node.map_id == m.id))
    deleted_nodes = res_n.rowcount or 0

    deleted_map = False
    removed_file = False

    # 4) xóa map (tùy chọn)
    if payload.delete_map:
        # lưu đường dẫn trước khi xóa để có thể remove file
        img_path = m.image_path
        session.exec(sa_delete(Map).where(Map.id == m.id))
        deleted_map = True
        # xóa file (tùy chọn)
        if payload.delete_upload and img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
                removed_file = True
            except Exception:
                removed_file = False

    session.commit()

    return {
        "ok": True,
        "deleted": {
            "aliases": deleted_aliases,
            "edges": deleted_edges,
            "nodes": deleted_nodes,
            "map": deleted_map,
            "upload_removed": removed_file,
        },
    }
