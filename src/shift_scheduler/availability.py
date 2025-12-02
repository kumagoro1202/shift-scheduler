"""Availability evaluation utilities."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from .database import get_absence, get_employment_pattern
from .models import Employee, TimeSlot

WEEKDAY_NAMES = ["月", "火", "水", "木", "金", "土", "日"]


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def is_employee_available(employee: Employee, date_str: str, time_slot: TimeSlot) -> bool:
    """Return ``True`` if the employee can work on the supplied date and slot."""

    if not time_slot.is_active:
        return False

    date_obj = _parse_date(date_str)

    # Day of week must match fixed time slot configuration
    if time_slot.day_of_week != date_obj.weekday():
        return False

    # Clinic is closed on Sundays
    if date_obj.weekday() == 6:
        return False

    # Absence check
    absence = get_absence(employee.id, date_str)
    if absence:
        if absence.absence_type == "full_day":
            return False
        if absence.absence_type == "morning" and time_slot.period == "morning":
            return False
        if absence.absence_type == "afternoon" and time_slot.period == "afternoon":
            return False

    # Employment pattern check
    pattern = None
    if employee.employment_pattern_id:
        pattern = get_employment_pattern(employee.employment_pattern_id)
        if pattern is None:
            return False

    if pattern:
        if time_slot.period == "afternoon" and not pattern.can_work_afternoon:
            return False

        try:
            slot_start = datetime.strptime(time_slot.start_time, "%H:%M").time()
            slot_end = datetime.strptime(time_slot.end_time, "%H:%M").time()
            pattern_start = datetime.strptime(pattern.start_time, "%H:%M").time()
            pattern_end = datetime.strptime(pattern.end_time, "%H:%M").time()
        except ValueError:
            return False

        if slot_start < pattern_start or slot_end > pattern_end:
            return False

    return True


def describe_unavailability(employee: Employee, date_str: str, time_slot: TimeSlot) -> Optional[str]:
    """Return a human readable reason explaining why a slot is unavailable."""

    if not time_slot.is_active:
        return "時間帯が休診です"

    date_obj = _parse_date(date_str)

    if time_slot.day_of_week != date_obj.weekday():
        day_label = WEEKDAY_NAMES[time_slot.day_of_week]
        return f"{date_str}は{day_label}曜日の時間帯ではありません"

    if date_obj.weekday() == 6:
        return "日曜日は休診です"

    absence = get_absence(employee.id, date_str)
    if absence:
        labels = {
            "full_day": "終日休暇",
            "morning": "午前休",
            "afternoon": "午後休",
        }
        label = labels.get(absence.absence_type, absence.absence_type)
        note = f"（{absence.reason}）" if absence.reason else ""
        return f"{label}{note}"

    pattern = None
    if employee.employment_pattern_id:
        pattern = get_employment_pattern(employee.employment_pattern_id)
        if pattern is None:
            return "勤務パターンが見つかりません"

    if pattern:
        if time_slot.period == "afternoon" and not pattern.can_work_afternoon:
            return f"勤務パターン「{pattern.name}」は午後勤務不可です"

        try:
            slot_start = datetime.strptime(time_slot.start_time, "%H:%M").time()
            slot_end = datetime.strptime(time_slot.end_time, "%H:%M").time()
            pattern_start = datetime.strptime(pattern.start_time, "%H:%M").time()
            pattern_end = datetime.strptime(pattern.end_time, "%H:%M").time()
        except ValueError:
            return "時刻データの解釈に失敗しました"

        if slot_start < pattern_start:
            return f"勤務開始前の時間帯です（開始 {pattern.start_time}）"
        if slot_end > pattern_end:
            return f"勤務終了後の時間帯です（終了 {pattern.end_time}）"

    return None


def available_time_slots(
    employee: Employee,
    date_str: str,
    time_slots: Iterable[TimeSlot],
) -> List[TimeSlot]:
    """Return the subset of time slots an employee can work for a given date."""

    return [ts for ts in time_slots if is_employee_available(employee, date_str, ts)]
