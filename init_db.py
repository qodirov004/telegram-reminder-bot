#!/usr/bin/env python3
"""
Database initialization script
Run this script to create the database manually: python init_db.py
"""

from app.db import init_db
from app.bot import load_settings

def main():
    print("Database yaratilmoqda...")
    settings = load_settings()
    init_db(settings.db_path)
    print(f"✅ Database muvaffaqiyatli yaratildi: {settings.db_path}")

if __name__ == "__main__":
    main()

