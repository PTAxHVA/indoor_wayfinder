#!/usr/bin/env python3
"""
Script để khởi tạo database cho Indoor Wayfinder
Chạy script này trước khi start server để tạo các bảng cần thiết
"""

import sys
import os
from pathlib import Path

# Thêm đường dẫn project vào Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from backend.core.db import init_db

if __name__ == "__main__":
    print("Đang khởi tạo database...")
    try:
        init_db()
        print("✅ Database đã được khởi tạo thành công!")
        print("Bây giờ bạn có thể chạy server với: uvicorn backend.main:app --reload")
    except Exception as e:
        print(f"❌ Lỗi khi khởi tạo database: {e}")
        sys.exit(1)
