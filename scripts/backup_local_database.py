"""Consistent SQLite backup with integrity verification; never overwrites a backup."""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBSOLETE_TABLES = (
    "projects_project",
    "projects_projectsite",
    "projects_projectassignment",
    "ac_reporting_acdailyreport",
    "ac_reporting_acworkentry",
    "ac_reporting_acworktype",
    "ac_reporting_acweeklytimesheet",
    "ac_reporting_acbreak",
    "ac_reporting_acworkentryparticipant",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-empty-scaffold", action="store_true")
    args = parser.parse_args()
    source_path = ROOT / "data" / "db" / "dlc_montage.sqlite3"
    with sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True) as source:
        if args.check_empty_scaffold:
            existing = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            # Identifiers come only from the fixed OBSOLETE_TABLES allowlist above.
            counts = {
                name: source.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]  # noqa: S608
                for name in OBSOLETE_TABLES
                if name in existing
            }
            print("Scaffold rows:", counts)
            if any(counts.values()):
                raise SystemExit("Old scaffold contains data. Migration must not proceed.")
        target = source_path.with_name(f"{source_path.stem}-backup-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3")
        if target.exists():
            raise SystemExit("Backup already exists.")
        with sqlite3.connect(target) as backup:
            source.backup(backup)
            result = backup.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise SystemExit(f"Backup integrity failed: {result}")
        print(f"Verified backup: {target}")


if __name__ == "__main__":
    main()
