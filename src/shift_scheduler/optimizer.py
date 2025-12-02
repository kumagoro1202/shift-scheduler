"""Heuristic shift optimisation aligned with the V3.0 specification."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

from .availability import describe_unavailability, is_employee_available
from .models import Employee, GeneratedShift, TimeSlot


@dataclass
class RejectionSummary:
    """Aggregate information about why employees were excluded from a slot."""

    reason: str
    count: int
    examples: List[str] = field(default_factory=list)


@dataclass
class ShiftGenerationIssue:
    """Structured detail describing why shift generation failed."""

    code: str
    message: str
    date: Optional[str] = None
    time_slot_id: Optional[str] = None
    time_slot_name: Optional[str] = None
    required: Optional[int] = None
    available: Optional[int] = None
    shortage: Optional[int] = None
    available_employees: List[str] = field(default_factory=list)
    rejections: List[RejectionSummary] = field(default_factory=list)


class ShiftGenerationError(Exception):
    """Exception raised when shift generation cannot produce a valid roster."""

    def __init__(self, issue: ShiftGenerationIssue):
        super().__init__(issue.message)
        self.issue = issue


def _time_to_minutes(value: str) -> int:
    hours, minutes = map(int, value.split(":"))
    return hours * 60 + minutes


def check_time_overlap(slot_a: TimeSlot, slot_b: TimeSlot) -> bool:
    """Return ``True`` if the supplied time slots overlap."""

    start_a = _time_to_minutes(slot_a.start_time)
    end_a = _time_to_minutes(slot_a.end_time)
    start_b = _time_to_minutes(slot_b.start_time)
    end_b = _time_to_minutes(slot_b.end_time)

    if end_a < start_a:
        end_a += 24 * 60
    if end_b < start_b:
        end_b += 24 * 60

    return not (end_a <= start_b or end_b <= start_a)


def calculate_skill_score(employee: Employee, time_slot: TimeSlot) -> int:
    """Compute the score contribution for an employee in a slot."""

    general = employee.skill_general
    if time_slot.area == "リハ室":
        return employee.skill_reha + general
    if time_slot.area == "受付":
        if time_slot.period == "morning":
            return employee.skill_reception_am + general
        if time_slot.period == "afternoon":
            return employee.skill_reception_pm + general
        return ((employee.skill_reception_am + employee.skill_reception_pm) // 2) + general
    return general


def _can_assign_to_area(employee: Employee, time_slot: TimeSlot) -> bool:
    if time_slot.area == "リハ室":
        if employee.employee_type not in {"TYPE_A", "TYPE_C", "TYPE_D"}:
            return False
        return employee.skill_reha > 0

    if time_slot.area == "受付":
        if employee.employee_type not in {"TYPE_A", "TYPE_B"}:
            return False
        return employee.skill_reception_am > 0 or employee.skill_reception_pm > 0

    return True


def _select_employees_for_slot(
    candidates: Sequence[Employee],
    time_slot: TimeSlot,
    count: int,
    work_count: Dict[int, int],
    mode: str,
) -> List[Employee]:
    if len(candidates) < count:
        return []

    selected: List[Employee] = []
    remaining = list(candidates)

    for _ in range(count):
        if not remaining:
            break

        if mode == "days":
            min_work = min(work_count[e.id] for e in remaining)
            pool = [e for e in remaining if work_count[e.id] == min_work]
            chosen = pool[0]
        elif mode == "skill":
            target = time_slot.target_skill_score or (time_slot.required_staff * 150)
            current = sum(calculate_skill_score(e, time_slot) for e in selected)
            remaining_slots = max(1, count - len(selected))
            per_person_target = target - current
            per_person_target /= remaining_slots
            chosen = min(
                remaining,
                key=lambda e: abs(calculate_skill_score(e, time_slot) - per_person_target),
            )
        else:  # balance
            min_work = min(work_count[e.id] for e in remaining)
            pool = [e for e in remaining if work_count[e.id] == min_work]
            target = time_slot.target_skill_score or (time_slot.required_staff * 150)
            current = sum(calculate_skill_score(e, time_slot) for e in selected)
            remaining_slots = max(1, count - len(selected))
            per_person_target = target - current
            per_person_target /= remaining_slots
            chosen = min(
                pool,
                key=lambda e: abs(calculate_skill_score(e, time_slot) - per_person_target),
            )

        selected.append(chosen)
        remaining.remove(chosen)

    return selected


def _evaluate_part_time_rule(
    shifts: Sequence[GeneratedShift],
    time_slots: Sequence[TimeSlot],
) -> Optional[ShiftGenerationIssue]:
    """Ensure TYPE_D staff in rehab slots are paired with TYPE_A/C colleagues."""

    if not shifts:
        return None

    shift_lookup: Dict[str, TimeSlot] = {slot.id: slot for slot in time_slots}

    grouped: Dict[str, List[GeneratedShift]] = {}
    for shift in shifts:
        grouped.setdefault(shift.time_slot_id, []).append(shift)

    for slot_id, slot_shifts in grouped.items():
        slot = shift_lookup.get(slot_id, slot_shifts[0].time_slot)
        if slot.area != "リハ室":
            continue

        types = {s.employee.employee_type for s in slot_shifts}
        if "TYPE_D" in types and not ({"TYPE_A", "TYPE_C"} & types):
            employees = [s.employee_name for s in slot_shifts]
            issue = ShiftGenerationIssue(
                code="part_time_rule",
                message=(
                    "リハ室の時間帯でTYPE_D職員のみが割り当てられています。"
                    "TYPE_AまたはTYPE_Cを同じ時間帯に配置してください。"
                ),
                date=slot_shifts[0].date,
                time_slot_id=slot_id,
                time_slot_name=slot.display_name,
                required=slot.required_staff,
                available=len(slot_shifts),
                available_employees=employees,
            )
            return issue

    return None


def generate_shifts(
    employees: Sequence[Employee],
    time_slots: Sequence[TimeSlot],
    start_date: str,
    end_date: str,
    *,
    optimisation_mode: str = "balance",
) -> List[GeneratedShift]:
    if not employees:
        raise ShiftGenerationError(
            ShiftGenerationIssue(code="no_employees", message="職員が登録されていません。")
        )
    if not time_slots:
        raise ShiftGenerationError(
            ShiftGenerationIssue(code="no_time_slots", message="時間帯が登録されていません。")
        )

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    if end < start:
        raise ShiftGenerationError(
            ShiftGenerationIssue(
                code="invalid_range",
                message="終了日は開始日以降の日付を指定してください。",
            )
        )

    schedule: List[GeneratedShift] = []
    work_count: Dict[int, int] = {emp.id: 0 for emp in employees}

    all_slots_by_day: Dict[int, List[TimeSlot]] = {}
    for slot in time_slots:
        all_slots_by_day.setdefault(slot.day_of_week, []).append(slot)

    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        weekday = current.weekday()
        daily_slots = all_slots_by_day.get(weekday, [])
        daily_assignments: List[GeneratedShift] = []

        # Sort slots to process morning before afternoon for full-day work preference
        morning_slots = [s for s in daily_slots if s.period == "morning"]
        afternoon_slots = [s for s in daily_slots if s.period == "afternoon"]
        
        # Track which employees worked in the morning (by area) for full-day preference
        morning_workers_by_area: Dict[str, List[int]] = {}

        # Process morning slots first
        for slot in morning_slots:
            required = slot.required_staff
            available: List[Employee] = []
            rejection_log: Dict[str, List[str]] = {}

            for employee in employees:
                if not _can_assign_to_area(employee, slot):
                    rejection_log.setdefault("担当エリアの要件を満たしていません", []).append(employee.name)
                    continue
                # avoid double booking on the same day
                conflict = any(
                    s.employee_id == employee.id and s.date == date_str and check_time_overlap(slot, s.time_slot)
                    for s in schedule
                )
                if conflict:
                    rejection_log.setdefault("同日の別時間帯と重複しています", []).append(employee.name)
                    continue
                if not is_employee_available(employee, date_str, slot):
                    reason = describe_unavailability(employee, date_str, slot) or "勤務不可の設定があります"
                    rejection_log.setdefault(reason, []).append(employee.name)
                    continue
                available.append(employee)

            if len(available) < required:
                rejections = [
                    RejectionSummary(
                        reason=reason,
                        count=len(names),
                        examples=sorted(names)[:5],
                    )
                    for reason, names in sorted(
                        rejection_log.items(), key=lambda item: len(item[1]), reverse=True
                    )
                ]

                issue = ShiftGenerationIssue(
                    code="insufficient_staff",
                    message=(
                        f"{date_str} {slot.display_name}で必要人数{required}名を確保できませんでした。"
                    ),
                    date=date_str,
                    time_slot_id=slot.id,
                    time_slot_name=slot.display_name,
                    required=required,
                    available=len(available),
                    shortage=required - len(available),
                    available_employees=[emp.name for emp in available],
                    rejections=rejections,
                )
                raise ShiftGenerationError(issue)

            selected = _select_employees_for_slot(available, slot, required, work_count, optimisation_mode)
            if len(selected) < required:
                issue = ShiftGenerationIssue(
                    code="selection_failed",
                    message=(
                        f"{date_str} {slot.display_name}の割り当てに失敗しました。"
                        "最適化パラメータを見直してください。"
                    ),
                    date=date_str,
                    time_slot_id=slot.id,
                    time_slot_name=slot.display_name,
                    required=required,
                    available=len(available),
                    shortage=required - len(selected),
                    available_employees=[emp.name for emp in available],
                )
                raise ShiftGenerationError(issue)

            for employee in selected:
                shift = GeneratedShift(
                    date=date_str,
                    time_slot_id=slot.id,
                    employee_id=employee.id,
                    employee_name=employee.name,
                    time_slot_name=slot.display_name,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    skill_score=calculate_skill_score(employee, slot),
                    employee=employee,
                    time_slot=slot,
                )
                schedule.append(shift)
                daily_assignments.append(shift)
                work_count[employee.id] += 1
                
                # Track morning workers by area for full-day preference
                morning_workers_by_area.setdefault(slot.area, []).append(employee.id)

        # Process afternoon slots with full-day work preference
        for slot in afternoon_slots:
            required = slot.required_staff
            available: List[Employee] = []
            rejection_log: Dict[str, List[str]] = {}

            # Check if there are morning workers in the same area who can work afternoon
            morning_workers = morning_workers_by_area.get(slot.area, [])
            afternoon_capable_morning_workers: List[Employee] = []

            for employee in employees:
                if not _can_assign_to_area(employee, slot):
                    rejection_log.setdefault("担当エリアの要件を満たしていません", []).append(employee.name)
                    continue
                # avoid double booking on the same day
                conflict = any(
                    s.employee_id == employee.id and s.date == date_str and check_time_overlap(slot, s.time_slot)
                    for s in schedule
                )
                if conflict:
                    rejection_log.setdefault("同日の別時間帯と重複しています", []).append(employee.name)
                    continue
                if not is_employee_available(employee, date_str, slot):
                    reason = describe_unavailability(employee, date_str, slot) or "勤務不可の設定があります"
                    rejection_log.setdefault(reason, []).append(employee.name)
                    continue
                available.append(employee)
                
                # Prefer employees who worked the morning shift in the same area
                if employee.id in morning_workers:
                    afternoon_capable_morning_workers.append(employee)

            if len(available) < required:
                rejections = [
                    RejectionSummary(
                        reason=reason,
                        count=len(names),
                        examples=sorted(names)[:5],
                    )
                    for reason, names in sorted(
                        rejection_log.items(), key=lambda item: len(item[1]), reverse=True
                    )
                ]

                issue = ShiftGenerationIssue(
                    code="insufficient_staff",
                    message=(
                        f"{date_str} {slot.display_name}で必要人数{required}名を確保できませんでした。"
                    ),
                    date=date_str,
                    time_slot_id=slot.id,
                    time_slot_name=slot.display_name,
                    required=required,
                    available=len(available),
                    shortage=required - len(available),
                    available_employees=[emp.name for emp in available],
                    rejections=rejections,
                )
                raise ShiftGenerationError(issue)

            # Prioritize morning workers for full-day work, but still use selection logic
            # First try to fill with morning workers
            selected: List[Employee] = []
            if afternoon_capable_morning_workers:
                needed_from_morning = min(len(afternoon_capable_morning_workers), required)
                selected = _select_employees_for_slot(
                    afternoon_capable_morning_workers, slot, needed_from_morning, work_count, optimisation_mode
                )
            
            # Fill remaining slots with other available employees
            if len(selected) < required:
                remaining_available = [e for e in available if e not in selected]
                additional_needed = required - len(selected)
                additional = _select_employees_for_slot(
                    remaining_available, slot, additional_needed, work_count, optimisation_mode
                )
                selected.extend(additional)

            if len(selected) < required:
                issue = ShiftGenerationIssue(
                    code="selection_failed",
                    message=(
                        f"{date_str} {slot.display_name}の割り当てに失敗しました。"
                        "最適化パラメータを見直してください。"
                    ),
                    date=date_str,
                    time_slot_id=slot.id,
                    time_slot_name=slot.display_name,
                    required=required,
                    available=len(available),
                    shortage=required - len(selected),
                    available_employees=[emp.name for emp in available],
                )
                raise ShiftGenerationError(issue)

            for employee in selected:
                shift = GeneratedShift(
                    date=date_str,
                    time_slot_id=slot.id,
                    employee_id=employee.id,
                    employee_name=employee.name,
                    time_slot_name=slot.display_name,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    skill_score=calculate_skill_score(employee, slot),
                    employee=employee,
                    time_slot=slot,
                )
                schedule.append(shift)
                daily_assignments.append(shift)
                work_count[employee.id] += 1

        if daily_assignments:
            violation = _evaluate_part_time_rule(daily_assignments, time_slots)
            if violation:
                raise ShiftGenerationError(violation)

        current += timedelta(days=1)

    return schedule


def calculate_skill_balance(shifts: Sequence[GeneratedShift], time_slots: Sequence[TimeSlot]) -> Dict[str, float]:
    if not shifts:
        return {"avg_skill": 0.0, "std_skill": 0.0, "min_skill": 0.0, "max_skill": 0.0}

    slot_totals: Dict[str, int] = {}
    for shift in shifts:
        slot_totals.setdefault(shift.time_slot_id, 0)
        slot_totals[shift.time_slot_id] += shift.skill_score

    if not slot_totals:
        return {"avg_skill": 0.0, "std_skill": 0.0, "min_skill": 0.0, "max_skill": 0.0}

    scores = list(slot_totals.values())
    average = sum(scores) / len(scores)
    variance = sum((score - average) ** 2 for score in scores) / len(scores)
    std_dev = variance ** 0.5

    return {
        "avg_skill": average,
        "std_skill": std_dev,
        "min_skill": float(min(scores)),
        "max_skill": float(max(scores)),
        "balance_score": (std_dev / average) if average > 0 else 0.0,
    }
