"""SQLite access layer for the shift scheduler application.

This module centralises all persistence logic so that the rest of the code base
can operate on Python domain objects defined in :mod:`shift_scheduler.models`.
The schema aligns with the V3.0 requirements (see docs/REQUIREMENTS.md).
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from .models import (
    Absence,
    BreakSchedule,
    Employee,
    EmploymentPattern,
    Shift,
    TimeSlot,
)

__all__ = [
    "DB_PATH",
    "get_connection",
    "init_database",
    "list_employees",
    "get_employee",
    "create_employee",
    "update_employee",
    "delete_employee",
    "list_employment_patterns",
    "get_employment_pattern",
    "list_time_slots",
    "get_time_slot",
    "list_absences_for_employee",
    "get_absence",
    "record_absence",
    "remove_absence",
    "list_shifts",
    "create_shift",
    "delete_shift",
    "delete_shifts_by_date_range",
    "list_break_schedules_by_date",
    "create_break_schedule",
    "delete_break_schedules_by_date_range",
    "reset_employment_patterns",
    "reset_time_slots",
    "get_setting",
    "set_setting",
]

_TIME_SLOT_DEFINITIONS = [
    # Monday
    ("mon_reha_am", 0, "morning", "08:30", "13:00", 1, 2, "リハ室", "リハ室（月曜午前）", 1.0, None),
    ("mon_reha_pm", 0, "afternoon", "13:00", "19:00", 1, 2, "リハ室", "リハ室（月曜午後）", 1.0, None),
    ("mon_recep_am", 0, "morning", "08:30", "13:00", 1, 2, "受付", "受付（月曜午前）", 1.0, None),
    ("mon_recep_pm", 0, "afternoon", "13:00", "19:00", 1, 1, "受付", "受付（月曜午後）", 1.0, None),
    # Tuesday
    ("tue_reha_am", 1, "morning", "08:30", "13:00", 1, 2, "リハ室", "リハ室（火曜午前）", 1.0, None),
    ("tue_reha_pm", 1, "afternoon", "13:00", "19:00", 1, 2, "リハ室", "リハ室（火曜午後）", 1.0, None),
    ("tue_recep_am", 1, "morning", "08:30", "13:00", 1, 2, "受付", "受付（火曜午前）", 1.0, None),
    ("tue_recep_pm", 1, "afternoon", "13:00", "19:00", 1, 1, "受付", "受付（火曜午後）", 1.0, None),
    # Wednesday
    ("wed_reha_am", 2, "morning", "08:30", "13:00", 1, 2, "リハ室", "リハ室（水曜午前）", 1.0, None),
    ("wed_reha_pm", 2, "afternoon", "13:00", "18:00", 1, 2, "リハ室", "リハ室（水曜午後）", 1.0, None),
    ("wed_recep_am", 2, "morning", "08:30", "13:00", 1, 2, "受付", "受付（水曜午前）", 1.0, None),
    ("wed_recep_pm", 2, "afternoon", "13:00", "18:00", 1, 1, "受付", "受付（水曜午後）", 1.0, None),
    # Thursday (morning only)
    ("thu_reha_am", 3, "morning", "08:30", "13:00", 1, 2, "リハ室", "リハ室（木曜午前）", 1.0, None),
    ("thu_recep_am", 3, "morning", "08:30", "13:00", 1, 2, "受付", "受付（木曜午前）", 1.0, None),
    # Friday
    ("fri_reha_am", 4, "morning", "08:30", "13:00", 1, 2, "リハ室", "リハ室（金曜午前）", 1.0, None),
    ("fri_reha_pm", 4, "afternoon", "13:00", "19:00", 1, 2, "リハ室", "リハ室（金曜午後）", 1.0, None),
    ("fri_recep_am", 4, "morning", "08:30", "13:00", 1, 2, "受付", "受付（金曜午前）", 1.0, None),
    ("fri_recep_pm", 4, "afternoon", "13:00", "19:00", 1, 1, "受付", "受付（金曜午後）", 1.0, None),
    # Saturday (morning only)
    ("sat_reha_am", 5, "morning", "08:30", "13:30", 1, 2, "リハ室", "リハ室（土曜午前）", 1.0, None),
    ("sat_recep_am", 5, "morning", "08:30", "13:30", 1, 2, "受付", "受付（土曜午前）", 1.0, None),
]

def _read_template_version(db_path: Path) -> Optional[str]:
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key='template_version'")
        row = cur.fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _should_replace_user_db(db_path: Path, template_version: Optional[str]) -> bool:
    if not db_path.exists():
        return True

    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
        if not cur.fetchone():
            return True

        cur.execute("SELECT value FROM settings WHERE key='template_version'")
        row = cur.fetchone()
        if row is None and template_version:
            cur.execute("SELECT COUNT(*) FROM employees")
            count = cur.fetchone()[0]
            return count == 0

        return False
    except sqlite3.Error:
        return True
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Database location and connection helpers
# ---------------------------------------------------------------------------

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _bundle_data = Path(sys._MEIPASS) / "data"
    _user_data_dir = Path.home() / ".shift_scheduler"
    _user_data_dir.mkdir(exist_ok=True)
    DB_PATH = _user_data_dir / "shift.db"
    template_db = _bundle_data / "shift.db"
    template_version = _read_template_version(template_db) if template_db.exists() else None
    if template_db.exists() and _should_replace_user_db(DB_PATH, template_version):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template_db, DB_PATH)
else:
    DB_PATH = Path(__file__).resolve().parents[1] / "data" / "shift.db"


def _ensure_parent_exists() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Provide a SQLite connection with an automatic row factory."""

    _ensure_parent_exists()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _execute(
    sql: str,
    params: Sequence[object] | None = None,
    *,
    many: bool = False,
) -> None:
    params = params or []
    with get_connection() as conn:
        cur = conn.cursor()
        if many and isinstance(params, Iterable):
            cur.executemany(sql, params)  # type: ignore[arg-type]
        else:
            cur.execute(sql, params)
        conn.commit()


