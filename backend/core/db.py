from pathlib import Path
import os
from sqlmodel import create_engine, SQLModel

# Cho phép override bằng biến môi trường (tuỳ chọn)
ENV_URL = os.getenv("WAYFINDER_DB_URL") or os.getenv("DATABASE_URL")

if ENV_URL:
    DB_URL = ENV_URL
else:
    # db.py nằm ở: indoor_wayfinder/backend/core/db.py
    # => parents[2] là thư mục 'indoor_wayfinder/'
    BASE_PKG = Path(__file__).resolve().parents[2]
    DB_DIR = BASE_PKG / "data" / "db"
    DB_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH = (DB_DIR / "wayfinder.db").resolve()
    DB_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})


def init_db():
    # import models để SQLModel biết tất cả lớp
    from backend.models.entities import Map, Node, Alias, Edge

    SQLModel.metadata.create_all(engine)
