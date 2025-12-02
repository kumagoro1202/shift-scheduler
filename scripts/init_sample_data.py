"""Seed the database with sample data for testing the scheduler."""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from shift_scheduler import (
    DB_PATH,
    create_employee,
    init_database,
    list_employees,
    record_absence,
    reset_employment_patterns,
    set_setting,
)

SAMPLE_EMPLOYEES = [
    {
        "name": "山田太郎",
        "employee_type": "TYPE_A",
        "employment_type": "正職員",
        "employment_pattern_id": "full_early",
        "skill_reha": 90,
        "skill_reception_am": 88,
        "skill_reception_pm": 85,
        "skill_general": 92,
    },
    {
        "name": "佐藤花子",
        "employee_type": "TYPE_A",
        "employment_type": "正職員",
        "employment_pattern_id": "full_early",
        "skill_reha": 82,
        "skill_reception_am": 84,
        "skill_reception_pm": 90,
        "skill_general": 86,
    },
    {
        "name": "鈴木一郎",
        "employee_type": "TYPE_B",
        "employment_type": "正職員",
        "employment_pattern_id": "full_early",
        "skill_reha": 0,
        "skill_reception_am": 95,
        "skill_reception_pm": 94,
        "skill_general": 80,
    },
    {
        "name": "田中美咲",
        "employee_type": "TYPE_C",
        "employment_type": "正職員",
        "employment_pattern_id": "full_late",
        "skill_reha": 92,
        "skill_reception_am": 0,
        "skill_reception_pm": 0,
        "skill_general": 78,
    },
    {
        "name": "高橋健太",
        "employee_type": "TYPE_D",
        "employment_type": "パート",
        "employment_pattern_id": "part_morning_early",
        "skill_reha": 70,
        "skill_reception_am": 0,
        "skill_reception_pm": 0,
        "skill_general": 60,
    },
    {
        "name": "伊藤さくら",
        "employee_type": "TYPE_D",
        "employment_type": "パート",
        "employment_pattern_id": "part_morning_early",
        "skill_reha": 76,
        "skill_reception_am": 0,
        "skill_reception_pm": 0,
        "skill_general": 65,
    },
    {
        "name": "中村陽介",
        "employee_type": "TYPE_A",
        "employment_type": "正職員",
        "employment_pattern_id": "full_early",
        "skill_reha": 80,
        "skill_reception_am": 72,
        "skill_reception_pm": 78,
        "skill_general": 84,
    },
    {
        "name": "三浦あかり",
        "employee_type": "TYPE_C",
        "employment_type": "正職員",
        "employment_pattern_id": "full_early",
        "skill_reha": 88,
        "skill_reception_am": 0,
        "skill_reception_pm": 0,
        "skill_general": 80,
    },
    {
        "name": "岡本真理",
        "employee_type": "TYPE_B",
        "employment_type": "正職員",
        "employment_pattern_id": "full_early",
        "skill_reha": 0,
        "skill_reception_am": 90,
        "skill_reception_pm": 93,
        "skill_general": 82,
    },
    {
        "name": "木村菜摘",
        "employee_type": "TYPE_A",
        "employment_type": "正職員",
        "employment_pattern_id": "short_time",
        "skill_reha": 74,
        "skill_reception_am": 70,
        "skill_reception_pm": 68,
        "skill_general": 76,
    },
    {
        "name": "小林直樹",
        "employee_type": "TYPE_A",
        "employment_type": "正職員",
        "employment_pattern_id": "full_early",
        "skill_reha": 86,
        "skill_reception_am": 80,
        "skill_reception_pm": 82,
        "skill_general": 88,
    },
    {
        "name": "吉田彩香",
        "employee_type": "TYPE_B",
        "employment_type": "正職員",
        "employment_pattern_id": "full_early",
        "skill_reha": 0,
        "skill_reception_am": 88,
        "skill_reception_pm": 91,
        "skill_general": 85,
    },
]

ABSENCE_TYPE_LABELS = {
    "full_day": "終日休暇",
    "morning": "午前休",
    "afternoon": "午後休",
}