def _fetchall(sql: str, params: Sequence[object] | None = None) -> List[sqlite3.Row]:
    params = params or []
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()


def _fetchone(sql: str, params: Sequence[object] | None = None) -> Optional[sqlite3.Row]:
    params = params or []
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone()


# ---------------------------------------------------------------------------
# Schema management
# ---------------------------------------------------------------------------

_EMPLOYEE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    employee_type TEXT NOT NULL CHECK(employee_type IN ('TYPE_A', 'TYPE_B', 'TYPE_C', 'TYPE_D')),
    employment_type TEXT NOT NULL CHECK(employment_type IN ('正職員', 'パート')),
    employment_pattern_id TEXT REFERENCES employment_patterns(id),
    skill_reha INTEGER DEFAULT 50 CHECK(skill_reha BETWEEN 0 AND 100),
    skill_reception_am INTEGER DEFAULT 50 CHECK(skill_reception_am BETWEEN 0 AND 100),
    skill_reception_pm INTEGER DEFAULT 50 CHECK(skill_reception_pm BETWEEN 0 AND 100),
    skill_general INTEGER DEFAULT 50 CHECK(skill_general BETWEEN 0 AND 100),
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_EMPLOYMENT_PATTERN_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS employment_patterns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('full_time', 'short_time', 'part_time')),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    break_hours REAL NOT NULL,
    work_hours REAL NOT NULL,
    can_work_afternoon BOOLEAN DEFAULT 1,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_EMPLOYEE_ABSENCE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS employee_absences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    absence_date DATE NOT NULL,
    absence_type TEXT NOT NULL CHECK(absence_type IN ('full_day', 'morning', 'afternoon')),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(employee_id, absence_date, absence_type)
);
"""

_TIME_SLOT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS time_slots (
    id TEXT PRIMARY KEY,
    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
    period TEXT NOT NULL CHECK(period IN ('morning', 'afternoon')),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    required_staff INTEGER DEFAULT 2,
    area TEXT NOT NULL,
    display_name TEXT NOT NULL,
    skill_weight REAL DEFAULT 1.0,
    target_skill_score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_SHIFT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    time_slot_id TEXT NOT NULL REFERENCES time_slots(id),
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, time_slot_id, employee_id)
);
"""

_BREAK_SCHEDULE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS break_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    break_number INTEGER NOT NULL,
    break_start_time TEXT NOT NULL,
    break_end_time TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def init_database() -> None:
    """Create tables and seed static data if required."""

    with get_connection() as conn:
        cur = conn.cursor()
        cur.executescript(
            "\n".join(
                [
                    _EMPLOYEE_TABLE_SQL,
                    _EMPLOYMENT_PATTERN_TABLE_SQL,
                    _EMPLOYEE_ABSENCE_TABLE_SQL,
                    _TIME_SLOT_TABLE_SQL,
                    _SHIFT_TABLE_SQL,
                    _BREAK_SCHEDULE_TABLE_SQL,
                    _SETTINGS_TABLE_SQL,
                ]
            )
        )
        conn.commit()

    _seed_employment_patterns()
    _seed_time_slots()


