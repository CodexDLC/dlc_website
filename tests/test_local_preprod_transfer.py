"""Tests for local preprod transfer tool (SQLite -> PostgreSQL).

Uses synthetic SQLite databases and mocks for unit tests.
Optionally runs real integration test if explicit TEST_DATABASE_URL is provided.
Never touches application databases, data/, or secrets.
"""

import json
import os
import sqlite3
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.local_preprod.cli import main as cli_main
from scripts.local_preprod.normalization import (
    canonical_column_bytes,
    compute_row_hash,
    compute_table_hash,
    convert_value_for_postgres,
)
from scripts.local_preprod.orchestrator import (
    PreprodTransferOrchestrator,
    SchemaMismatchError,
)
from scripts.local_preprod.postgres_adapter import (
    InvalidTargetHostError,
    PostgresAdapter,
    PostgresColumn,
    TargetDatabaseNotEmptyError,
)
from scripts.local_preprod.sqlite_reader import (
    SqliteBackupReader,
    SqliteForeignKeyError,
    SqliteIntegrityError,
)


@pytest.fixture
def synthetic_sqlite_db(tmp_path: Path) -> Path:
    """Create a synthetic SQLite database with representative types, keys, and bootstrap tables."""
    db_file = tmp_path / "synthetic_backup.sqlite3"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys = ON;")

    # 1. Django bootstrap tables
    cur.execute(
        """
        CREATE TABLE django_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            applied DATETIME NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE django_content_type (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_label VARCHAR(100) NOT NULL,
            model VARCHAR(100) NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE auth_permission (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL,
            content_type_id INTEGER NOT NULL REFERENCES django_content_type(id),
            codename VARCHAR(100) NOT NULL
        );
        """
    )

    # 2. Business tables with diverse types
    cur.execute(
        """
        CREATE TABLE test_business_entity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid_col VARCHAR(36) NOT NULL,
            is_active INTEGER NOT NULL,
            metadata_json TEXT,
            amount_decimal VARCHAR(30) NOT NULL,
            secret_cipher TEXT NOT NULL,
            pbkdf_hash TEXT NOT NULL,
            created_at DATETIME NOT NULL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE test_business_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL REFERENCES test_business_entity(id),
            title VARCHAR(100) NOT NULL
        );
        """
    )

    # Insert synthetic rows
    cur.execute(
        "INSERT INTO django_migrations (id, app, name, applied) "
        "VALUES (1, 'core', '0001_initial', '2026-10-01 10:00:00');"
    )
    cur.execute(
        "INSERT INTO django_content_type (id, app_label, model) VALUES (1, 'staff', 'employee');"
    )
    cur.execute(
        "INSERT INTO auth_permission (id, name, content_type_id, codename) "
        "VALUES (1, 'Can add employee', 1, 'add_employee');"
    )

    cur.execute(
        """
        INSERT INTO test_business_entity (
            id, uuid_col, is_active, metadata_json, amount_decimal, secret_cipher, pbkdf_hash, created_at
        ) VALUES (
            10,
            'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
            1,
            '{"flags": [1, 2], "active": true}',
            '1234.50',
            'enc:v1:aes-gcm:abc123encrypted==',
            'pbkdf2_sha256$260000$saltsalt$fakehashedvalue==',
            '2026-10-04 12:00:00'
        );
        """
    )
    cur.execute("INSERT INTO test_business_item (id, entity_id, title) VALUES (100, 10, 'Item A');")

    conn.commit()
    conn.close()
    return db_file


# ---------------------------------------------------------------------------
# Unit Tests: SqliteBackupReader
# ---------------------------------------------------------------------------


def test_sqlite_reader_healthy(synthetic_sqlite_db: Path) -> None:
    with SqliteBackupReader(synthetic_sqlite_db) as reader:
        reader.check_integrity()
        tables = reader.get_tables()
        assert "sqlite_sequence" not in tables
        assert "django_migrations" in tables
        assert "test_business_entity" in tables
        assert reader.count_rows("test_business_entity") == 1

        rows = list(reader.stream_rows("test_business_entity"))
        assert len(rows) == 1
        assert rows[0][0]["id"] == 10
        assert rows[0][0]["secret_cipher"] == "enc:v1:aes-gcm:abc123encrypted=="  # noqa: S105


