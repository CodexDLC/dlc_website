"""Command Line Interface for local preprod data transfer.

Ensures strict confirmation guard, supports --verify-only, and outputs structured JSON summaries.
"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .orchestrator import PreprodTransferOrchestrator
from .postgres_adapter import PostgresAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local preprod raw database transfer tool (SQLite -> PostgreSQL)."
    )
    parser.add_argument(
        "--source-sqlite",
        type=str,
        required=True,
        help="Path to the read-only backup SQLite database file.",
    )
    parser.add_argument(
        "--target-env-var",
        type=str,
        default="PREPROD_POSTGRES_DSN",
        help="Environment variable containing PostgreSQL DSN (defaults to PREPROD_POSTGRES_DSN).",
    )
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--confirm-import",
        action="store_true",
        default=False,
        help="Explicit confirmation flag to execute raw copy into target PostgreSQL.",
    )
    action_group.add_argument(
        "--verify-only",
        action="store_true",
        default=False,
        help="Read-only mode: compare schemas, row counts, and deterministic hashes without writing.",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write JSON verification report.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_path = Path(args.source_sqlite)
    if not source_path.exists():
        sys.stderr.write(f"ERROR: Source SQLite backup not found: {source_path}\n")
        return 1

    try:
        pg_adapter = PostgresAdapter(env_var_name=args.target_env_var)
    except Exception as err:
        sys.stderr.write(f"ERROR: Target adapter initialization failed ({type(err).__name__}).\n")
        return 1

    orchestrator = PreprodTransferOrchestrator(
        source_path=source_path,
        postgres_adapter=pg_adapter,
    )

    try:
        if args.confirm_import:
            sys.stdout.write("Starting raw data transfer from backup SQLite to PostgreSQL...\n")
            report = orchestrator.execute_import()
            sys.stdout.write("Import transaction committed successfully.\n")
        else:
            report = orchestrator.verify()

        report_data = asdict(report)
        report_json = json.dumps(report_data, indent=2, ensure_ascii=False)

        if args.output_json:
            out_file = Path(args.output_json)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(report_json, encoding="utf-8")
            sys.stdout.write(f"Verification report written to {out_file}\n")
        else:
            sys.stdout.write(report_json + "\n")

        if report.overall_status != "VERIFIED_OK":
            sys.stderr.write(f"Verification completed with status: {report.overall_status}\n")
            return 1

        sys.stdout.write("Operation completed successfully with 100% hash parity.\n")
        return 0

    except Exception as err:
        sys.stderr.write(f"Transfer failed ({type(err).__name__}). Sensitive error details withheld.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
