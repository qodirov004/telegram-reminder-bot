#!/usr/bin/env python3
"""
Telegram Reminder Bot - Entry point
Run with: python bot.py
"""

from app.bot import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())