SAMPLE_ABSENCES = [
    {"employee_index": 0, "date": date(2025, 12, 9), "absence_type": "afternoon", "reason": "通院"},
    {"employee_index": 0, "date": date(2026, 1, 6), "absence_type": "full_day", "reason": "年次有給休暇"},
    {"employee_index": 1, "date": date(2025, 12, 16), "absence_type": "morning", "reason": "健康診断"},
    {"employee_index": 1, "date": date(2026, 1, 15), "absence_type": "full_day", "reason": "家族行事"},
    {"employee_index": 2, "date": date(2025, 12, 27), "absence_type": "morning", "reason": "通院"},
    {"employee_index": 2, "date": date(2026, 1, 8), "absence_type": "afternoon", "reason": "研修"},
    {"employee_index": 3, "date": date(2025, 12, 24), "absence_type": "full_day", "reason": "子の看護休暇"},
    {"employee_index": 4, "date": date(2025, 12, 23), "absence_type": "morning", "reason": "家族行事"},
    {"employee_index": 5, "date": date(2026, 1, 5), "absence_type": "morning", "reason": "家族行事"},
    {"employee_index": 6, "date": date(2025, 12, 21), "absence_type": "afternoon", "reason": "研修参加"},
    {"employee_index": 6, "date": date(2026, 1, 13), "absence_type": "full_day", "reason": "年次有給休暇"},
    {"employee_index": 7, "date": date(2025, 12, 28), "absence_type": "morning", "reason": "通院"},
    {"employee_index": 8, "date": date(2026, 1, 3), "absence_type": "full_day", "reason": "私用"},
    {"employee_index": 9, "date": date(2025, 12, 30), "absence_type": "morning", "reason": "通院"},
    {"employee_index": 10, "date": date(2026, 1, 10), "absence_type": "afternoon", "reason": "自己研鑽"},
    {"employee_index": 11, "date": date(2025, 12, 26), "absence_type": "full_day", "reason": "年次有給休暇"},
]

TEMPLATE_VERSION = "2025-12-02-shiftcycle"

DIST_DB_PATH = REPO_ROOT / "data" / "shift.db"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the database with sample data")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing employees before inserting sample data",
    )
    return parser.parse_args(argv)


def clear_existing_employees() -> None:
    employees = list_employees(active_only=False)
    removed = len(employees)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM break_schedules")
        conn.execute("DELETE FROM shifts")
        conn.execute("DELETE FROM employee_absences")
        conn.execute("DELETE FROM employees")
        conn.commit()

    if removed:
        print(f"Removed {removed} existing employees")


def reset_sequences() -> None:
    """Reset autoincrement counters for deterministic IDs."""

    with sqlite3.connect(DB_PATH) as conn:
        for table in ("employees", "employee_absences", "shifts", "break_schedules"):
            conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        conn.commit()


def seed_sample_data(force: bool) -> bool:
    init_database()
    reset_employment_patterns()

    employees = list_employees(active_only=False)
    if employees and not force:
        prompt = (
            f"Detected {len(employees)} existing employees. Overwrite with sample data? (y/N): "
        )
        response = input(prompt)
        if response.lower() != "y":
            print("Cancelled")
            return False

    if employees:
        clear_existing_employees()
        reset_sequences()
    else:
        reset_sequences()

    print("Inserting sample employees...")
    inserted_ids: list[int] = []
    for payload in SAMPLE_EMPLOYEES:
        employee_id = create_employee(**payload)
        inserted_ids.append(employee_id)
        print(f"  Added {payload['name']} (id={employee_id})")

    print("Inserting sample absences...")
    for record in SAMPLE_ABSENCES:
        employee_index = record["employee_index"]
        employee_id = inserted_ids[employee_index]
        absence_date = record["date"]
        absence_type = record["absence_type"]
        reason = record["reason"]
        record_absence(
            employee_id=employee_id,
            date=absence_date.isoformat(),
            absence_type=absence_type,
            reason=reason,
        )
        employee_name = SAMPLE_EMPLOYEES[employee_index]["name"]
        absence_label = ABSENCE_TYPE_LABELS[absence_type]
        print(
            f"  Added absence for {employee_name}: {absence_label} on {absence_date.isoformat()}"
        )

    set_setting("template_version", TEMPLATE_VERSION)
    print(f"Recorded template version: {TEMPLATE_VERSION}")
    print("Sample data seeding completed")
    return True


def copy_seeded_database() -> Path:
    """Copy the seeded database into the distribution data folder."""

    DIST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, DIST_DB_PATH)
    return DIST_DB_PATH


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    print("=" * 60)
    print("Shift Scheduler - Sample Data Seeder")
    print("=" * 60)

    seeded = seed_sample_data(force=args.force)

    if seeded:
        copied_path = copy_seeded_database()
        print(f"Copied seeded database to: {copied_path}")

    print("=" * 60)
    print("Done. Launch the app with: streamlit run main.py")


if __name__ == "__main__":
    main()
