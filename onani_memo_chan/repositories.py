from dataclasses import dataclass
from datetime import datetime

from .db import Database


@dataclass(frozen=True)
class UserProfile:
    user_id: int
    nickname: str | None
    timezone: str | None
    height_cm: int | None
    weight_kg: float | None
    birthday: str | None
    created_at_utc: datetime
    updated_at_utc: datetime


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_timezone(self, user_id: int) -> str | None:
        row = self._db.fetchone(
            "SELECT timezone FROM users WHERE user_id = ?;",
            (user_id,),
        )
        return row["timezone"] if row else None

    def upsert_timezone(
        self, user_id: int, timezone: str, now_utc: datetime, nickname: str | None
    ) -> None:
        now_iso = now_utc.isoformat()
        self._db.execute(
            """
            INSERT INTO users (user_id, timezone, nickname, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              timezone = excluded.timezone,
              nickname = COALESCE(users.nickname, excluded.nickname),
              updated_at_utc = excluded.updated_at_utc;
            """,
            (user_id, timezone, nickname, now_iso, now_iso),
        )

    def get_profile(self, user_id: int) -> UserProfile | None:
        row = self._db.fetchone(
            """
            SELECT
              user_id,
              nickname,
              timezone,
              height_cm,
              weight_kg,
              birthday,
              created_at_utc,
              updated_at_utc
            FROM users
            WHERE user_id = ?;
            """,
            (user_id,),
        )
        if row is None:
            return None
        return UserProfile(
            user_id=int(row["user_id"]),
            nickname=row["nickname"],
            timezone=row["timezone"],
            height_cm=row["height_cm"],
            weight_kg=row["weight_kg"],
            birthday=row["birthday"],
            created_at_utc=datetime.fromisoformat(row["created_at_utc"]),
            updated_at_utc=datetime.fromisoformat(row["updated_at_utc"]),
        )

    def update_nickname(self, user_id: int, nickname: str, now_utc: datetime) -> None:
        now_iso = now_utc.isoformat()
        self._db.execute(
            """
            UPDATE users
            SET nickname = ?, updated_at_utc = ?
            WHERE user_id = ?;
            """,
            (nickname, now_iso, user_id),
        )

    def update_height_cm(self, user_id: int, height_cm: int, now_utc: datetime) -> None:
        now_iso = now_utc.isoformat()
        self._db.execute(
            """
            UPDATE users
            SET height_cm = ?, updated_at_utc = ?
            WHERE user_id = ?;
            """,
            (height_cm, now_iso, user_id),
        )

    def update_weight_kg(self, user_id: int, weight_kg: float, now_utc: datetime) -> None:
        now_iso = now_utc.isoformat()
        self._db.execute(
            """
            UPDATE users
            SET weight_kg = ?, updated_at_utc = ?
            WHERE user_id = ?;
            """,
            (weight_kg, now_iso, user_id),
        )

    def update_birthday(self, user_id: int, birthday: str, now_utc: datetime) -> None:
        now_iso = now_utc.isoformat()
        self._db.execute(
            """
            UPDATE users
            SET birthday = ?, updated_at_utc = ?
            WHERE user_id = ?;
            """,
            (birthday, now_iso, user_id),
        )


class RecordRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def insert_record(
        self,
        user_id: int,
        timestamp_utc: datetime,
        timezone: str,
        timestamp_local: datetime,
        rating: int,
        duration_code: str,
        volume_code: str,
        viscosity_code: str,
        created_at_utc: datetime,
    ) -> int:
        cur = self._db.execute(
            """
            INSERT INTO records (
              user_id,
              timestamp_utc,
              timezone,
              timestamp_local,
              rating,
              duration_code,
              volume_code,
              viscosity_code,
              created_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                user_id,
                timestamp_utc.isoformat(),
                timezone,
                timestamp_local.isoformat(),
                rating,
                duration_code,
                volume_code,
                viscosity_code,
                created_at_utc.isoformat(),
            ),
        )
        record_id = cur.lastrowid
        if record_id is None:
            raise RuntimeError("Failed to obtain record id after insert.")
        return int(record_id)

    def soft_delete_record(self, record_id: int, user_id: int) -> bool:
        cur = self._db.execute(
            "DELETE FROM records WHERE id = ? AND user_id = ?;",
            (record_id, user_id),
        )
        return cur.rowcount > 0

    def list_records_in_range(
        self, user_id: int, start_utc: datetime, end_utc: datetime
    ) -> list[dict[str, str]]:
        rows = self._db.fetchall(
            """
            SELECT timestamp_utc, timestamp_local
            FROM records
            WHERE user_id = ?
              AND timestamp_utc BETWEEN ? AND ?
            ORDER BY timestamp_utc ASC;
            """,
            (user_id, start_utc.isoformat(), end_utc.isoformat()),
        )
        return [dict(row) for row in rows]

    def get_first_record_time(self, user_id: int) -> datetime | None:
        row = self._db.fetchone(
            """
            SELECT MIN(timestamp_utc) AS first_time
            FROM records WHERE user_id = ?;
            """,
            (user_id,),
        )
        if row and row["first_time"]:
            return datetime.fromisoformat(row["first_time"])
        return None

    def count_all_records(self, user_id: int) -> int:
        row = self._db.fetchone(
            "SELECT COUNT(*) AS cnt FROM records WHERE user_id = ?;",
            (user_id,),
        )
        if row is None or row["cnt"] is None:
            return 0
        return int(row["cnt"])

    def get_last_record_time(self, user_id: int) -> datetime | None:
        row = self._db.fetchone(
            """
            SELECT MAX(timestamp_utc) AS last_time
            FROM records WHERE user_id = ?;
            """,
            (user_id,),
        )
        if row and row["last_time"]:
            return datetime.fromisoformat(row["last_time"])
        return None
