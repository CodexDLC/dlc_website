"""SQLite reader module for local preprod transfer.

Opens SQLite backup exclusively in read-only mode via URI.
Performs PRAGMA integrity_check and PRAGMA foreign_key_check before reading.
"""

import os
import sqlite3
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SqliteIntegrityError(Exception):
    """Raised when SQLite PRAGMA integrity_check fails."""


class SqliteForeignKeyError(Exception):
    """Raised when SQLite PRAGMA foreign_key_check finds orphaned keys."""


@dataclass(frozen=True)
class SqliteColumn:
    cid: int
    name: str
    type_name: str
    not_null: bool
    default_value: Any
    is_pk: bool


@dataclass(frozen=True)
class SqliteForeignKey:
    id: int
    seq: int
    table: str
    from_col: str
    to_col: str


class SqliteBackupReader:
    """Read-only reader for backup SQLite database."""

    def __init__(self, backup_path: str | Path) -> None:
        self.path = Path(backup_path).resolve()
        if not self.path.exists():
            raise FileNotFoundError(f"Source SQLite backup file not found: {self.path}")
        if self.path.is_dir():
            raise IsADirectoryError(f"Source SQLite path points to a directory: {self.path}")
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        """Connect to SQLite backup strictly in read-only mode using URI syntax."""
        if self._conn is not None:
            return self._conn

        # Convert path to URI-safe form with forward slashes for Windows compatibility
        norm_path = os.path.abspath(self.path).replace("\\", "/")
        # Under Windows, absolute paths like D:/... need file:///D:/...
        if not norm_path.startswith("/"):
            norm_path = f"/{norm_path}"
        uri = f"file:{norm_path}?mode=ro"

        conn = sqlite3.connect(uri, uri=True, timeout=10.0)
        conn.row_factory = sqlite3.Row
        self._conn = conn
        return conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "SqliteBackupReader":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def check_integrity(self) -> None:
        """Verify PRAGMA integrity_check and PRAGMA foreign_key_check.

        Raises:
            SqliteIntegrityError: If integrity check does not return 'ok'.
            SqliteForeignKeyError: If any foreign key violation is found.
        """
        conn = self.connect()
        cursor = conn.cursor()

        # 1. Integrity check
        cursor.execute("PRAGMA integrity_check;")
        rows = cursor.fetchall()
        messages = [row[0] for row in rows]
        if messages != ["ok"]:
            raise SqliteIntegrityError(f"SQLite PRAGMA integrity_check failed: {'; '.join(messages)}")

        # 2. Foreign key check
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()
        if fk_violations:
            details = [f"table={row[0]}, rowid={row[1]}, parent={row[2]}" for row in fk_violations]
            raise SqliteForeignKeyError(
                f"SQLite PRAGMA foreign_key_check found {len(fk_violations)} violation(s): {'; '.join(details)}"
            )

    def get_tables(self) -> list[str]:
        """Return list of user and Django tables, strictly excluding sqlite internal tables."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        return [row["name"] for row in cursor.fetchall()]

    def get_columns(self, table_name: str) -> list[SqliteColumn]:
        """Get column metadata for a given table."""
        conn = self.connect()
        cursor = conn.cursor()
        # PRAGMA doesn't accept parameters in standard SQL, but table_name comes from get_tables()
        cursor.execute(f'PRAGMA table_info("{table_name}");')
        rows = cursor.fetchall()
        return [
            SqliteColumn(
                cid=row["cid"],
                name=row["name"],
                type_name=row["type"].upper(),
                not_null=bool(row["notnull"]),
                default_value=row["dflt_value"],
                is_pk=bool(row["pk"]),
            )
            for row in rows
        ]

    def get_foreign_keys(self, table_name: str) -> list[SqliteForeignKey]:
        """Get foreign keys declared on a table."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(f'PRAGMA foreign_key_list("{table_name}");')
        rows = cursor.fetchall()
        return [
            SqliteForeignKey(
                id=row["id"],
                seq=row["seq"],
                table=row["table"],
                from_col=row["from"],
                to_col=row["to"],
            )
            for row in rows
        ]

    def count_rows(self, table_name: str) -> int:
        """Count rows in a table."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}";')  # noqa: S608
        return int(cursor.fetchone()[0])

    def stream_rows(
        self, table_name: str, batch_size: int = 1000
    ) -> Generator[list[dict[str, Any]], None, None]:
        """Stream rows from a table as dictionaries in deterministic order."""
        conn = self.connect()
        cols = self.get_columns(table_name)
        pk_cols = [c.name for c in cols if c.is_pk]

        if pk_cols:
            order_clause = " ORDER BY " + ", ".join(f'"{col}" ASC' for col in pk_cols)
        else:
            order_clause = " ORDER BY rowid ASC"

        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM "{table_name}"{order_clause};')  # noqa: S608

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            yield [dict(row) for row in rows]