def test_sqlite_reader_missing_file(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist.sqlite3"
    with pytest.raises(FileNotFoundError):
        SqliteBackupReader(non_existent)


def test_sqlite_reader_foreign_key_violation(tmp_path: Path) -> None:
    bad_db = tmp_path / "fk_corrupt.sqlite3"
    conn = sqlite3.connect(str(bad_db))
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF;")
    cur.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY);")
    cur.execute("CREATE TABLE child (id INTEGER PRIMARY KEY, p_id INTEGER REFERENCES parent(id));")
    cur.execute("INSERT INTO child (id, p_id) VALUES (1, 999);")  # orphaned FK
    conn.commit()
    conn.close()

    with SqliteBackupReader(bad_db) as reader:
        with pytest.raises(SqliteForeignKeyError) as exc_info:
            reader.check_integrity()
        assert "violation(s)" in str(exc_info.value)


def test_sqlite_reader_corrupt_integrity(tmp_path: Path) -> None:
    corrupt_db = tmp_path / "corrupt.sqlite3"
    # Write garbage header
    corrupt_db.write_bytes(b"SQLite format 3\x00" + b"\xFF" * 1000)

    with SqliteBackupReader(corrupt_db) as reader:
        with pytest.raises((SqliteIntegrityError, sqlite3.DatabaseError)):
            reader.check_integrity()


# ---------------------------------------------------------------------------
# Unit Tests: PostgresAdapter
# ---------------------------------------------------------------------------


def test_postgres_adapter_rejects_remote_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_PG_DSN", "postgresql://user:pass@192.168.1.50:5432/db")
    with pytest.raises(InvalidTargetHostError) as exc_info:
        PostgresAdapter(env_var_name="TEST_PG_DSN")
    assert "NOT a local loopback address" in str(exc_info.value)

    monkeypatch.setenv("TEST_PG_DSN", "postgresql://user:pass@remote.cloud.provider:5432/db")
    with pytest.raises(InvalidTargetHostError):
        PostgresAdapter(env_var_name="TEST_PG_DSN")


def test_postgres_adapter_rejects_remote_hostaddr(monkeypatch: pytest.MonkeyPatch) -> None:
    # Even if host is localhost, remote hostaddr must be rejected
    monkeypatch.setenv("TEST_PG_DSN", "host=localhost hostaddr=192.168.1.55 dbname=db user=u")
    with pytest.raises(InvalidTargetHostError) as exc_info:
        PostgresAdapter(env_var_name="TEST_PG_DSN")
    assert "NOT a local loopback address" in str(exc_info.value)


def test_postgres_adapter_rejects_malformed_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_PG_DSN", "not_a_valid_dsn_::::////???")
    with pytest.raises(InvalidTargetHostError):
        PostgresAdapter(env_var_name="TEST_PG_DSN")


def test_postgres_adapter_accepts_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_PG_DSN", "postgresql://user:secret@127.0.0.1:5432/testdb")
    adapter = PostgresAdapter(env_var_name="TEST_PG_DSN")
    # Verify password is masked
    info = adapter.get_masked_connection_info()
    assert "secret" not in info
    assert "127.0.0.1" in info


def test_postgres_adapter_rejects_non_empty_business_tables() -> None:
    adapter = PostgresAdapter.__new__(PostgresAdapter)
    adapter.get_tables = MagicMock(return_value=["django_migrations", "auth_user", "features_item"])  # type: ignore

    def mock_count(tbl: str) -> int:
        if tbl == "django_migrations":
            return 5  # bootstrap allowed
        if tbl == "auth_user":
            return 2  # business table with rows -> must abort!
        return 0

    adapter.count_rows = MagicMock(side_effect=mock_count)  # type: ignore

    with pytest.raises(TargetDatabaseNotEmptyError) as exc:
        adapter.check_target_is_clean()
    assert "auth_user: 2 rows" in str(exc.value)


