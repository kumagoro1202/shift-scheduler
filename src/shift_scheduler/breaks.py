"""Break assignment helpers for reception coverage."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .database import (
    create_break_schedule,
    delete_break_schedules_by_date_range,
    get_employment_pattern,
    list_break_schedules_by_date,
)

TimeWindow = Tuple[str, str]

PREFERRED_WINDOWS: Sequence[TimeWindow] = (
    ("11:00", "12:00"),
    ("12:00", "13:00"),
    ("13:00", "14:00"),
)


def _parse_time(value: str) -> datetime:
    return datetime.strptime(value, "%H:%M")


def _window_overlaps(a: TimeWindow, b: TimeWindow) -> bool:
    start_a, end_a = map(_parse_time, a)
    start_b, end_b = map(_parse_time, b)
    return not (end_a <= start_b or end_b <= start_a)


def generate_time_intervals(start: str, end: str, interval_minutes: int = 15) -> List[TimeWindow]:
    start_dt = _parse_time(start)
    end_dt = _parse_time(end)
    result: List[TimeWindow] = []
    current = start_dt
    while current < end_dt:
        nxt = current + timedelta(minutes=interval_minutes)
        if nxt > end_dt:
            nxt = end_dt
        result.append((current.strftime("%H:%M"), nxt.strftime("%H:%M")))
        current = nxt
    return result


def _break_windows_for_pattern(pattern_break_hours: float) -> List[TimeWindow]:
    if pattern_break_hours >= 2:
        return [PREFERRED_WINDOWS[0], PREFERRED_WINDOWS[2]]
    if pattern_break_hours >= 1:
        return [PREFERRED_WINDOWS[1]]
    return []


def _find_covering_shift(shift_blocks: Sequence[dict], window: TimeWindow) -> Optional[dict]:
    start, end = map(_parse_time, window)
    for shift in shift_blocks:
        shift_start = _parse_time(shift["start_time"])
        shift_end = _parse_time(shift["end_time"])
        if shift_start <= start and shift_end >= end:
            return shift
    return shift_blocks[0] if shift_blocks else None


def _filter_reception_shifts(shifts: Sequence[dict]) -> List[dict]:
    """Filter shifts to get only reception area shifts."""
    return [s for s in shifts if s.get("time_slot", {}).get("area") == "受付"]


def _group_shifts_by_employee(shifts: Sequence[dict]) -> Dict[int, List[dict]]:
    """Group shifts by employee ID."""
    employee_blocks: Dict[int, List[dict]] = {}
    for shift in shifts:
        employee_blocks.setdefault(shift["employee_id"], []).append(shift)
    return employee_blocks


def _assign_break_for_employee(
    employee_id: int,
    blocks: List[dict],
    window_usage: Dict[TimeWindow, List[int]],
    coverage_limit: int,
) -> Optional[TimeWindow]:
    """Try to assign a break window for an employee.
    
    Returns assigned window if successful, None otherwise.
    """
    pattern_id = blocks[0]["employee"].get("employment_pattern_id") if blocks[0].get("employee") else None
    pattern = get_employment_pattern(pattern_id) if pattern_id else None
    break_windows = _break_windows_for_pattern(pattern.break_hours if pattern else 0.0)
    
    for window in break_windows:
        usable_windows = list(PREFERRED_WINDOWS)
        if window not in usable_windows:
            usable_windows.insert(0, window)
        
        for candidate in usable_windows:
            if candidate not in window_usage:
                window_usage[candidate] = []
            if len(window_usage[candidate]) >= coverage_limit:
                continue
            target_shift = _find_covering_shift(blocks, candidate)
            if not target_shift:
                continue
            window_usage[candidate].append(employee_id)
            return candidate
    
    return None


def _save_break_assignments(
    date: str,
    assignments: List[Tuple[int, TimeWindow]],
    employee_blocks: Dict[int, List[dict]],
) -> int:
    """Save break assignments to database.
    
    Returns number of breaks saved.
    """
    delete_break_schedules_by_date_range(date, date)
    
    saved = 0
    break_counts: Dict[int, int] = {}
    for employee_id, window in assignments:
        blocks = employee_blocks[employee_id]
        target_shift = _find_covering_shift(blocks, window) or blocks[0]
        break_counts[employee_id] = break_counts.get(employee_id, 0) + 1
        create_break_schedule(
            shift_id=target_shift["id"],
            employee_id=employee_id,
            date=date,
            break_number=break_counts[employee_id],
            break_start_time=window[0],
            break_end_time=window[1],
        )
        saved += 1
    
    return saved


def auto_assign_and_save_breaks(date: str, shifts: Sequence[dict]) -> Tuple[int, bool, List[str]]:
    reception_shifts = _filter_reception_shifts(shifts)
    if len(reception_shifts) < 3:
        return 0, True, ["受付職員が3名未満のため自動割り当てをスキップしました"]

    coverage_limit = len(reception_shifts) - 2
    window_usage: Dict[TimeWindow, List[int]] = {window: [] for window in PREFERRED_WINDOWS}
    employee_blocks = _group_shifts_by_employee(reception_shifts)

    assignments: List[Tuple[int, TimeWindow]] = []
    warnings: List[str] = []

    for employee_id, blocks in employee_blocks.items():
        assigned_window = _assign_break_for_employee(employee_id, blocks, window_usage, coverage_limit)
        if assigned_window:
            assignments.append((employee_id, assigned_window))
        else:
            warnings.append(f"{blocks[0]['employee_name']}の休憩時間を自動割り当てできませんでした")

    if not assignments:
        return 0, False, warnings or ["有効な休憩割り当てがありません"]

    saved = _save_break_assignments(date, assignments, employee_blocks)
    return saved, not warnings, warnings


def _is_employee_on_break(employee_id: int, window: TimeWindow, break_schedules: Sequence[dict]) -> bool:
    """Check if employee is on break during the given window."""
    breaks_for_employee = [b for b in break_schedules if b["employee_id"] == employee_id]
    return any(
        _window_overlaps(window, (b["break_start_time"], b["break_end_time"]))
        for b in breaks_for_employee
    )


def _count_working_staff(
    shifts: Sequence[dict],
    break_schedules: Sequence[dict],
    window: TimeWindow,
) -> int:
    """Count number of staff working (not on break) during a time window."""
    working = 0
    for shift in shifts:
        shift_window = (shift["start_time"], shift["end_time"])
        if not _window_overlaps(window, shift_window):
            continue
        if not _is_employee_on_break(shift["employee_id"], window, break_schedules):
            working += 1
    return working


def validate_reception_coverage(date: str, shifts: Sequence[dict], break_schedules: Sequence[dict]) -> Tuple[bool, List[str]]:
    reception_shifts = _filter_reception_shifts(shifts)
    if not reception_shifts:
        return True, []

    warnings: List[str] = []
    intervals = generate_time_intervals("08:30", "19:00", 15)
    
    for window in intervals:
        working = _count_working_staff(reception_shifts, break_schedules, window)
        if working < 2:
            warnings.append(f"{window[0]}-{window[1]}の受付常駐人数が不足しています ({working}名)")

    return (len(warnings) == 0), warnings


def get_break_schedules(date: str) -> List[dict]:
    return [schedule.to_dict() for schedule in list_break_schedules_by_date(date)]
