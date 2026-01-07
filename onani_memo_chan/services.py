from dataclasses import dataclass

from .repositories import RecordRepository, UserRepository
from .session import SessionManager
from .stats import StatsService


@dataclass(frozen=True)
class Services:
    users: UserRepository
    records: RecordRepository
    sessions: SessionManager
    stats: StatsService