# ---------------------------------------------------------------------------
# Unit Tests: Normalization & Deterministic Hashing
# ---------------------------------------------------------------------------


def test_convert_value_for_postgres() -> None:
    # Boolean
    assert convert_value_for_postgres(1, "bool", "is_active") is True
    assert convert_value_for_postgres(0, "bool", "is_active") is False
    assert convert_value_for_postgres("true", "bool", "is_active") is True

    # Decimal
    dec = convert_value_for_postgres("123.45", "numeric", "amount")
    assert isinstance(dec, Decimal)
    assert dec == Decimal("123.45")

    # UUID
    uid_str = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    assert convert_value_for_postgres(uid_str, "uuid", "uid") == uid_str

    # JSON
    json_val = convert_value_for_postgres('{"key": 123}', "jsonb", "data")
    assert json_val.adapted == {"key": 123}

    # Raw string preserving PBKDF hash & ciphertext
    hash_str = "pbkdf2_sha256$260000$salt$hash=="
    assert convert_value_for_postgres(hash_str, "varchar", "password") == hash_str


def test_convert_value_for_postgres_boolean_safety() -> None:
    # Unexpected strings must NOT silently evaluate to True
    with pytest.raises(ValueError) as exc:
        convert_value_for_postgres("invalid_bool", "bool", "is_active")
    assert "Invalid boolean representation" in str(exc.value)
    # Ensure sensitive value is NOT in error message
    assert "invalid_bool" not in str(exc.value)


def test_error_messages_do_not_leak_values() -> None:
    # Invalid Decimal: error must not leak the raw string
    with pytest.raises(ValueError) as exc_dec:
        convert_value_for_postgres("sensitive_bad_decimal_val", "numeric", "amount")
    assert "sensitive_bad_decimal_val" not in str(exc_dec.value)

    # Invalid UUID: error must not leak the raw string
    with pytest.raises(ValueError) as exc_uuid:
        convert_value_for_postgres("sensitive_bad_uuid_val", "uuid", "secret_id")
    assert "sensitive_bad_uuid_val" not in str(exc_uuid.value)

    # Invalid JSON: error must not leak the raw string
    with pytest.raises(ValueError) as exc_json:
        convert_value_for_postgres("{broken: sensitive_json", "jsonb", "payload")
    assert "sensitive_json" not in str(exc_json.value)


def test_canonical_column_bytes_stability() -> None:
    # Decimal normalization (12.30 vs 12.3)
    b1 = canonical_column_bytes("12.30", "numeric")
    b2 = canonical_column_bytes(Decimal("12.3"), "numeric")
    assert b1 == b2 == b"12.3"

    # JSON key sorting
    j1 = canonical_column_bytes('{"b": 2, "a": 1}', "jsonb")
    j2 = canonical_column_bytes({"a": 1, "b": 2}, "jsonb")
    assert j1 == j2 == b'{"a":1,"b":2}'

    # UUID lowercase
    u1 = canonical_column_bytes("A0EEBC99-9C0B-4EF8-BB6D-6BB9BD380A11", "uuid")
    u2 = canonical_column_bytes("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", "uuid")
    assert u1 == u2 == b"a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


