import asyncio
import os
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, date

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv

from .db import init_db, add_project, list_projects, delete_project, set_next_due_date
from .scheduler import setup_scheduler


class AddProjectForm(StatesGroup):
    project_name = State()
    server_name = State()
    owner_name = State()
    owner_phone = State()
    server_login_username = State()
    server_login_password = State()
    server_ip = State()
    root_password = State()
    next_due_date = State()


class EditDueForm(StatesGroup):
    project_id = State()
    new_due = State()


@dataclass
class Settings:
    token: str
    admin_chat_id: int
    db_path: str
    timezone: str


def load_settings() -> Settings:
    # Get project root directory (parent of app directory)
    project_root = Path(__file__).parent.parent
    # Try loading .env from project root first, then from config/
    env_file = project_root / ".env"
    if not env_file.exists():
        env_file = project_root / "config" / ".env"
    load_dotenv(dotenv_path=env_file)
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    admin_chat_id = int(os.getenv("ADMIN_CHAT_ID", "0"))
    db_path = os.getenv("DATABASE_PATH", "./data/reminder.db").strip()
    timezone = os.getenv("TIMEZONE", "Asia/Tashkent").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    if not admin_chat_id:
        raise RuntimeError("ADMIN_CHAT_ID is not set")
    return Settings(token=token, admin_chat_id=admin_chat_id, db_path=db_path, timezone=timezone)


def format_date(d: datetime | date | str) -> str:
    """Format date as dd.mm.yyyy"""
    if isinstance(d, str):
        try:
            # Try parsing from ISO format first
            d = datetime.fromisoformat(d)
        except (ValueError, AttributeError):
            try:
                # Try parsing from dd.mm.yyyy format
                d = datetime.strptime(d, "%d.%m.%Y")
            except ValueError:
                return d
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d.%m.%Y")


def parse_date(text: str) -> date | None:
    """Parse date from dd.mm.yyyy format"""
    text = text.strip()
    try:
        return datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        return None


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    kb = ReplyKeyboardBuilder()
    kb.button(text="/addproject")
    kb.button(text="/list")
    kb.button(text="/delete")
    kb.adjust(2)
    await message.answer(
        "Assalomu alaykum! Bu bot server/loyiha oylik to'lov eslatmalarini yuboradi.\n"
        "Buyruqlar: /addproject, /list, /delete, /help",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Buyruqlar:\n"
        "/addproject - Yangi loyiha qo'shish\n"
        "/list - Loyihalar ro'yxati\n"
        "/delete - ID bo'yicha o'chirish\n"
        "/editdue - Keyingi muddatni o'zgartirish"
    )


@router.message(Command("addproject"))
async def cmd_add_project(message: Message, state: FSMContext):
    await state.set_state(AddProjectForm.project_name)
    await message.answer("Loyiha nomini kiriting:")


@router.message(AddProjectForm.project_name)
async def ask_server_name(message: Message, state: FSMContext):
    await state.update_data(project_name=message.text.strip())
    await state.set_state(AddProjectForm.server_name)
    await message.answer("Qaysi serverda turganini kiriting:")


@router.message(AddProjectForm.server_name)
async def ask_owner_name(message: Message, state: FSMContext):
    await state.update_data(server_name=message.text.strip())
    await state.set_state(AddProjectForm.owner_name)
    await message.answer("Loyiha egasining ismini kiriting:")


@router.message(AddProjectForm.owner_name)
async def ask_owner_phone(message: Message, state: FSMContext):
    await state.update_data(owner_name=message.text.strip())
    await state.set_state(AddProjectForm.owner_phone)
    await message.answer("Telefon raqamini kiriting (masalan, +998901234567):")


@router.message(AddProjectForm.owner_phone)
async def ask_server_login_username(message: Message, state: FSMContext):
    owner_phone = message.text.strip()
    await state.update_data(owner_phone=owner_phone)
    await state.set_state(AddProjectForm.server_login_username)
    await message.answer("Server login username ni kiriting:")


@router.message(AddProjectForm.server_login_username)
async def ask_server_login_password(message: Message, state: FSMContext):
    server_login_username = message.text.strip()
    await state.update_data(server_login_username=server_login_username)
    await state.set_state(AddProjectForm.server_login_password)
    await message.answer("Server login password ni kiriting:")


@router.message(AddProjectForm.server_login_password)
async def ask_server_ip(message: Message, state: FSMContext):
    server_login_password = message.text.strip()
    await state.update_data(server_login_password=server_login_password)
    await state.set_state(AddProjectForm.server_ip)
    await message.answer("Server IP manzilini kiriting (masalan: 192.168.1.1):")


@router.message(AddProjectForm.server_ip)
async def ask_root_password(message: Message, state: FSMContext):
    server_ip = message.text.strip()
    await state.update_data(server_ip=server_ip)
    await state.set_state(AddProjectForm.root_password)
    await message.answer("Root password ni kiriting:")


@router.message(AddProjectForm.root_password)
async def ask_next_due_date(message: Message, state: FSMContext):
    root_password = message.text.strip()
    await state.update_data(root_password=root_password)
    await state.set_state(AddProjectForm.next_due_date)
    await message.answer("Tugash sanasini kiriting (format: dd.mm.yyyy, masalan: 25.12.2024):")


