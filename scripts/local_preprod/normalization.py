"""Data normalization and deterministic hashing for preprod transfer.

Ensures strict PG typization and cross-database deterministic row/table hashing
without ever printing or logging raw values or personal data.
"""

import hashlib
import json
import uuid
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg2
import psycopg2.extras


def convert_value_for_postgres(
    val: Any, target_udt_type: str, column_name: str
) -> Any:
    """Convert SQLite value to appropriate Python/psycopg2 type for PostgreSQL."""
    if val is None:
        return None

    norm_type = target_udt_type.lower()

    # Boolean
    if norm_type in ("bool", "boolean"):
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            if val == 1:
                return True
            if val == 0:
                return False
            raise ValueError(f"Invalid boolean representation for column '{column_name}'")
        if isinstance(val, str):
            s = val.strip().lower()
            if s in ("1", "t", "true", "yes", "y"):
                return True
            if s in ("0", "f", "false", "no", "n"):
                return False
        raise ValueError(f"Invalid boolean representation for column '{column_name}'")

    # JSON / JSONB
    if norm_type in ("json", "jsonb"):
        if isinstance(val, (dict, list)):
            return psycopg2.extras.Json(val)
        if isinstance(val, str):
            val_str = val.strip()
            if not val_str:
                return None
            try:
                parsed = json.loads(val_str)
                return psycopg2.extras.Json(parsed)
            except json.JSONDecodeError as err:
                raise ValueError(
                    f"Invalid JSON syntax for column '{column_name}'"
                ) from err
        return psycopg2.extras.Json(val)

    # Numeric / Decimal
    if norm_type in ("numeric", "decimal"):
        if isinstance(val, Decimal):
            return val
        try:
            return Decimal(str(val).strip())
        except (InvalidOperation, ValueError) as err:
            raise ValueError(
                f"Invalid Decimal representation for column '{column_name}'"
            ) from err

    # UUID
    if norm_type == "uuid":
        if isinstance(val, uuid.UUID):
            return str(val)
        try:
            return str(uuid.UUID(str(val).strip()))
        except (ValueError, AttributeError) as err:
            raise ValueError(
                f"Invalid UUID representation for column '{column_name}'"
            ) from err

    # Timestamp / Datetime
    if norm_type in ("timestamp", "timestamptz"):
        if isinstance(val, datetime):
            return val
        return str(val)

    # Date
    if norm_type == "date":
        if isinstance(val, (date, datetime)):
            return val
        return str(val)

    # Time
    if norm_type in ("time", "timetz"):
        if isinstance(val, (time, datetime)):
            return val
        return str(val)

    # Bytea / Binary
    if norm_type == "bytea":
        if isinstance(val, bytes):
            return psycopg2.Binary(val)
        if isinstance(val, memoryview):
            return psycopg2.Binary(val.tobytes())
        return psycopg2.Binary(bytes(val))

    # Integer / BigInt / SmallInt
    if norm_type in ("int2", "int4", "int8", "smallint", "integer", "bigint"):
        return int(val)

    # Float / Double precision
    if norm_type in ("float4", "float8"):
        return float(val)

    # Text, Varchar, Ciphertext, PBKDF2 hashes - preserved verbatim
    return str(val)


def canonical_column_bytes(val: Any, target_udt_type: str = "") -> bytes:
    """Normalize any database value into deterministic canonical UTF-8 bytes for hashing."""
    if val is None:
        return b"\x00null\x00"

    norm_type = target_udt_type.lower()

    if norm_type in ("bool", "boolean") or isinstance(val, bool):
        if isinstance(val, str):
            b_val = val.strip().lower() in ("1", "t", "true", "yes", "y")
        else:
            b_val = bool(val)
        return b"true" if b_val else b"false"

    if norm_type in ("json", "jsonb"):
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
            except Exception:
                parsed = val
        else:
            parsed = val
        return json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    if norm_type in ("numeric", "decimal") or isinstance(val, Decimal):
        try:
            d = Decimal(str(val).strip())
            # Format cleanly: strip trailing zeros from fraction if decimal point exists
            s = f"{d:f}"
            if "." in s:
                s = s.rstrip("0").rstrip(".")
            return s.encode("utf-8")
        except Exception:
            return str(val).encode("utf-8")

    if norm_type == "uuid":
        try:
            return str(uuid.UUID(str(val).strip())).lower().encode("utf-8")
        except Exception:
            return str(val).lower().encode("utf-8")

    # Datetime / Timestamp
    if norm_type in ("timestamp", "timestamptz") or isinstance(val, datetime):
        dt = None
        if isinstance(val, str):
            s = val.strip()
            if " " in s and "T" not in s:
                s = s.replace(" ", "T")
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(s)
            except ValueError:
                return val.encode("utf-8")
        elif isinstance(val, datetime):
            dt = val

        if dt is not None:
            # Django naive timestamps in SQLite are UTC; aware timestamptz in Postgres are converted to UTC
            from datetime import timezone

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            base = dt.strftime("%Y-%m-%dT%H:%M:%S")
            if dt.microsecond:
                base += f".{dt.microsecond:06d}"
            base += "+00:00"
            return base.encode("utf-8")

    # Date (strictly not datetime)
    if norm_type == "date" or (isinstance(val, date) and not isinstance(val, datetime)):
        if isinstance(val, str):
            return val.strip()[:10].encode("utf-8")
        return val.strftime("%Y-%m-%d").encode("utf-8")

    # Time
    if norm_type in ("time", "timetz") or isinstance(val, time):
        t = None
        if isinstance(val, str):
            s = val.strip().split("+")[0]
            try:
                t = time.fromisoformat(s)
            except ValueError:
                return s.encode("utf-8")
        elif isinstance(val, time):
            t = val

        if t is not None:
            base = t.strftime("%H:%M:%S")
            if t.microsecond:
                base += f".{t.microsecond:06d}"
            return base.encode("utf-8")

    if isinstance(val, (bytes, memoryview)):
        return bytes(val).hex().encode("utf-8")

    if isinstance(val, int):
        return str(val).encode("utf-8")

    if isinstance(val, float):
        return f"{val:.8f}".rstrip("0").rstrip(".").encode("utf-8")

    # Raw string (PBKDF hashes, ciphertext, plain text)
    return str(val).encode("utf-8")


def compute_row_hash(row: dict[str, Any], column_types: dict[str, str]) -> str:
    """Compute SHA-256 hash of a single row deterministically based on column names."""
    hasher = hashlib.sha256()
    for col_name in sorted(row.keys()):
        hasher.update(col_name.encode("utf-8"))
        hasher.update(b":")
        col_type = column_types.get(col_name, "")
        hasher.update(canonical_column_bytes(row[col_name], col_type))
        hasher.update(b"|")
    return hasher.hexdigest()


def compute_table_hash(row_hashes: list[str]) -> str:
    """Compute deterministic SHA-256 hash of entire table from individual row hashes."""
    hasher = hashlib.sha256()
    for rh in sorted(row_hashes):
        hasher.update(rh.encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest()
