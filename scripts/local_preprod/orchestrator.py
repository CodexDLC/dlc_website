"""Orchestrator for local preprod transfer.

Performs strict pre-flight checks, schema validation, safe transaction execution,
sequence resetting, and deterministic row/table hash verification.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .normalization import compute_row_hash, compute_table_hash
from .postgres_adapter import PostgresAdapter
from .sqlite_reader import SqliteBackupReader


class TransferPreconditionError(Exception):
    """Raised when pre-flight integrity or preconditions fail."""


class SchemaMismatchError(Exception):
    """Raised when source and target database schemas are incompatible."""


@dataclass
class TableVerificationResult:
    table_name: str
    source_count: int
    target_count: int
    source_hash: str
    target_hash: str
    status: str  # "MATCH" | "COUNT_MISMATCH" | "HASH_MISMATCH" | "MISSING_IN_TARGET"


@dataclass
class TransferReport:
    source_path: str
    target_info: str
    integrity_check: str
    foreign_key_check: str
    overall_status: str  # "SUCCESS" | "FAILED" | "VERIFIED_OK" | "VERIFIED_MISMATCH"
    tables: dict[str, dict[str, Any]]
    errors: list[str]


class PreprodTransferOrchestrator:
    """Coordinates SQLite backup reading, PostgreSQL loading, and deterministic verification."""

    def __init__(
        self,
        source_path: str | Path,
        postgres_adapter: PostgresAdapter,
    ) -> None:
        self.source_path = Path(source_path)
        self.pg = postgres_adapter

    def _topological_sort_tables(
        self,
        tables_to_sort: set[str],
        fk_dependencies: list[tuple[str, str]],
    ) -> list[str]:
        """Sort tables in topological order (parents before children).

        Bootstrap tables (django_content_type, auth_permission, django_migrations)
        are placed first in a safe known sequence.
        """
        bootstrap_order = ["django_content_type", "auth_permission", "django_migrations"]
        ordered_tables: list[str] = [t for t in bootstrap_order if t in tables_to_sort]
        remaining = set(tables_to_sort) - set(ordered_tables)

        # Build graph: parent -> set of children
        # In DB loading, if child depends on parent, parent must be loaded before child.
        in_degree: dict[str, int] = {t: 0 for t in remaining}
        adj: dict[str, set[str]] = defaultdict(set)

        for child, parent in fk_dependencies:
            if child in remaining and parent in remaining and child != parent:
                # parent must come before child
                if child not in adj[parent]:
                    adj[parent].add(child)
                    in_degree[child] += 1

        queue = deque([t for t in remaining if in_degree[t] == 0])
        sorted_remaining: list[str] = []

        while queue:
            node = queue.popleft()
            sorted_remaining.append(node)
            for child in adj[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        # If there are circular dependencies among non-bootstrap tables,
        # append any leftover tables (SET CONSTRAINTS ALL DEFERRED handles deferrable FK cycles)
        leftovers = remaining - set(sorted_remaining)
        if leftovers:
            sorted_remaining.extend(sorted(leftovers))

        return ordered_tables + sorted_remaining

    def preflight_check(self) -> None:
        """Run all safety checks on source and target without modifying anything."""
        with SqliteBackupReader(self.source_path) as reader:
            reader.check_integrity()

        self.pg.check_target_is_clean()

    def validate_schema(self) -> None:
        """Verify schema compatibility between source SQLite and target PostgreSQL."""
        with SqliteBackupReader(self.source_path) as reader:
            src_tables = reader.get_tables()
            pg_tables = set(self.pg.get_tables())

            for tbl in src_tables:
                if tbl not in pg_tables:
                    cnt = reader.count_rows(tbl)
                    if cnt > 0:
                        raise SchemaMismatchError(
                            f"Non-empty source table '{tbl}' ({cnt} rows) does not exist in target PostgreSQL."
                        )
                    continue

                # Check columns for common table bidirectionally
                src_cols = {c.name: c for c in reader.get_columns(tbl)}
                pg_cols = self.pg.get_columns(tbl)

                for cname in src_cols:
                    if cname not in pg_cols:
                        raise SchemaMismatchError(
                            f"Column '{cname}' of table '{tbl}' in source SQLite is missing in target PostgreSQL."
                        )
                for cname in pg_cols:
                    if cname not in src_cols:
                        raise SchemaMismatchError(
                            f"Column '{cname}' of table '{tbl}' in target PostgreSQL is missing in source SQLite."
                        )

            # Check migrations alignment
            if "django_migrations" in src_tables and "django_migrations" in pg_tables:
                src_mig_rows: list[dict[str, Any]] = []
                for batch in reader.stream_rows("django_migrations"):
                    src_mig_rows.extend(batch)
                src_mig_keys = {(r["app"], r["name"]) for r in src_mig_rows}

                pg_mig_rows: list[dict[str, Any]] = []
                for batch in self.pg.stream_rows("django_migrations"):
                    pg_mig_rows.extend(batch)
                pg_mig_keys = {(r["app"], r["name"]) for r in pg_mig_rows}

                missing_in_target = src_mig_keys - pg_mig_keys
                if missing_in_target:
                    raise SchemaMismatchError(
                        f"Source contains migrations not applied in target PostgreSQL schema: {missing_in_target}. "
                        "Target schema must be migrated to at least the source migration state."
                    )

    def execute_import(self) -> TransferReport:
        """Execute transactional raw copy from SQLite to PostgreSQL.

        Verifies all deferred constraints and deterministic hashes INSIDE the transaction
        prior to committing. Rolls back immediately on any mismatch.
        """
        # 1. Pre-checks
        self.preflight_check()
        self.validate_schema()

        # 2. Get list of tables and dependency ordering
        with SqliteBackupReader(self.source_path) as reader:
            source_tables = set(reader.get_tables())

        pg_tables = set(self.pg.get_tables())
        # Do not attempt to load source-only empty tables that don't exist in target
        tables_to_load = source_tables & pg_tables

        fk_deps = self.pg.get_foreign_key_dependencies()
        ordered_tables = self._topological_sort_tables(tables_to_load, fk_deps)

        # 3. Transactional transfer
        conn = self.pg.connect()
        try:
            with conn.cursor() as cur:
                # Defer constraints where supported
                cur.execute("SET CONSTRAINTS ALL DEFERRED;")

                # Safely delete pre-existing bootstrap rows (empty DB post-migrate)
                self.pg.clear_bootstrap_rows(cur)

                with SqliteBackupReader(self.source_path) as reader:
                    for tbl in ordered_tables:
                        target_cols = self.pg.get_columns(tbl)
                        pk_col = self.pg.get_primary_key_column(tbl)

                        # Insert rows in batches
                        for batch in reader.stream_rows(tbl, batch_size=1000):
                            self.pg.insert_rows(cur, tbl, batch, target_cols)

                        # Reset sequence for PK if exists
                        if pk_col:
                            self.pg.reset_sequence(cur, tbl, pk_col)

                # Validate all deferred constraints immediately before checking hashes
                cur.execute("SET CONSTRAINTS ALL IMMEDIATE;")

            # 4. In-transaction verification before commit
            report = self.verify()
            if report.overall_status != "VERIFIED_OK":
                raise TransferPreconditionError(
                    f"In-transaction verification failed: {report.errors}. Rolling back."
                )

            # Commit the transaction only when constraints and hashes are 100% verified
            conn.commit()
            return report
        except Exception:
            conn.rollback()
            raise

    def verify(self) -> TransferReport:
        """Perform verification and compute deterministic hashes across all tables."""
        errors: list[str] = []
        table_reports: dict[str, dict[str, Any]] = {}

        # 1. Check SQLite integrity
        with SqliteBackupReader(self.source_path) as reader:
            try:
                reader.check_integrity()
                integrity_str = "OK"
                fk_str = "OK"
            except Exception as err:
                integrity_str = f"ERROR: {err}"
                fk_str = "ERROR"
                errors.append(str(err))

            source_tables = reader.get_tables()

        pg_tables = set(self.pg.get_tables())

        for tbl in source_tables:
            if tbl not in pg_tables:
                table_reports[tbl] = {
                    "source_count": -1,
                    "target_count": -1,
                    "source_hash": "",
                    "target_hash": "",
                    "status": "MISSING_IN_TARGET",
                }
                errors.append(f"Table '{tbl}' missing in target PostgreSQL.")
                continue

            pg_cols = self.pg.get_columns(tbl)
            col_types = {col: meta.udt_name for col, meta in pg_cols.items()}

            # Stream and hash source
            src_row_hashes: list[str] = []
            src_cnt = 0
            with SqliteBackupReader(self.source_path) as reader:
                src_cnt = reader.count_rows(tbl)
                for batch in reader.stream_rows(tbl, batch_size=1000):
                    for row in batch:
                        src_row_hashes.append(compute_row_hash(row, col_types))
            src_hash = compute_table_hash(src_row_hashes)

            # Stream and hash target
            tgt_row_hashes: list[str] = []
            tgt_cnt = self.pg.count_rows(tbl)
            for batch in self.pg.stream_rows(tbl, batch_size=1000):
                for row in batch:
                    tgt_row_hashes.append(compute_row_hash(row, col_types))
            tgt_hash = compute_table_hash(tgt_row_hashes)

            # Determine status
            if src_cnt != tgt_cnt:
                status = "COUNT_MISMATCH"
                errors.append(f"Table '{tbl}' count mismatch: source={src_cnt}, target={tgt_cnt}")
            elif src_hash != tgt_hash:
                status = "HASH_MISMATCH"
                errors.append(f"Table '{tbl}' hash mismatch despite matching row counts ({src_cnt}).")
            else:
                status = "MATCH"

            table_reports[tbl] = {
                "source_count": src_cnt,
                "target_count": tgt_cnt,
                "source_hash": src_hash,
                "target_hash": tgt_hash,
                "status": status,
            }

        # Check target-only tables: if any contain records, flag as error
        for tbl in pg_tables:
            if tbl not in source_tables:
                cnt = self.pg.count_rows(tbl)
                if cnt > 0:
                    table_reports[tbl] = {
                        "source_count": 0,
                        "target_count": cnt,
                        "source_hash": "",
                        "target_hash": "",
                        "status": "TARGET_ONLY_NON_EMPTY",
                    }
                    errors.append(
                        f"Target PostgreSQL contains extra non-empty table '{tbl}' ({cnt} rows) not in source SQLite."
                    )

        overall_status = "VERIFIED_OK" if not errors else "VERIFIED_MISMATCH"

        return TransferReport(
            source_path=str(self.source_path),
            target_info=self.pg.get_masked_connection_info(),
            integrity_check=integrity_str,
            foreign_key_check=fk_str,
            overall_status=overall_status,
            tables=table_reports,
            errors=errors,
        )