def test_canonical_datetime_naive_utc_and_aware_utc_parity() -> None:
    from datetime import datetime, timezone

    # Django stores naive timestamps in UTC in SQLite: '2026-10-04 12:00:00'
    # PostgreSQL with timestamptz yields aware UTC: datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
    sqlite_str = "2026-10-04 12:00:00"
    pg_aware = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
    pg_str_z = "2026-10-04T12:00:00Z"
    pg_str_offset = "2026-10-04T12:00:00+00:00"

    h1 = canonical_column_bytes(sqlite_str, "timestamp")
    h2 = canonical_column_bytes(pg_aware, "timestamptz")
    h3 = canonical_column_bytes(pg_str_z, "timestamptz")
    h4 = canonical_column_bytes(pg_str_offset, "timestamptz")

    assert h1 == h2 == h3 == h4

    # Microseconds precision must be preserved
    s_micro = "2026-10-04 12:00:00.123450"
    pg_micro = datetime(2026, 10, 4, 12, 0, 0, 123450, tzinfo=timezone.utc)
    assert canonical_column_bytes(s_micro, "timestamp") == canonical_column_bytes(pg_micro, "timestamptz")

    # Truly different timestamps must differ
    h_diff = canonical_column_bytes("2026-10-04 12:00:01", "timestamp")
    assert h1 != h_diff


def test_row_and_table_hashing() -> None:
    col_types = {"id": "int4", "amount": "numeric", "is_active": "bool"}
    row1 = {"id": 1, "amount": "50.00", "is_active": 1}
    row2 = {"id": 1, "amount": Decimal("50"), "is_active": True}

    h1 = compute_row_hash(row1, col_types)
    h2 = compute_row_hash(row2, col_types)
    assert h1 == h2

    th1 = compute_table_hash([h1])
    th2 = compute_table_hash([h2])
    assert th1 == th2


# ---------------------------------------------------------------------------
# Unit Tests: Orchestrator Logic
# ---------------------------------------------------------------------------


def test_orchestrator_topological_sort() -> None:
    adapter = MagicMock(spec=PostgresAdapter)
    orchestrator = PreprodTransferOrchestrator(source_path="dummy.sqlite", postgres_adapter=adapter)

    tables = {"auth_permission", "django_content_type", "order_item", "order", "django_migrations"}
    fk_deps = [
        ("auth_permission", "django_content_type"),
        ("order_item", "order"),
    ]

    sorted_tables = orchestrator._topological_sort_tables(tables, fk_deps)

    # Bootstrap tables must be first
    assert sorted_tables[0] == "django_content_type"
    assert sorted_tables[1] == "auth_permission"
    assert sorted_tables[2] == "django_migrations"

    # Parents must come before children
    assert sorted_tables.index("order") < sorted_tables.index("order_item")


def test_orchestrator_schema_mismatch_missing_table(synthetic_sqlite_db: Path) -> None:
    adapter = MagicMock(spec=PostgresAdapter)
    # Target postgres is missing test_business_entity
    adapter.get_tables.return_value = ["django_migrations", "django_content_type", "auth_permission"]

    def mock_get_columns(tbl: str) -> dict[str, PostgresColumn]:
        if tbl == "django_migrations":
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "app": PostgresColumn("app", "varchar", "varchar", False, None),
                "name": PostgresColumn("name", "varchar", "varchar", False, None),
                "applied": PostgresColumn("applied", "timestamp", "timestamp", False, None),
            }
        if tbl == "django_content_type":
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "app_label": PostgresColumn("app_label", "varchar", "varchar", False, None),
                "model": PostgresColumn("model", "varchar", "varchar", False, None),
            }
        if tbl == "auth_permission":
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "name": PostgresColumn("name", "varchar", "varchar", False, None),
                "content_type_id": PostgresColumn("content_type_id", "integer", "int4", False, None),
                "codename": PostgresColumn("codename", "varchar", "varchar", False, None),
            }
        return {}

    adapter.get_columns.side_effect = mock_get_columns

    orchestrator = PreprodTransferOrchestrator(
        source_path=synthetic_sqlite_db, postgres_adapter=adapter
    )
    with pytest.raises(SchemaMismatchError) as exc:
        orchestrator.validate_schema()
    assert "test_business_entity" in str(exc.value)


