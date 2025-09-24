import os, shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi import Depends
from PIL import Image
from sqlmodel import Session, select
from backend.core.db import engine
from backend.models.entities import Map

router = APIRouter()

UPLOAD_DIR = os.path.join("data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

BASE_STATIC = "/static/uploads"


def get_session():
    with Session(engine) as session:
        yield session


@router.post("", response_model=dict)
async def create_map(
    name: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    # validate mimetype
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
        raise HTTPException(status_code=400, detail="File phải là ảnh (png/jpg/webp).")

    # lưu tạm để đọc size
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    filename = f"map_{ts}{ext}"
    disk_path = os.path.join(UPLOAD_DIR, filename)

    with open(disk_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # đọc kích thước
    try:
        with Image.open(disk_path) as im:
            width, height = im.size
    except Exception:
        os.remove(disk_path)
        raise HTTPException(status_code=400, detail="Không đọc được ảnh.")

    # tạo bản ghi DB
    m = Map(name=name, image_path=disk_path, width=width, height=height)
    session.add(m)
    session.commit()
    session.refresh(m)

    return {
        "id": m.id,
        "name": m.name,
        "image_path": m.image_path,
        "image_url": f"{BASE_STATIC}/{os.path.basename(m.image_path)}",
        "width": m.width,
        "height": m.height,
        "created_at": m.created_at.isoformat() + "Z",
    }


@router.get("/{map_id}", response_model=dict)
def get_map(map_id: int, session: Session = Depends(get_session)):
    m = session.get(Map, map_id)
    if not m:
        raise HTTPException(status_code=404, detail="Map không tồn tại.")
    return {
        "id": m.id,
        "name": m.name,
        "image_path": m.image_path,
        "image_url": f"{BASE_STATIC}/{os.path.basename(m.image_path)}",
        "width": m.width,
        "height": m.height,
        "created_at": m.created_at.isoformat() + "Z",
    }


@router.get("", response_model=dict)
def list_maps(session: Session = Depends(get_session)):
    maps = session.exec(select(Map).order_by(Map.created_at.desc())).all()
    return {
        "items": [
            {
                "id": m.id,
                "name": m.name,
                "image_path": m.image_path,
                "image_url": f"{BASE_STATIC}/{os.path.basename(m.image_path)}",
                "width": m.width,
                "height": m.height,
                "created_at": m.created_at.isoformat() + "Z",
            }
            for m in maps
        ]
    }
