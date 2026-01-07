from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from uuid import uuid4

from .enums import DurationCode, Step, ViscosityCode, VolumeCode
from .utils import utc_now


@dataclass
class Session:
    session_id: str
    user_id: int
    chat_id: int
    message_id: int
    step: Step
    created_at_utc: datetime = field(default_factory=utc_now)
    rating: int | None = None
    duration_code: DurationCode | None = None
    volume_code: VolumeCode | None = None
    viscosity_code: ViscosityCode | None = None
    finalizing: bool = False


class SessionManager:
    def __init__(self, ttl: timedelta) -> None:
        self._ttl = ttl
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def create(self, user_id: int, chat_id: int, message_id: int = 0) -> Session:
        session_id = f"{user_id}_{int(utc_now().timestamp() * 1000)}_{uuid4().hex[:4]}"
        session = Session(
            session_id=session_id,
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            step=Step.RATING,
        )
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.pop(session_id, None)

    def cleanup_expired(self) -> int:
        now = utc_now()
        expired: list[str] = []
        with self._lock:
            for session_id, session in self._sessions.items():
                if now - session.created_at_utc > self._ttl:
                    expired.append(session_id)
            for session_id in expired:
                self._sessions.pop(session_id, None)
        return len(expired)