def test_orchestrator_schema_mismatch_missing_column(synthetic_sqlite_db: Path) -> None:
    adapter = MagicMock(spec=PostgresAdapter)
    adapter.get_tables.return_value = [
        "django_migrations",
        "django_content_type",
        "auth_permission",
        "test_business_entity",
        "test_business_item",
    ]

    def mock_get_columns(tbl: str) -> dict[str, PostgresColumn]:
        if tbl == "django_migrations":
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "app": PostgresColumn("app", "varchar", "varchar", False, None),
                "name": PostgresColumn("name", "varchar", "varchar", False, None),
                "applied": PostgresColumn("applied", "timestamp", "timestamp", False, None),
            }
        if tbl == "django_content_type":
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "app_label": PostgresColumn("app_label", "varchar", "varchar", False, None),
                "model": PostgresColumn("model", "varchar", "varchar", False, None),
            }
        if tbl == "auth_permission":
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "name": PostgresColumn("name", "varchar", "varchar", False, None),
                "content_type_id": PostgresColumn("content_type_id", "integer", "int4", False, None),
                "codename": PostgresColumn("codename", "varchar", "varchar", False, None),
            }
        if tbl == "test_business_entity":
            # Missing 'secret_cipher' column
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "uuid_col": PostgresColumn("uuid_col", "character varying", "varchar", False, None),
                "is_active": PostgresColumn("is_active", "boolean", "bool", False, None),
                "metadata_json": PostgresColumn("metadata_json", "jsonb", "jsonb", True, None),
                "amount_decimal": PostgresColumn("amount_decimal", "numeric", "numeric", False, None),
                "pbkdf_hash": PostgresColumn("pbkdf_hash", "character varying", "varchar", False, None),
                "created_at": PostgresColumn("created_at", "timestamp", "timestamp", False, None),
            }
        return {}

    adapter.get_columns.side_effect = mock_get_columns

    orchestrator = PreprodTransferOrchestrator(
        source_path=synthetic_sqlite_db, postgres_adapter=adapter
    )
    with pytest.raises(SchemaMismatchError) as exc:
        orchestrator.validate_schema()
    assert "secret_cipher" in str(exc.value)


def test_orchestrator_schema_mismatch_target_extra_column(synthetic_sqlite_db: Path) -> None:
    adapter = MagicMock(spec=PostgresAdapter)
    adapter.get_tables.return_value = [
        "django_migrations",
        "django_content_type",
        "auth_permission",
        "test_business_entity",
        "test_business_item",
    ]

    def mock_get_columns(tbl: str) -> dict[str, PostgresColumn]:
        if tbl == "django_migrations":
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "app": PostgresColumn("app", "varchar", "varchar", False, None),
                "name": PostgresColumn("name", "varchar", "varchar", False, None),
                "applied": PostgresColumn("applied", "timestamp", "timestamp", False, None),
            }
        if tbl == "django_content_type":
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "app_label": PostgresColumn("app_label", "varchar", "varchar", False, None),
                "model": PostgresColumn("model", "varchar", "varchar", False, None),
            }
        if tbl == "auth_permission":
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "name": PostgresColumn("name", "varchar", "varchar", False, None),
                "content_type_id": PostgresColumn("content_type_id", "integer", "int4", False, None),
                "codename": PostgresColumn("codename", "varchar", "varchar", False, None),
            }
        if tbl == "test_business_entity":
            return {
                "id": PostgresColumn("id", "integer", "int4", False, None),
                "uuid_col": PostgresColumn("uuid_col", "character varying", "varchar", False, None),
                "is_active": PostgresColumn("is_active", "boolean", "bool", False, None),
                "metadata_json": PostgresColumn("metadata_json", "jsonb", "jsonb", True, None),
                "amount_decimal": PostgresColumn("amount_decimal", "numeric", "numeric", False, None),
                "secret_cipher": PostgresColumn("secret_cipher", "text", "text", False, None),
                "pbkdf_hash": PostgresColumn("pbkdf_hash", "character varying", "varchar", False, None),
                "created_at": PostgresColumn("created_at", "timestamp", "timestamp", False, None),
                # Extra target column
                "untracked_new_field": PostgresColumn("untracked_new_field", "varchar", "varchar", True, "'dflt'"),
            }
        return {}

    adapter.get_columns.side_effect = mock_get_columns

    orchestrator = PreprodTransferOrchestrator(
        source_path=synthetic_sqlite_db, postgres_adapter=adapter
    )
    with pytest.raises(SchemaMismatchError) as exc:
        orchestrator.validate_schema()
    assert "untracked_new_field" in str(exc.value)


