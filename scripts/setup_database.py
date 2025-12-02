"""Database bootstrap script for the shift scheduler application.

This utility ensures that the SQLite database has the required schema and
static master data (employment patterns and time slots). It can optionally
remove the existing database file to recreate it from scratch.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from shift_scheduler import (
    DB_PATH,
    init_database,
    list_employment_patterns,
    list_time_slots,
    reset_employment_patterns,
    reset_time_slots,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set up the shift scheduler database")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete the existing database file before initialising (if it exists)",
    )
    parser.add_argument(
        "--refresh-static",
        action="store_true",
        help="Re-seed employment patterns and time slots after initialisation",
    )
    parser.add_argument(
        "--refresh-patterns",
        action="store_true",
        help="Re-seed employment pattern master data",
    )
    parser.add_argument(
        "--refresh-time-slots",
        action="store_true",
        help="Re-seed time slot master data",
    )
    parser.add_argument(
        "--show-time-slots",
        action="store_true",
        help="Output a detailed summary of time slots after initialisation",
    )
    return parser.parse_args(argv)


def remove_existing_database() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database: {DB_PATH}")
    else:
        print("No existing database file found; nothing to remove")


def _summarise_time_slots(time_slots) -> None:
    grouped = defaultdict(list)
    for slot in time_slots:
        grouped[slot.day_of_week].append(slot)

    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    for day_index in sorted(grouped.keys()):
        label = weekdays[day_index] if day_index < len(weekdays) else str(day_index)
        print(f"\n[{label}曜]")
        for slot in sorted(grouped[day_index], key=lambda item: (item.area, item.start_time)):
            print(f"  {slot.area:6s} | {slot.start_time}-{slot.end_time} | {slot.display_name}")


def initialise_database(*, refresh_patterns: bool, refresh_time_slots: bool, show_time_slots: bool) -> None:
    init_database()
    print(f"Database initialised at: {DB_PATH}")

    if refresh_patterns:
        reset_employment_patterns()
        print("Employment patterns re-seeded")

    if refresh_time_slots:
        reset_time_slots()
        print("Time slots re-seeded")

    patterns = list_employment_patterns()
    time_slots = list_time_slots(active_only=False)
    print(f"Employment patterns: {len(patterns)} entries")
    print(f"Time slots: {len(time_slots)} entries")

    if show_time_slots:
        _summarise_time_slots(time_slots)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    refresh_patterns = args.refresh_patterns or args.refresh_static
    refresh_time_slots = args.refresh_time_slots or args.refresh_static

    print("=" * 60)
    print("Shift Scheduler - Database Setup")
    print("=" * 60)

    if args.force:
        remove_existing_database()

    initialise_database(
        refresh_patterns=refresh_patterns,
        refresh_time_slots=refresh_time_slots,
        show_time_slots=args.show_time_slots,
    )

    print("=" * 60)
    print("Done. You can now run: streamlit run main.py")


if __name__ == "__main__":
    main()
