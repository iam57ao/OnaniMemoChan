import sqlite3
from pathlib import Path
from threading import Lock

SCHEMA_VERSION = 2


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
                self._apply_schema_v2()
                self._conn.execute(
                    "INSERT INTO schema_meta (version) VALUES (?);",
                    (SCHEMA_VERSION,),
                )
            elif row["version"] == 1 and SCHEMA_VERSION == 2:
                self._migrate_v1_to_v2()
                self._conn.execute("UPDATE schema_meta SET version = ?;", (SCHEMA_VERSION,))
            elif row["version"] == 2 and SCHEMA_VERSION == 2:
                self._ensure_user_columns()
            elif row["version"] != SCHEMA_VERSION:
                raise RuntimeError(
                    f"Unsupported schema version {row['version']}, expected {SCHEMA_VERSION}."
                )
            self._conn.commit()

    def _apply_schema_v2(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              user_id         INTEGER PRIMARY KEY,
              timezone        TEXT NOT NULL,
              nickname        TEXT,
              height_cm       INTEGER,
              weight_kg       REAL,
              birthday        TEXT,
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

    def _migrate_v1_to_v2(self) -> None:
        self._ensure_user_columns()

    def _ensure_user_columns(self) -> None:
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(users);")
        }
        if "nickname" not in columns:
            self._conn.execute("ALTER TABLE users ADD COLUMN nickname TEXT;")
        if "height_cm" not in columns:
            self._conn.execute("ALTER TABLE users ADD COLUMN height_cm INTEGER;")
        if "weight_kg" not in columns:
            self._conn.execute("ALTER TABLE users ADD COLUMN weight_kg REAL;")
        if "birthday" not in columns:
            self._conn.execute("ALTER TABLE users ADD COLUMN birthday TEXT;")
