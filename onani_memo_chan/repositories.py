from datetime import datetime

from .db import Database


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_timezone(self, user_id: int) -> str | None:
        row = self._db.fetchone(
            "SELECT timezone FROM users WHERE user_id = ?;",
            (user_id,),
        )
        return row["timezone"] if row else None

    def upsert_timezone(self, user_id: int, timezone: str, now_utc: datetime) -> None:
        now_iso = now_utc.isoformat()
        self._db.execute(
            """
            INSERT INTO users (user_id, timezone, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              timezone = excluded.timezone,
              updated_at_utc = excluded.updated_at_utc;
            """,
            (user_id, timezone, now_iso, now_iso),
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
