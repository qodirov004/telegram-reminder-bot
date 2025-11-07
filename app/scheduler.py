from datetime import datetime
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .db import get_due_projects, get_projects_due_in_days, bump_next_due_date


def format_date(d: datetime | str) -> str:
    """Format date as dd.mm.yyyy"""
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d)
        except (ValueError, AttributeError):
            return d
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d.%m.%Y")


async def run_due_checks(db_path: str, notify: Callable[[str], None]):
    """Check for projects that are due today or earlier"""
    now = datetime.now()
    due = get_due_projects(db_path, now)
    for item in due:
        due_date_formatted = format_date(item['next_due_date'])
        message = (
            f"🔴 Eslatma: Server uchun oylik to'lov vaqti keldi!\n"
            f"Project: {item['project_name']}\n"
            f"Server: {item['server_name']}\n"
            f"Ega: {item['owner_name']}\n"
            f"Telefon: {item['owner_phone']}\n"
            f"Login: {item.get('server_login_username', 'N/A')}\n"
            f"IP: {item.get('server_ip', 'N/A')}\n"
            f"Tugash sanasi: {due_date_formatted}"
        )
        await notify(message)
        bump_next_due_date(db_path, int(item["id"]))


async def run_reminder_checks(db_path: str, notify: Callable[[str], None], days_ahead: int):
    """Check for projects that are due in N days (reminder notification)"""
    now = datetime.now()
    due_soon = get_projects_due_in_days(db_path, now, days_ahead)
    for item in due_soon:
        due_date_formatted = format_date(item['next_due_date'])
        message = (
            f"⚠️ Eslatma: Server uchun to'lov {days_ahead} kun qoldi!\n"
            f"Project: {item['project_name']}\n"
            f"Server: {item['server_name']}\n"
            f"Ega: {item['owner_name']}\n"
            f"Telefon: {item['owner_phone']}\n"
            f"Login: {item.get('server_login_username', 'N/A')}\n"
            f"IP: {item.get('server_ip', 'N/A')}\n"
            f"Tugash sanasi: {due_date_formatted}"
        )
        await notify(message)


def setup_scheduler(db_path: str, tz: str, notify_coro: Callable[[str], None]) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=tz)

    async def job_wrapper():
        await run_due_checks(db_path, notify_coro)

    async def reminder_wrapper():
        await run_reminder_checks(db_path, notify_coro, days_ahead=2)

    # Run every day at 09:00 local time - check due projects
    scheduler.add_job(job_wrapper, CronTrigger(hour=9, minute=0))
    # Run every day at 09:00 local time - send 2 days ahead reminder
    scheduler.add_job(reminder_wrapper, CronTrigger(hour=9, minute=0))
    return scheduler

