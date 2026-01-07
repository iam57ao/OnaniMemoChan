import sqlite3
from pathlib import Path
from threading import Lock

SCHEMA_VERSION = 1


class Database:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA journal_mode = WAL;")
        self._ensure_schema()

    def close(self) -> None:
        self._conn.close()

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def fetchone(
        self, sql: str, params: tuple[object, ...] = ()
    ) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchone()

    def fetchall(
        self, sql: str, params: tuple[object, ...] = ()
    ) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchall()

    def _ensure_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                  version INTEGER NOT NULL
                );
                """
            )
            row = self._conn.execute(
                "SELECT version FROM schema_meta LIMIT 1;"
            ).fetchone()
            if row is None:
                self._apply_schema_v1()
                self._conn.execute(
                    "INSERT INTO schema_meta (version) VALUES (?);",
                    (SCHEMA_VERSION,),
                )
            elif row["version"] == 2 and SCHEMA_VERSION == 1:
                # Older code marked the same schema as v2; normalize back to v1.
                self._conn.execute("UPDATE schema_meta SET version = ?;", (SCHEMA_VERSION,))
            elif row["version"] != SCHEMA_VERSION:
                raise RuntimeError(
                    f"Unsupported schema version {row['version']}, expected {SCHEMA_VERSION}."
                )
            self._conn.commit()

    def _apply_schema_v1(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              user_id         INTEGER PRIMARY KEY,
              timezone        TEXT NOT NULL,
              created_at_utc  TEXT NOT NULL,
              updated_at_utc  TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_users_updated ON users(updated_at_utc);

            CREATE TABLE IF NOT EXISTS records (
              id               INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id          INTEGER NOT NULL,

              timestamp_utc    TEXT NOT NULL,
              timezone         TEXT NOT NULL,
              timestamp_local  TEXT NOT NULL,

              rating           INTEGER NOT NULL,
              duration_code    TEXT NOT NULL,
              volume_code      TEXT NOT NULL,
              viscosity_code   TEXT NOT NULL,

              created_at_utc   TEXT NOT NULL,

              FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_records_user_time
              ON records(user_id, timestamp_utc);
            """
        )
