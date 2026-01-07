import logging
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler
from telegram.request import HTTPXRequest

from .config import Settings
from .db import Database
from .handlers import (
    callback,
    cleanup_sessions,
    do,
    error_handler,
    month,
    start,
    timezone,
    week,
)
from .repositories import RecordRepository, UserRepository
from .services import Services
from .session import SessionManager
from .stats import StatsService


def build_application(settings: Settings) -> Application:
    _ensure_db_dir(settings.db_path)
    db = Database(settings.db_path)
    users = UserRepository(db)
    records = RecordRepository(db)
    sessions = SessionManager(ttl=timedelta(minutes=settings.session_ttl_minutes))
    stats = StatsService(records)
    services = Services(users=users, records=records, sessions=sessions, stats=stats)

    request = HTTPXRequest(connect_timeout=10.0, read_timeout=60.0, write_timeout=60.0)
    application = Application.builder().token(settings.bot_token).request(request).build()
    application.bot_data["services"] = services

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("timezone", timezone))
    application.add_handler(CommandHandler("do", do))
    application.add_handler(CommandHandler("week", week))
    application.add_handler(CommandHandler("month", month))
    application.add_handler(CallbackQueryHandler(callback))
    application.add_error_handler(error_handler)

    interval = settings.session_cleanup_minutes * 60
    if application.job_queue:
        application.job_queue.run_repeating(
            cleanup_sessions, interval=interval, first=interval
        )
    return application


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    load_dotenv()
    settings = Settings.from_env()
    application = build_application(settings)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def _ensure_db_dir(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