@router.message(AddProjectForm.next_due_date)
async def finalize_add(message: Message, state: FSMContext, bot: Bot):
    due_date_text = message.text.strip()
    due_date = parse_date(due_date_text)
    if due_date is None:
        await message.answer("Noto'g'ri format. Iltimos, dd.mm.yyyy formatida kiriting (masalan: 25.12.2024). Qayta kiriting:")
        return
    
    data = await state.get_data()
    settings = load_settings()
    init_db(settings.db_path)
    
    # Convert date to datetime at midnight for storage
    due_datetime = datetime.combine(due_date, datetime.min.time())
    
    project_id = add_project(
        db_path=settings.db_path,
        project_name=data["project_name"],
        server_name=data["server_name"],
        owner_name=data["owner_name"],
        owner_phone=data["owner_phone"],
        server_login_username=data["server_login_username"],
        server_login_password=data["server_login_password"],
        server_ip=data["server_ip"],
        root_password=data["root_password"],
        start_date=datetime.now(),
        next_due_date=due_datetime,
    )
    await state.clear()
    await message.answer(f"Loyiha qo'shildi. ID: {project_id}")
    await bot.send_message(
        chat_id=settings.admin_chat_id,
        text=(
            "Yangi loyiha qo'shildi:\n"
            f"ID: {project_id}\n"
            f"Project: {data['project_name']}\n"
            f"Server: {data['server_name']}\n"
            f"Ega: {data['owner_name']}\n"
            f"Telefon: {data['owner_phone']}\n"
            f"Login: {data['server_login_username']}\n"
            f"IP: {data['server_ip']}\n"
            f"Tugash sanasi: {format_date(due_date)}"
        ),
    )


@router.message(Command("list"))
async def cmd_list(message: Message):
    settings = load_settings()
    init_db(settings.db_path)
    items = list_projects(settings.db_path)
    if not items:
        await message.answer("Hozircha loyihalar yo'q.")
        return
    lines = []
    for it in items:
        due_date_formatted = format_date(it['next_due_date'])
        lines.append(
            f"ID: {it['id']} | {it['project_name']}\n"
            f"Server: {it['server_name']}\n"
            f"Ega: {it['owner_name']} | Tel: {it['owner_phone']}\n"
            f"Login: {it.get('server_login_username', 'N/A')} | IP: {it.get('server_ip', 'N/A')}\n"
            f"Tugash sanasi: {due_date_formatted}\n"
            f"{'─' * 30}"
        )
    # Split into multiple messages if too long
    message_text = "\n".join(lines)
    if len(message_text) > 4096:
        # Split into chunks
        chunks = [message_text[i:i+4096] for i in range(0, len(message_text), 4096)]
        for chunk in chunks:
            await message.answer(chunk)
    else:
        await message.answer(message_text)


@router.message(Command("delete"))
async def cmd_delete(message: Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: /delete <ID>")
        return
    project_id = int(parts[1])
    settings = load_settings()
    init_db(settings.db_path)
    ok = delete_project(settings.db_path, project_id)
    await message.answer("O'chirildi" if ok else "Topilmadi")


@router.message(Command("editdue"))
async def cmd_edit_due(message: Message, state: FSMContext):
    await state.set_state(EditDueForm.project_id)
    await message.answer("Loyiha ID sini kiriting (masalan: 12):")


@router.message(EditDueForm.project_id)
async def ask_new_due(message: Message, state: FSMContext):
    parts = message.text.strip()
    if not parts.isdigit():
        await message.answer("Iltimos, raqamli ID kiriting (masalan: 12). Qayta kiriting:")
        return
    await state.update_data(project_id=int(parts))
    await state.set_state(EditDueForm.new_due)
    await message.answer(
        "Yangi tugash sanasini kiriting (format: dd.mm.yyyy, masalan: 25.12.2024):"
    )


@router.message(EditDueForm.new_due)
async def finalize_edit_due(message: Message, state: FSMContext):
    due_date = parse_date(message.text)
    if due_date is None:
        await message.answer(
            "Noto'g'ri format. Iltimos, dd.mm.yyyy formatida kiriting (masalan: 25.12.2024). Qayta kiriting:"
        )
        return
    
    # Convert date to datetime at midnight for storage
    new_due_datetime = datetime.combine(due_date, datetime.min.time())
    
    data = await state.get_data()
    settings = load_settings()
    init_db(settings.db_path)
    ok = set_next_due_date(settings.db_path, int(data["project_id"]), new_due_datetime)
    await state.clear()
    await message.answer(f"Yangilandi. Yangi tugash sanasi: {format_date(due_date)}" if ok else "Topilmadi")


async def main():
    settings = load_settings()
    init_db(settings.db_path)
    bot = Bot(token=settings.token)
    dp = Dispatcher()
    dp.include_router(router)

    async def notify_admin(text: str):
        await bot.send_message(chat_id=settings.admin_chat_id, text=text)

    scheduler = setup_scheduler(settings.db_path, settings.timezone, notify_admin)
    scheduler.start()
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())