def test_orchestrator_execute_import_success(synthetic_sqlite_db: Path) -> None:
    adapter = MagicMock(spec=PostgresAdapter)
    adapter.get_tables.return_value = [
        "django_migrations",
        "django_content_type",
        "auth_permission",
        "test_business_entity",
        "test_business_item",
    ]
    adapter.get_columns.return_value = {
        "id": PostgresColumn("id", "integer", "int4", False, None),
    }
    adapter.get_primary_key_column.return_value = "id"
    adapter.get_foreign_key_dependencies.return_value = [
        ("auth_permission", "django_content_type"),
        ("test_business_item", "test_business_entity"),
    ]

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    adapter.connect.return_value = mock_conn

    orchestrator = PreprodTransferOrchestrator(
        source_path=synthetic_sqlite_db, postgres_adapter=adapter
    )
    # Bypass schema check in execution unit test
    orchestrator.validate_schema = MagicMock()  # type: ignore

    mock_report = MagicMock()
    mock_report.overall_status = "VERIFIED_OK"
    mock_report.errors = []
    orchestrator.verify = MagicMock(return_value=mock_report)  # type: ignore

    orchestrator.execute_import()

    # Verify bootstrap clearing
    adapter.clear_bootstrap_rows.assert_called_once_with(mock_cur)
    # Verify set constraints deferred & immediate
    mock_cur.execute.assert_any_call("SET CONSTRAINTS ALL DEFERRED;")
    mock_cur.execute.assert_any_call("SET CONSTRAINTS ALL IMMEDIATE;")
    # Verify insert called for all tables
    assert adapter.insert_rows.call_count >= 5
    # Verify sequences reset
    assert adapter.reset_sequence.call_count >= 5
    # Verify transaction commit
    mock_conn.commit.assert_called_once()
    mock_conn.rollback.assert_not_called()


def test_orchestrator_execute_import_rollback_on_hash_mismatch(synthetic_sqlite_db: Path) -> None:
    from scripts.local_preprod.orchestrator import TransferPreconditionError

    adapter = MagicMock(spec=PostgresAdapter)
    adapter.get_tables.return_value = ["django_migrations", "django_content_type", "auth_permission"]
    adapter.get_columns.return_value = {"id": PostgresColumn("id", "integer", "int4", False, None)}
    adapter.get_primary_key_column.return_value = "id"
    adapter.get_foreign_key_dependencies.return_value = []

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    adapter.connect.return_value = mock_conn

    orchestrator = PreprodTransferOrchestrator(
        source_path=synthetic_sqlite_db, postgres_adapter=adapter
    )
    orchestrator.validate_schema = MagicMock()  # type: ignore

    # Simulate hash mismatch inside transaction
    mismatch_report = MagicMock()
    mismatch_report.overall_status = "VERIFIED_MISMATCH"
    mismatch_report.errors = ["Hash mismatch in auth_permission"]
    orchestrator.verify = MagicMock(return_value=mismatch_report)  # type: ignore

    with pytest.raises(TransferPreconditionError) as exc:
        orchestrator.execute_import()
    assert "In-transaction verification failed" in str(exc.value)

    # Must rollback and NOT commit
    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()


def test_orchestrator_verify_flags_target_only_nonempty_tables(synthetic_sqlite_db: Path) -> None:
    adapter = MagicMock(spec=PostgresAdapter)
    # Target postgres has an extra table
    adapter.get_tables.return_value = [
        "django_migrations",
        "django_content_type",
        "auth_permission",
        "test_business_entity",
        "test_business_item",
        "extra_target_only_table",
    ]
    adapter.get_columns.return_value = {"id": PostgresColumn("id", "integer", "int4", False, None)}
    adapter.get_primary_key_column.return_value = "id"
    adapter.count_rows.side_effect = lambda t: 5 if t == "extra_target_only_table" else 1
    adapter.stream_rows.return_value = iter([])

    orchestrator = PreprodTransferOrchestrator(
        source_path=synthetic_sqlite_db, postgres_adapter=adapter
    )
    report = orchestrator.verify()
    assert report.overall_status == "VERIFIED_MISMATCH"
    assert "extra_target_only_table" in report.tables
    assert report.tables["extra_target_only_table"]["status"] == "TARGET_ONLY_NON_EMPTY"


