from pathlib import Path
import os
from sqlmodel import create_engine, SQLModel
from dotenv import load_dotenv

# Resolve project root and load .env explicitly to avoid CWD issues
BASE_PKG = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=BASE_PKG / ".env")
# Also load a local .env next to this file if present (e.g., backend/core/.env)
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# Cho phép override bằng biến môi trường (tuỳ chọn)
ENV_URL = os.getenv("WAYFINDER_DB_URL") or os.getenv("DATABASE_URL")

if ENV_URL:
    DB_URL = ENV_URL
else:
    # db.py nằm ở: indoor_wayfinder/backend/core/db.py
    # => BASE_PKG là thư mục 'indoor_wayfinder/'
    DB_DIR = BASE_PKG / "data" / "db"
    DB_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH = (DB_DIR / "wayfinder.db").resolve()
    DB_URL = f"sqlite:///{DB_PATH.as_posix()}"

if DB_URL.startswith("sqlite"):
    engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DB_URL, echo=False)


def init_db():
    # import models để SQLModel biết tất cả lớp
    from backend.models.entities import Map, Node, Alias, Edge

    SQLModel.metadata.create_all(engine)