def _seed_employment_patterns() -> None:
    """Insert the default employment patterns if none exist."""

    existing = _fetchone("SELECT COUNT(*) AS cnt FROM employment_patterns")
    if existing and existing["cnt"]:
        return

    patterns: List[Tuple] = [
        ("full_early", "フルタイム（早番）", "full_time", "08:30", "18:30", 2.0, 8.0, 1, "正職員・早番"),
        ("full_mid", "フルタイム（中番）", "full_time", "08:45", "18:45", 2.0, 8.0, 1, "正職員・中番"),
        ("full_late", "フルタイム（遅番）", "full_time", "09:00", "19:00", 2.0, 8.0, 1, "正職員・遅番"),
        ("short_time", "時短勤務", "short_time", "08:45", "16:45", 1.0, 7.0, 0, "正職員・時短"),
        ("part_morning_early", "パート午前（早番）", "part_time", "08:30", "12:30", 0.0, 4.0, 0, "パート・午前4時間（早番）"),
        ("part_morning", "パート午前", "part_time", "08:45", "12:45", 0.0, 4.0, 0, "パート・午前4時間"),
        ("part_morning_ext", "パート午前延長", "part_time", "08:45", "13:45", 0.0, 5.0, 0, "パート・午前5時間"),
    ]
    _execute(
        """
        INSERT INTO employment_patterns (
            id, name, category, start_time, end_time, break_hours, work_hours, can_work_afternoon, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        patterns,
        many=True,
    )


def _seed_time_slots() -> None:
    """Ensure time slot master data matches the clinic operating hours."""

    desired_ids = {record[0] for record in _TIME_SLOT_DEFINITIONS}
    existing_rows = _fetchall("SELECT id FROM time_slots")

    with get_connection() as conn:
        cur = conn.cursor()
        upsert_sql = (
            """
            INSERT INTO time_slots (
                id, day_of_week, period, start_time, end_time, is_active,
                required_staff, area, display_name, skill_weight, target_skill_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                day_of_week = excluded.day_of_week,
                period = excluded.period,
                start_time = excluded.start_time,
                end_time = excluded.end_time,
                is_active = excluded.is_active,
                required_staff = excluded.required_staff,
                area = excluded.area,
                display_name = excluded.display_name,
                skill_weight = excluded.skill_weight,
                target_skill_score = excluded.target_skill_score
            """
        )

        for record in _TIME_SLOT_DEFINITIONS:
            cur.execute(upsert_sql, record)

        existing_ids = {row["id"] for row in existing_rows}
        builtin_prefixes = ("mon_", "tue_", "wed_", "thu_", "fri_", "sat_", "sun_")
        obsolete = [slot_id for slot_id in existing_ids if slot_id.startswith(builtin_prefixes) and slot_id not in desired_ids]
        if obsolete:
            cur.executemany("DELETE FROM time_slots WHERE id = ?", [(slot_id,) for slot_id in obsolete])

        conn.commit()


def reset_employment_patterns() -> None:
    """Remove and reseed all employment patterns."""

    _execute("DELETE FROM employment_patterns")
    _seed_employment_patterns()


def reset_time_slots() -> None:
    """Remove and reseed all time slots."""

    _execute("DELETE FROM time_slots")
    _seed_time_slots()


def get_setting(key: str) -> Optional[str]:
    """Retrieve a setting value from the settings table."""

    row = _fetchone("SELECT value FROM settings WHERE key = ?", [key])
    return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    """Insert or update a setting value."""

    _execute(
        """
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        [key, value],
    )


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def _row_to_employee(row: sqlite3.Row) -> Employee:
    return Employee(
        id=row["id"],
        name=row["name"],
        employee_type=row["employee_type"],
        employment_type=row["employment_type"],
        employment_pattern_id=row["employment_pattern_id"],
        skill_reha=row["skill_reha"],
        skill_reception_am=row["skill_reception_am"],
        skill_reception_pm=row["skill_reception_pm"],
        skill_general=row["skill_general"],
        is_active=bool(row["is_active"]),
    )


def _row_to_pattern(row: sqlite3.Row) -> EmploymentPattern:
    return EmploymentPattern(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        break_hours=row["break_hours"],
        work_hours=row["work_hours"],
        can_work_afternoon=bool(row["can_work_afternoon"]),
        description=row["description"],
    )


def _row_to_absence(row: sqlite3.Row) -> Absence:
    return Absence(
        id=row["id"],
        employee_id=row["employee_id"],
        absence_date=row["absence_date"],
        absence_type=row["absence_type"],
        reason=row["reason"],
    )


def _row_to_time_slot(row: sqlite3.Row) -> TimeSlot:
    return TimeSlot(
        id=row["id"],
        day_of_week=row["day_of_week"],
        period=row["period"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        is_active=bool(row["is_active"]),
        required_staff=row["required_staff"],
        area=row["area"],
        display_name=row["display_name"],
        skill_weight=row["skill_weight"],
        target_skill_score=row["target_skill_score"],
    )


def _row_to_break_schedule(row: sqlite3.Row) -> BreakSchedule:
    return BreakSchedule(
        id=row["id"],
        shift_id=row["shift_id"],
        employee_id=row["employee_id"],
        date=row["date"],
        break_number=row["break_number"],
        break_start_time=row["break_start_time"],
        break_end_time=row["break_end_time"],
    )


# ---------------------------------------------------------------------------
# Employee operations
# ---------------------------------------------------------------------------

def list_employees(*, active_only: bool = True) -> List[Employee]:
    sql = "SELECT * FROM employees"
    params: Sequence[object] = []
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY id"
    return [_row_to_employee(row) for row in _fetchall(sql, params)]


def get_employee(employee_id: int) -> Optional[Employee]:
    row = _fetchone("SELECT * FROM employees WHERE id = ?", [employee_id])
    return _row_to_employee(row) if row else None


def create_employee(
    *,
    name: str,
    employee_type: str,
    employment_type: str,
    employment_pattern_id: Optional[str],
    skill_reha: int,
    skill_reception_am: int,
    skill_reception_pm: int,
    skill_general: int,
) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO employees (
                name, employee_type, employment_type, employment_pattern_id,
                skill_reha, skill_reception_am, skill_reception_pm, skill_general
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                employee_type,
                employment_type,
                employment_pattern_id,
                skill_reha,
                skill_reception_am,
                skill_reception_pm,
                skill_general,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def update_employee(employee_id: int, **fields: object) -> bool:
    if not fields:
        return False
    columns = [f"{key} = ?" for key in fields]
    params = list(fields.values()) + [employee_id]
    sql = f"UPDATE employees SET {', '.join(columns)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount > 0


def delete_employee(employee_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM employees WHERE id = ?", [employee_id])
        conn.commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Employment pattern operations
# ---------------------------------------------------------------------------

def list_employment_patterns(*, category: Optional[str] = None) -> List[EmploymentPattern]:
    sql = "SELECT * FROM employment_patterns"
    params: List[object] = []
    if category:
        sql += " WHERE category = ?"
        params.append(category)
    sql += " ORDER BY name"
    return [_row_to_pattern(row) for row in _fetchall(sql, params)]


def get_employment_pattern(pattern_id: str) -> Optional[EmploymentPattern]:
    row = _fetchone("SELECT * FROM employment_patterns WHERE id = ?", [pattern_id])
    return _row_to_pattern(row) if row else None


# ---------------------------------------------------------------------------
# Time slot operations
# ---------------------------------------------------------------------------

def list_time_slots(*, active_only: bool = True) -> List[TimeSlot]:
    sql = "SELECT * FROM time_slots"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY day_of_week, period, start_time"
    return [_row_to_time_slot(row) for row in _fetchall(sql)]


def get_time_slot(time_slot_id: str) -> Optional[TimeSlot]:
    row = _fetchone("SELECT * FROM time_slots WHERE id = ?", [time_slot_id])
    return _row_to_time_slot(row) if row else None


# ---------------------------------------------------------------------------
# Absence management
# ---------------------------------------------------------------------------

def list_absences_for_employee(
    employee_id: int,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Absence]:
    sql = "SELECT * FROM employee_absences WHERE employee_id = ?"
    params: List[object] = [employee_id]
    if start_date:
        sql += " AND absence_date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND absence_date <= ?"
        params.append(end_date)
    sql += " ORDER BY absence_date"
    return [_row_to_absence(row) for row in _fetchall(sql, params)]


def get_absence(employee_id: int, date: str) -> Optional[Absence]:
    row = _fetchone(
        "SELECT * FROM employee_absences WHERE employee_id = ? AND absence_date = ?",
        [employee_id, date],
    )
    return _row_to_absence(row) if row else None


def record_absence(
    employee_id: int,
    date: str,
    absence_type: str,
    reason: Optional[str] = None,
) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO employee_absences (employee_id, absence_date, absence_type, reason)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(employee_id, absence_date, absence_type)
            DO UPDATE SET reason = excluded.reason, updated_at = CURRENT_TIMESTAMP
            """,
            (employee_id, date, absence_type, reason),
        )
        conn.commit()


def remove_absence(employee_id: int, date: str, absence_type: Optional[str] = None) -> None:
    sql = "DELETE FROM employee_absences WHERE employee_id = ? AND absence_date = ?"
    params: List[object] = [employee_id, date]
    if absence_type:
        sql += " AND absence_type = ?"
        params.append(absence_type)
    _execute(sql, params)


# ---------------------------------------------------------------------------
# Shift operations
# ---------------------------------------------------------------------------

def list_shifts(start_date: str, end_date: str) -> List[dict]:
    rows = _fetchall(
        """
        SELECT
            s.id,
            s.date,
            s.time_slot_id,
            s.employee_id,
            e.name AS employee_name,
            e.employee_type,
            e.employment_pattern_id,
            e.skill_reha,
            e.skill_reception_am,
            e.skill_reception_pm,
            e.skill_general,
            ts.display_name AS time_slot_name,
            ts.start_time,
            ts.end_time,
            ts.area,
            ts.period,
            ts.required_staff,
            ts.skill_weight,
            ts.target_skill_score,
            ts.day_of_week,
            (e.skill_general +
             CASE ts.area
                 WHEN 'リハ室' THEN e.skill_reha
                 WHEN '受付' AND ts.period = 'morning' THEN e.skill_reception_am
                 WHEN '受付' AND ts.period = 'afternoon' THEN e.skill_reception_pm
                 ELSE e.skill_general
             END) AS skill_score
        FROM shifts AS s
        JOIN employees AS e ON e.id = s.employee_id
        JOIN time_slots AS ts ON ts.id = s.time_slot_id
        WHERE s.date BETWEEN ? AND ?
        ORDER BY s.date, ts.day_of_week, ts.period, ts.start_time
        """,
        [start_date, end_date],
    )

    result = []
    for row in rows:
        employee_payload = {
            "id": row["employee_id"],
            "name": row["employee_name"],
            "employee_type": row["employee_type"],
            "employment_pattern_id": row["employment_pattern_id"],
            "skill_reha": row["skill_reha"],
            "skill_reception_am": row["skill_reception_am"],
            "skill_reception_pm": row["skill_reception_pm"],
            "skill_general": row["skill_general"],
        }
        slot_payload = {
            "id": row["time_slot_id"],
            "display_name": row["time_slot_name"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "area": row["area"],
            "area_type": row["area"],
            "period": row["period"],
            "time_period": "午前" if row["period"] == "morning" else "午後",
            "required_staff": row["required_staff"],
            "skill_weight": row["skill_weight"],
            "target_skill_score": row["target_skill_score"] or row["required_staff"] * 150,
            "day_of_week": row["day_of_week"],
        }
        result.append(
            {
                "id": row["id"],
                "date": row["date"],
                "time_slot_id": row["time_slot_id"],
                "employee_id": row["employee_id"],
                "employee_name": row["employee_name"],
                "time_slot_name": row["time_slot_name"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "skill_score": row["skill_score"],
                "employee": employee_payload,
                "time_slot": slot_payload,
            }
        )
    return result


def create_shift(date: str, time_slot_id: str, employee_id: int) -> Optional[int]:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO shifts (date, time_slot_id, employee_id) VALUES (?, ?, ?)",
                (date, time_slot_id, employee_id),
            )
            conn.commit()
            return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return None


def delete_shift(shift_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM shifts WHERE id = ?", [shift_id])
        conn.commit()
        return cur.rowcount > 0


def delete_shifts_by_date_range(start_date: str, end_date: str) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM shifts WHERE date BETWEEN ? AND ?", [start_date, end_date])
        conn.commit()
        return cur.rowcount


# ---------------------------------------------------------------------------
# Break schedules
# ---------------------------------------------------------------------------

def list_break_schedules_by_date(date: str) -> List[BreakSchedule]:
    rows = _fetchall(
        "SELECT * FROM break_schedules WHERE date = ? ORDER BY break_start_time",
        [date],
    )
    return [_row_to_break_schedule(row) for row in rows]


def create_break_schedule(
    *,
    shift_id: int,
    employee_id: int,
    date: str,
    break_number: int,
    break_start_time: str,
    break_end_time: str,
) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO break_schedules (
                shift_id, employee_id, date, break_number, break_start_time, break_end_time
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (shift_id, employee_id, date, break_number, break_start_time, break_end_time),
        )
        conn.commit()
        return int(cur.lastrowid)


def delete_break_schedules_by_date_range(start_date: str, end_date: str) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM break_schedules WHERE date BETWEEN ? AND ?",
            [start_date, end_date],
        )
        conn.commit()
        return cur.rowcount