def test_orchestrator_execute_import_rollback_on_error(synthetic_sqlite_db: Path) -> None:
    adapter = MagicMock(spec=PostgresAdapter)
    adapter.get_tables.return_value = [
        "django_migrations",
        "django_content_type",
        "auth_permission",
        "test_business_entity",
        "test_business_item",
    ]
    adapter.get_columns.return_value = {
        "id": PostgresColumn("id", "integer", "int4", False, None),
    }
    adapter.get_primary_key_column.return_value = "id"
    adapter.get_foreign_key_dependencies.return_value = []

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    adapter.connect.return_value = mock_conn
    # Simulate DB error during insertion
    adapter.insert_rows.side_effect = RuntimeError("Simulated DB connection drop")

    orchestrator = PreprodTransferOrchestrator(
        source_path=synthetic_sqlite_db, postgres_adapter=adapter
    )
    orchestrator.validate_schema = MagicMock()  # type: ignore

    with pytest.raises(RuntimeError) as exc:
        orchestrator.execute_import()
    assert "Simulated DB connection drop" in str(exc.value)

    # Verify transaction rolled back
    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Unit Tests: CLI Guards & Execution
# ---------------------------------------------------------------------------


def test_cli_requires_action_flag(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr("sys.argv", ["cli.py", "--source-sqlite", "test.db"])
    with pytest.raises(SystemExit):
        cli_main()


def test_cli_mutually_exclusive_flags(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["cli.py", "--source-sqlite", "test.db", "--verify-only", "--confirm-import"],
    )
    with pytest.raises(SystemExit):
        cli_main()


def test_cli_missing_source(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["cli.py", "--source-sqlite", "non_existent.db", "--verify-only"],
    )
    ret = cli_main()
    assert ret == 1
    captured = capsys.readouterr()
    assert "Source SQLite backup not found" in captured.err


def test_cli_verify_only_json_output(
    synthetic_sqlite_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    from scripts.local_preprod.orchestrator import TransferReport

    out_json = tmp_path / "report.json"
    monkeypatch.setenv("TEST_LOOPBACK_DSN", "postgresql://user:pw@127.0.0.1:5432/db")

    with patch("scripts.local_preprod.cli.PostgresAdapter") as mock_adapter_cls:
        adapter_inst = MagicMock()
        mock_adapter_cls.return_value = adapter_inst

        with patch("scripts.local_preprod.cli.PreprodTransferOrchestrator") as mock_orch_cls:
            orch_inst = MagicMock()
            mock_orch_cls.return_value = orch_inst

            report_obj = TransferReport(
                source_path=str(synthetic_sqlite_db),
                target_info="host=127.0.0.1 dbname=db user=user",
                integrity_check="OK",
                foreign_key_check="OK",
                overall_status="VERIFIED_OK",
                tables={},
                errors=[],
            )
            orch_inst.verify.return_value = report_obj

            monkeypatch.setattr(
                "sys.argv",
                [
                    "cli.py",
                    "--source-sqlite",
                    str(synthetic_sqlite_db),
                    "--target-env-var",
                    "TEST_LOOPBACK_DSN",
                    "--verify-only",
                    "--output-json",
                    str(out_json),
                ],
            )
            ret = cli_main()
            assert ret == 0
            assert out_json.exists()
            data = json.loads(out_json.read_text(encoding="utf-8"))
            assert data["overall_status"] == "VERIFIED_OK"
            # execute_import must NOT be called in verify-only mode
            orch_inst.execute_import.assert_not_called()


# ---------------------------------------------------------------------------
# Optional Integration Test with dedicated isolated PREPROD_TRANSFER_TEST_DSN
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("PREPROD_TRANSFER_TEST_DSN"),
    reason="Explicit isolated PREPROD_TRANSFER_TEST_DSN required for PostgreSQL integration test.",
)
def test_full_sqlite_to_postgres_integration(synthetic_sqlite_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_dsn = os.environ["PREPROD_TRANSFER_TEST_DSN"]
    # Safety guard: ensure this is explicitly an isolated test database with name containing test_transfer_
    if "test_transfer_" not in test_dsn:
        pytest.fail(
            "PREPROD_TRANSFER_TEST_DSN must point to an isolated database name containing 'test_transfer_' "
            "to prevent accidental dropping of Django test or application tables."
        )

    monkeypatch.setenv("INTEGRATION_TEST_PG_DSN", test_dsn)

    adapter = PostgresAdapter(env_var_name="INTEGRATION_TEST_PG_DSN")
    conn = adapter.connect()

    # Setup tables in dedicated test database
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS test_business_item CASCADE;")
        cur.execute("DROP TABLE IF EXISTS test_business_entity CASCADE;")
        cur.execute("DROP TABLE IF EXISTS auth_permission CASCADE;")
        cur.execute("DROP TABLE IF EXISTS django_content_type CASCADE;")
        cur.execute("DROP TABLE IF EXISTS django_migrations CASCADE;")

        cur.execute(
            """
            CREATE TABLE django_migrations (
                id SERIAL PRIMARY KEY,
                app VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                applied TIMESTAMP WITH TIME ZONE NOT NULL
            );
            CREATE TABLE django_content_type (
                id SERIAL PRIMARY KEY,
                app_label VARCHAR(100) NOT NULL,
                model VARCHAR(100) NOT NULL
            );
            CREATE TABLE auth_permission (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                content_type_id INTEGER NOT NULL REFERENCES django_content_type(id),
                codename VARCHAR(100) NOT NULL
            );
            CREATE TABLE test_business_entity (
                id SERIAL PRIMARY KEY,
                uuid_col UUID NOT NULL,
                is_active BOOLEAN NOT NULL,
                metadata_json JSONB,
                amount_decimal NUMERIC(10, 2) NOT NULL,
                secret_cipher TEXT NOT NULL,
                pbkdf_hash TEXT NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
            );
            CREATE TABLE test_business_item (
                id SERIAL PRIMARY KEY,
                entity_id INTEGER NOT NULL REFERENCES test_business_entity(id),
                title VARCHAR(100) NOT NULL
            );
            """
        )
        # Simulate Django bootstrap rows
        cur.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('core', '0001_initial', NOW());")
        cur.execute("INSERT INTO django_content_type (app_label, model) VALUES ('temp', 'bootstrap');")
        cur.execute("INSERT INTO auth_permission (name, content_type_id, codename) VALUES ('perm', 1, 'temp');")
    conn.commit()

    orchestrator = PreprodTransferOrchestrator(
        source_path=synthetic_sqlite_db, postgres_adapter=adapter
    )

    # 1. Execute transfer
    orchestrator.execute_import()

    # 2. Verify deterministic hashes match
    report = orchestrator.verify()
    assert report.overall_status == "VERIFIED_OK"
    assert report.tables["test_business_entity"]["status"] == "MATCH"
    assert report.tables["test_business_item"]["status"] == "MATCH"

    # 3. Verify sequence was reset properly: next insert should succeed without PK collision
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO test_business_entity (
                uuid_col, is_active, amount_decimal, secret_cipher, pbkdf_hash, created_at
            ) VALUES (
                'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
                false,
                99.99,
                'secret',
                'hash',
                NOW()
            ) RETURNING id;
            """
        )
        new_id = cur.fetchone()[0]
        # In synthetic SQLite, max id was 10. Next serial id should be 11.
        assert new_id > 10
    conn.commit()
