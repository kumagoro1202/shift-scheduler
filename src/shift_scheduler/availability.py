"""Availability evaluation utilities."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from .database import get_absence, get_employment_pattern
from .models import Employee, TimeSlot

WEEKDAY_NAMES = ["月", "火", "水", "木", "金", "土", "日"]


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def _check_basic_slot_availability(time_slot: TimeSlot, date_obj: datetime) -> Optional[str]:
    """Check basic slot availability (active status, weekday match, Sunday closure).
    
    Returns None if available, error message if unavailable.
    """
    if not time_slot.is_active:
        return "時間帯が休診です"
    
    if time_slot.day_of_week != date_obj.weekday():
        return None  # Not an error, just doesn't match
    
    if date_obj.weekday() == 6:
        return "日曜日は休診です"
    
    return None


def _check_absence(employee: Employee, date_str: str, time_slot: TimeSlot) -> Optional[str]:
    """Check if employee has absence that conflicts with time slot.
    
    Returns None if no conflict, absence description if conflict.
    """
    absence = get_absence(employee.id, date_str)
    if not absence:
        return None
    
    if absence.absence_type == "full_day":
        return "full_day"
    if absence.absence_type == "morning" and time_slot.period == "morning":
        return "morning"
    if absence.absence_type == "afternoon" and time_slot.period == "afternoon":
        return "afternoon"
    
    return None


def _check_employment_pattern(employee: Employee, time_slot: TimeSlot) -> Optional[str]:
    """Check if employment pattern allows working in this time slot.
    
    Returns None if allowed, error code if not allowed.
    """
    if not employee.employment_pattern_id:
        return None
    
    pattern = get_employment_pattern(employee.employment_pattern_id)
    if pattern is None:
        return "pattern_not_found"
    
    if time_slot.period == "afternoon" and not pattern.can_work_afternoon:
        return "no_afternoon"
    
    try:
        slot_start = datetime.strptime(time_slot.start_time, "%H:%M").time()
        slot_end = datetime.strptime(time_slot.end_time, "%H:%M").time()
        pattern_start = datetime.strptime(pattern.start_time, "%H:%M").time()
        pattern_end = datetime.strptime(pattern.end_time, "%H:%M").time()
    except ValueError:
        return "time_parse_error"
    
    if slot_start < pattern_start:
        return "before_start"
    if slot_end > pattern_end:
        return "after_end"
    
    return None


def is_employee_available(employee: Employee, date_str: str, time_slot: TimeSlot) -> bool:
    """Return ``True`` if the employee can work on the supplied date and slot."""
    date_obj = _parse_date(date_str)
    
    # Check basic slot availability
    basic_check = _check_basic_slot_availability(time_slot, date_obj)
    if basic_check == "日曜日は休診です":
        return False
    if not time_slot.is_active:
        return False
    
    # Day of week must match
    if time_slot.day_of_week != date_obj.weekday():
        return False
    
    # Check absence
    absence_check = _check_absence(employee, date_str, time_slot)
    if absence_check:
        return False
    
    # Check employment pattern
    pattern_check = _check_employment_pattern(employee, time_slot)
    if pattern_check:
        return False
    
    return True


def _format_absence_reason(absence) -> str:
    """Format absence information as a readable string."""
    labels = {
        "full_day": "終日休暇",
        "morning": "午前休",
        "afternoon": "午後休",
    }
    label = labels.get(absence.absence_type, absence.absence_type)
    note = f"（{absence.reason}）" if absence.reason else ""
    return f"{label}{note}"


def _format_pattern_error(pattern_check: str, pattern) -> str:
    """Format employment pattern error as a readable string."""
    if pattern_check == "pattern_not_found":
        return "勤務パターンが見つかりません"
    if pattern_check == "no_afternoon":
        return f"勤務パターン「{pattern.name}」は午後勤務不可です"
    if pattern_check == "time_parse_error":
        return "時刻データの解釈に失敗しました"
    if pattern_check == "before_start":
        return f"勤務開始前の時間帯です（開始 {pattern.start_time}）"
    if pattern_check == "after_end":
        return f"勤務終了後の時間帯です（終了 {pattern.end_time}）"
    return None


def describe_unavailability(employee: Employee, date_str: str, time_slot: TimeSlot) -> Optional[str]:
    """Return a human readable reason explaining why a slot is unavailable."""
    date_obj = _parse_date(date_str)
    
    # Check basic slot issues
    basic_check = _check_basic_slot_availability(time_slot, date_obj)
    if basic_check:
        return basic_check
    
    # Check weekday match
    if time_slot.day_of_week != date_obj.weekday():
        day_label = WEEKDAY_NAMES[time_slot.day_of_week]
        return f"{date_str}は{day_label}曜日の時間帯ではありません"
    
    # Check absence
    absence_check = _check_absence(employee, date_str, time_slot)
    if absence_check:
        absence = get_absence(employee.id, date_str)
        return _format_absence_reason(absence)
    
    # Check employment pattern
    pattern_check = _check_employment_pattern(employee, time_slot)
    if not pattern_check:
        return None
    
    pattern = get_employment_pattern(employee.employment_pattern_id) if employee.employment_pattern_id else None
    return _format_pattern_error(pattern_check, pattern)


def available_time_slots(
    employee: Employee,
    date_str: str,
    time_slots: Iterable[TimeSlot],
) -> List[TimeSlot]:
    """Return the subset of time slots an employee can work for a given date."""

    return [ts for ts in time_slots if is_employee_available(employee, date_str, ts)]
