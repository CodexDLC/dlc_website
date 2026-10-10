"""PostgreSQL target adapter for local preprod transfer.

Enforces connection strictly to local loopback PostgreSQL via env DSN.
Validates clean post-migrate state, safely handles bootstrap rows,
applies deferred constraints, performs batched typed inserts, and resets sequences.
Never logs DSN credentials or row values.
"""

import os
import urllib.parse
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import psycopg2.extras
from psycopg2 import sql
from psycopg2.extensions import connection as PgConnection

from .normalization import convert_value_for_postgres


class InvalidTargetHostError(Exception):
    """Raised when target host is not a local loopback."""


class TargetDatabaseNotEmptyError(Exception):
    """Raised when target PostgreSQL contains unexpected business records."""


class PostgresSchemaError(Exception):
    """Raised when target schema does not match expectations."""


BOOTSTRAP_ALLOWED_TABLES = frozenset(
    {"django_migrations", "django_content_type", "auth_permission"}
)

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


@dataclass(frozen=True)
class PostgresColumn:
    name: str
    data_type: str
    udt_name: str
    is_nullable: bool
    column_default: str | None


class PostgresAdapter:
    """Manages transactional interactions with local loopback PostgreSQL."""

    def __init__(self, env_var_name: str = "PREPROD_POSTGRES_DSN") -> None:
        self.env_var_name = env_var_name
        self.dsn = os.environ.get(env_var_name, "").strip()
        if not self.dsn:
            raise ValueError(
                f"Target PostgreSQL DSN environment variable '{env_var_name}' is not set or empty."
            )
        self._validate_loopback_host()
        self._conn: PgConnection | None = None

    def _validate_loopback_host(self) -> None:
        """Verify target host and hostaddr are strictly loopback (localhost/127.0.0.1/socket)."""
        host: str | None = None
        hostaddr: str | None = None

        if self.dsn.startswith("postgres://") or self.dsn.startswith("postgresql://"):
            try:
                parsed = urllib.parse.urlparse(self.dsn)
            except Exception as err:
                raise InvalidTargetHostError(f"Target PostgreSQL DSN is malformed: {err}") from err
            if not parsed.hostname and not parsed.path:
                raise InvalidTargetHostError("Target PostgreSQL DSN is malformed.")
            host = parsed.hostname
            qs = urllib.parse.parse_qs(parsed.query)
            if "hostaddr" in qs:
                hostaddr = qs["hostaddr"][0]
        else:
            try:
                parsed_dict = psycopg2.extensions.parse_dsn(self.dsn)
                host = parsed_dict.get("host")
                hostaddr = parsed_dict.get("hostaddr")
            except Exception as err:
                raise InvalidTargetHostError(f"Target PostgreSQL DSN is malformed: {err}") from err

        # Verify host if present
        if host is not None and host != "":
            if host not in LOOPBACK_HOSTS and not host.startswith("/"):
                raise InvalidTargetHostError(
                    f"Target host '{host}' is NOT a local loopback address. "
                    "Only localhost / 127.0.0.1 / unix domain sockets are permitted."
                )

        # Verify hostaddr if present
        if hostaddr is not None and hostaddr != "":
            if hostaddr not in LOOPBACK_HOSTS:
                raise InvalidTargetHostError(
                    f"Target hostaddr '{hostaddr}' is NOT a local loopback address."
                )

    def get_masked_connection_info(self) -> str:
        """Return safe description of target DB without password or sensitive tokens."""
        try:
            if self.dsn.startswith("postgres://") or self.dsn.startswith("postgresql://"):
                p = urllib.parse.urlparse(self.dsn)
                return f"postgres://{p.username or 'anon'}@{p.hostname or 'localhost'}:{p.port or 5432}{p.path}"
            d = psycopg2.extensions.parse_dsn(self.dsn)
            return f"host={d.get('host', 'local-socket')} dbname={d.get('dbname', '')} user={d.get('user', '')}"
        except Exception:
            return "host=loopback (masked)"

    def connect(self) -> PgConnection:
        """Establish connection to PostgreSQL."""
        if self._conn is not None and not self._conn.closed:
            return self._conn
        conn = psycopg2.connect(self.dsn)
        conn.autocommit = False
        self._conn = conn
        return conn

    def close(self) -> None:
        """Close connection if open."""
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "PostgresAdapter":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def get_tables(self) -> list[str]:
        """Return list of base tables in the public schema."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name;
                """
            )
            return [row[0] for row in cur.fetchall()]

    def get_columns(self, table_name: str) -> dict[str, PostgresColumn]:
        """Get column metadata for a given table."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, udt_name, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
                """,
                (table_name,),
            )
            return {
                row[0]: PostgresColumn(
                    name=row[0],
                    data_type=row[1],
                    udt_name=row[2],
                    is_nullable=(row[3] == "YES"),
                    column_default=row[4],
                )
                for row in cur.fetchall()
            }

    def get_primary_key_column(self, table_name: str) -> str | None:
        """Find the single primary key column if one exists."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public'
                  AND tc.table_name = %s;
                """,
                (table_name,),
            )
            rows = cur.fetchall()
            if len(rows) == 1:
                return rows[0][0]
            return None

    def get_foreign_key_dependencies(self) -> list[tuple[str, str]]:
        """Return list of (child_table, parent_table) foreign key relationships."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    tc.table_name AS child_table,
                    ccu.table_name AS parent_table
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public';
                """
            )
            return cur.fetchall()

    def count_rows(self, table_name: str) -> int:
        """Count rows in a table."""
        conn = self.connect()
        with conn.cursor() as cur:
            query = sql.SQL("SELECT COUNT(*) FROM {table};").format(table=sql.Identifier(table_name))
            cur.execute(query)
            return int(cur.fetchone()[0])

    def check_target_is_clean(self) -> dict[str, int]:
        """Ensure no business records exist in target database.

        Only BOOTSTRAP_ALLOWED_TABLES (django_migrations, django_content_type, auth_permission)
        may contain rows created by initial 'migrate'.
        All other business tables must be completely empty.

        Raises:
            TargetDatabaseNotEmptyError: If any business table has count > 0.
        """
        tables = self.get_tables()
        row_counts: dict[str, int] = {}
        dirty_business_tables: dict[str, int] = {}

        for tbl in tables:
            cnt = self.count_rows(tbl)
            row_counts[tbl] = cnt
            if tbl not in BOOTSTRAP_ALLOWED_TABLES and cnt > 0:
                dirty_business_tables[tbl] = cnt

        if dirty_business_tables:
            details = ", ".join(f"{t}: {c} rows" for t, c in dirty_business_tables.items())
            raise TargetDatabaseNotEmptyError(
                f"Target PostgreSQL contains existing business records: {details}. "
                "Import requires a clean post-migrate database to prevent overwriting or corruption."
            )

        return row_counts

    def clear_bootstrap_rows(self, cur: Any) -> None:
        """Safely delete bootstrap rows in reverse FK dependency order.

        No CASCADE is used, ensuring strict safety.
        """
        # Order: auth_permission depends on django_content_type
        cur.execute("DELETE FROM auth_permission;")
        cur.execute("DELETE FROM django_content_type;")
        cur.execute("DELETE FROM django_migrations;")

    def insert_rows(
        self,
        cur: Any,
        table_name: str,
        rows: list[dict[str, Any]],
        target_columns: dict[str, PostgresColumn],
    ) -> None:
        """Insert batch of rows with exact type conversion."""
        if not rows:
            return

        col_names = [col for col in rows[0].keys() if col in target_columns]
        if not col_names:
            return

        cols_sql = sql.SQL(", ").join(sql.Identifier(c) for c in col_names)
        placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in col_names)
        insert_query = sql.SQL("INSERT INTO {table} ({cols}) VALUES ({vals})").format(
            table=sql.Identifier(table_name),
            cols=cols_sql,
            vals=placeholders,
        )

        converted_batch: list[tuple[Any, ...]] = []
        for row in rows:
            converted_row = []
            for col in col_names:
                raw_val = row.get(col)
                target_col = target_columns[col]
                converted_val = convert_value_for_postgres(raw_val, target_col.udt_name, col)
                converted_row.append(converted_val)
            converted_batch.append(tuple(converted_row))

        psycopg2.extras.execute_batch(cur, insert_query, converted_batch)

    def reset_sequence(self, cur: Any, table_name: str, pk_col: str) -> None:
        """Reset sequence for a table's primary key to MAX(pk_col)."""
        cur.execute(
            "SELECT pg_get_serial_sequence(%s, %s);",
            (f"public.{table_name}", pk_col),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return
        seq_name = row[0]

        max_query = sql.SQL("SELECT COALESCE(MAX({pk}), 0) FROM {table};").format(
            pk=sql.Identifier(pk_col),
            table=sql.Identifier(table_name),
        )
        cur.execute(max_query)
        max_val = cur.fetchone()[0]

        if max_val > 0:
            cur.execute("SELECT setval(%s, %s, true);", (seq_name, max_val))
        else:
            cur.execute("SELECT setval(%s, 1, false);", (seq_name,))

    def stream_rows(
        self, table_name: str, batch_size: int = 1000
    ) -> Generator[list[dict[str, Any]], None, None]:
        """Stream rows from target PostgreSQL in deterministic order."""
        conn = self.connect()
        pk = self.get_primary_key_column(table_name)

        if pk:
            stream_query = sql.SQL("SELECT * FROM {table} ORDER BY {pk} ASC;").format(
                table=sql.Identifier(table_name),
                pk=sql.Identifier(pk),
            )
        else:
            stream_query = sql.SQL("SELECT * FROM {table};").format(
                table=sql.Identifier(table_name),
            )

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(stream_query)
            while True:
                batch = cur.fetchmany(batch_size)
                if not batch:
                    break
                yield [dict(r) for r in batch]
