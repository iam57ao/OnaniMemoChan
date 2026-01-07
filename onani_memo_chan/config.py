import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_path: Path
    session_ttl_minutes: int
    session_cleanup_minutes: int

    @classmethod
    def from_env(cls) -> "Settings":
        bot_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise RuntimeError("Missing BOT_TOKEN or TELEGRAM_BOT_TOKEN.")

        db_path = Path(os.getenv("ONANI_DB_PATH", "data/onani_memo.db"))
        session_ttl_minutes = int(os.getenv("SESSION_TTL_MINUTES", "30"))
        session_cleanup_minutes = int(os.getenv("SESSION_CLEANUP_MINUTES", "5"))
        return cls(
            bot_token=bot_token,
            db_path=db_path,
            session_ttl_minutes=session_ttl_minutes,
            session_cleanup_minutes=session_cleanup_minutes,
        )
