#!/usr/bin/env python3
"""Migrate legacy OpenFlight .pkl capture files to secure JSON format.

Usage:
    # Migrate a single file
    python scripts/analysis/migrate_pickles.py session_logs/capture.pkl

    # Migrate all pickles in a directory
    python scripts/analysis/migrate_pickles.py session_logs/

    # Migrate and gzip compress (.json.gz)
    python scripts/analysis/migrate_pickles.py session_logs/ --compress
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from openflight.capture_io import migrate_pickle_to_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate legacy .pkl capture files to safe JSON format."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more .pkl files or directories containing .pkl files",
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="Emit gzipped JSON (.json.gz) instead of plain .json",
    )
    parser.add_argument(
        "--delete-source",
        action="store_true",
        help="Delete original .pkl file after successful migration",
    )
    args = parser.parse_args()

    pkl_files: list[Path] = []
    for p in args.paths:
        if p.is_file() and p.suffix.lower() == ".pkl":
            pkl_files.append(p)
        elif p.is_dir():
            pkl_files.extend(sorted(p.rglob("*.pkl")))
        else:
            print(f"Warning: path not found or not .pkl: {p}", file=sys.stderr)

    if not pkl_files:
        print("No .pkl files found to migrate.")
        return 0

    print(f"Found {len(pkl_files)} pickle capture file(s) to migrate...")
    migrated_count = 0
    errors = 0

    for pkl_file in pkl_files:
        try:
            target = migrate_pickle_to_json(pkl_file, compress=args.compress)
            old_kb = pkl_file.stat().st_size / 1024
            new_kb = target.stat().st_size / 1024
            print(f"  [OK] {pkl_file} ({old_kb:.1f} KB) -> {target.name} ({new_kb:.1f} KB)")
            if args.delete_source:
                pkl_file.unlink()
                print(f"       Deleted {pkl_file.name}")
            migrated_count += 1
        except Exception as exc:
            print(f"  [FAIL] {pkl_file}: {exc}", file=sys.stderr)
            errors += 1

    print(f"Migration complete: {migrated_count} succeeded, {errors} failed.")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
