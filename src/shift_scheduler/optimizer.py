"""Heuristic shift optimisation aligned with the V3.0 specification."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from .availability import describe_unavailability, is_employee_available
from .models import Employee, EmploymentPattern, GeneratedShift, TimeSlot


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


def _get_available_patterns_for_day(date: str, employee: Employee) -> List[str]:
    """指定日の曜日に応じて利用可能な勤務パターンIDのリストを返す
    
    Args:
        date: YYYY-MM-DD形式の日付文字列
        employee: 職員オブジェクト
    
    Returns:
        利用可能な勤務パターンIDのリスト
        
    Note:
        - 正職員でis_pattern_fixed=Falseの場合のみ複数パターンを返す
        - それ以外は登録済みのemployment_pattern_idを返す
    """
    # パターン固定の場合は登録済みパターンを返す
    if employee.is_pattern_fixed or not employee.employment_pattern_id:
        return [employee.employment_pattern_id] if employee.employment_pattern_id else []
    
    # 曜日判定
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    weekday = date_obj.weekday()  # 0=月, 1=火, 2=水, 3=木, 4=金, 5=土, 6=日
    
    # 曜日別にパターンを返す
    if weekday in [0, 1, 4]:  # 月火金
        return ["weekday_full_A", "weekday_full_B", "weekday_full_C"]
    elif weekday == 2:  # 水曜
        return ["wednesday_early", "wednesday_normal", "wednesday_late"]
    elif weekday in [3, 5]:  # 木土
        return ["thu_sat_1", "thu_sat_2", "thu_sat_3"]
    else:
        return []


def _select_best_pattern(
    employee: Employee,
    date: str,
    available_patterns: List[str],
    pattern_usage_count: Dict[Tuple[int, str], int],
) -> str:
    """勤務パターンの偏りを防止しつつ最適なパターンを選択
    
    Args:
        employee: 職員オブジェクト
        date: 日付文字列
        available_patterns: 利用可能なパターンIDリスト
        pattern_usage_count: (employee_id, pattern_id) -> 使用回数のマッピング
    
    Returns:
        選択された勤務パターンID
    """
    if not available_patterns:
        return None
    
    # 各パターンの使用回数を確認
    usage_counts = []
    for pattern_id in available_patterns:
        count = pattern_usage_count.get((employee.id, pattern_id), 0)
        usage_counts.append((pattern_id, count))
    
    # 最小使用回数のパターンから選択（偏り防止）
    min_count = min(count for _, count in usage_counts)
    least_used = [pid for pid, count in usage_counts if count == min_count]
    
    # 同率の場合は先頭を返す（シンプルな実装）
    return least_used[0]


def calculate_skill_score(employee: Employee, time_slot: TimeSlot) -> int:
    """職員のスキルスコアを計算する。
    
    受付業務では医事能力（保険登録、会計など）を優先的に評価する。
    各時間帯のスキルスコアを均等化することで、日によるサービス品質の
    偏りを防止する。
    """
    general = employee.skill_general
    if time_slot.area == "リハ室":
        return employee.skill_reha + general
    if time_slot.area == "受付":
        # 受付スキルには医事能力（保険登録、会計など）が含まれる
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


def _select_by_workday_count(candidates: Sequence[Employee], count: int, work_count: Dict[int, int]) -> List[Employee]:
    """Select employees with minimum work days."""
    selected: List[Employee] = []
    remaining = list(candidates)
    
    for _ in range(count):
        if not remaining:
            break
        min_work = min(work_count[e.id] for e in remaining)
        pool = [e for e in remaining if work_count[e.id] == min_work]
        chosen = pool[0]
        selected.append(chosen)
        remaining.remove(chosen)
    
    return selected


def _select_by_skill_score(
    candidates: Sequence[Employee],
    count: int,
    work_count: Dict[int, int],
    time_slot: TimeSlot,
    current_selected: List[Employee],
) -> List[Employee]:
    """スキル能力の平均化を優先する選択アルゴリズム。
    
    各時間帯において、配置される職員のスキル能力を均等化する。
    特に受付業務では医事能力（保険登録、会計など）を優先する。
    
    目標値に近いスキルスコアを持つ職員を選択することで、
    日によって能力が偏らないよう、各時間帯の職員スキルレベルを均一化する。
    """
    selected: List[Employee] = list(current_selected)
    remaining = list(candidates)
    
    for _ in range(count - len(selected)):
        if not remaining:
            break
        
        target = time_slot.target_skill_score or (time_slot.required_staff * 150)
        current_score = sum(calculate_skill_score(e, time_slot) for e in selected)
        remaining_slots = max(1, count - len(selected))
        per_person_target = (target - current_score) / remaining_slots
        
        # 目標スコアに最も近い職員を選択（医事能力を優先評価）
        chosen = min(
            remaining,
            key=lambda e: abs(calculate_skill_score(e, time_slot) - per_person_target),
        )
        selected.append(chosen)
        remaining.remove(chosen)
    
    return selected


def _select_by_balance(
    candidates: Sequence[Employee],
    count: int,
    work_count: Dict[int, int],
    time_slot: TimeSlot,
) -> List[Employee]:
    """勤務回数とスキル能力のバランスを考慮した選択アルゴリズム。
    
    最小勤務回数の職員の中から、スキル能力の平均化を考慮して選択する。
    特に受付業務では医事能力（保険登録、会計など）を優先評価する。
    """
    selected: List[Employee] = []
    remaining = list(candidates)
    
    for _ in range(count):
        if not remaining:
            break
        
        # 最小勤務回数の職員を抽出
        min_work = min(work_count[e.id] for e in remaining)
        pool = [e for e in remaining if work_count[e.id] == min_work]
        
        # その中からスキルバランスが良い職員を選択（能力の平均化）
        target = time_slot.target_skill_score or (time_slot.required_staff * 150)
        current_score = sum(calculate_skill_score(e, time_slot) for e in selected)
        remaining_slots = max(1, count - len(selected))
        per_person_target = (target - current_score) / remaining_slots
        
        chosen = min(
            pool,
            key=lambda e: abs(calculate_skill_score(e, time_slot) - per_person_target),
        )
        selected.append(chosen)
        remaining.remove(chosen)
    
    return selected


def _select_employees_for_slot(
    candidates: Sequence[Employee],
    time_slot: TimeSlot,
    count: int,
    work_count: Dict[int, int],
    mode: str,
) -> List[Employee]:
    if len(candidates) < count:
        return []

    if mode == "days":
        return _select_by_workday_count(candidates, count, work_count)
    elif mode == "skill":
        return _select_by_skill_score(candidates, count, work_count, time_slot, [])
    else:  # balance
        return _select_by_balance(candidates, count, work_count, time_slot)


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


def _validate_shift_inputs(employees: Sequence[Employee], time_slots: Sequence[TimeSlot], start_date: str, end_date: str) -> None:
    """Validate inputs for shift generation."""
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


def _filter_available_employees(
    employees: Sequence[Employee],
    date_str: str,
    slot: TimeSlot,
    schedule: List[GeneratedShift],
) -> tuple[List[Employee], Dict[str, List[str]]]:
    """Filter employees available for a specific slot.
    
    Returns tuple of (available employees, rejection log).
    """
    available: List[Employee] = []
    rejection_log: Dict[str, List[str]] = {}
    
    for employee in employees:
        if not _can_assign_to_area(employee, slot):
            rejection_log.setdefault("担当エリアの要件を満たしていません", []).append(employee.name)
            continue
        
        # Avoid double booking
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
    
    return available, rejection_log


def _create_insufficient_staff_error(
    date_str: str,
    slot: TimeSlot,
    available: List[Employee],
    rejection_log: Dict[str, List[str]],
) -> ShiftGenerationIssue:
    """Create error for insufficient staff situation."""
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
    
    return ShiftGenerationIssue(
        code="insufficient_staff",
        message=(
            f"{date_str} {slot.display_name}で必要人数{slot.required_staff}名を確保できませんでした。"
        ),
        date=date_str,
        time_slot_id=slot.id,
        time_slot_name=slot.display_name,
        required=slot.required_staff,
        available=len(available),
        shortage=slot.required_staff - len(available),
        available_employees=[emp.name for emp in available],
        rejections=rejections,
    )


def _assign_employees_to_slot(
    available: List[Employee],
    slot: TimeSlot,
    date_str: str,
    optimisation_mode: str,
    work_count: Dict[int, int],
    morning_workers: List[int],
    pattern_usage_count: Dict[Tuple[int, str], int],
) -> List[Tuple[Employee, str]]:
    """Assign employees to a time slot with employment patterns, preferring full-day workers for afternoon slots.
    
    Returns:
        List of (Employee, pattern_id) tuples
    """
    required = slot.required_staff
    selected_employees: List[Employee] = []
    
    # For afternoon slots, prefer employees who worked in the morning
    if slot.period == "afternoon" and morning_workers:
        afternoon_capable = [e for e in available if e.id in morning_workers]
        if afternoon_capable:
            needed = min(len(afternoon_capable), required)
            selected_employees = _select_employees_for_slot(afternoon_capable, slot, needed, work_count, optimisation_mode)
    
    # Fill remaining slots
    if len(selected_employees) < required:
        remaining_available = [e for e in available if e not in selected_employees]
        additional_needed = required - len(selected_employees)
        additional = _select_employees_for_slot(
            remaining_available, slot, additional_needed, work_count, optimisation_mode
        )
        selected_employees.extend(additional)
    
    # 各職員に勤務パターンを割り当て
    assignments: List[Tuple[Employee, str]] = []
    for employee in selected_employees:
        available_patterns = _get_available_patterns_for_day(date_str, employee)
        pattern_id = _select_best_pattern(
            employee, date_str, available_patterns, pattern_usage_count
        )
        assignments.append((employee, pattern_id))
        
        # パターン使用回数を更新
        if pattern_id:
            key = (employee.id, pattern_id)
            pattern_usage_count[key] = pattern_usage_count.get(key, 0) + 1
    
    return assignments


def _process_time_slot(
    slot: TimeSlot,
    date_str: str,
    employees: Sequence[Employee],
    schedule: List[GeneratedShift],
    work_count: Dict[int, int],
    optimisation_mode: str,
    morning_workers: List[int],
    pattern_usage_count: Dict[Tuple[int, str], int],
) -> List[GeneratedShift]:
    """Process a single time slot and return generated shifts."""
    available, rejection_log = _filter_available_employees(employees, date_str, slot, schedule)
    
    if len(available) < slot.required_staff:
        raise ShiftGenerationError(
            _create_insufficient_staff_error(date_str, slot, available, rejection_log)
        )
    
    assignments = _assign_employees_to_slot(
        available, slot, date_str, optimisation_mode, work_count, morning_workers, pattern_usage_count
    )
    
    if len(assignments) < slot.required_staff:
        issue = ShiftGenerationIssue(
            code="selection_failed",
            message=(
                f"{date_str} {slot.display_name}の割り当てに失敗しました。"
                "最適化パラメータを見直してください。"
            ),
            date=date_str,
            time_slot_id=slot.id,
            time_slot_name=slot.display_name,
            required=slot.required_staff,
            available=len(available),
            shortage=slot.required_staff - len(assignments),
            available_employees=[emp.name for emp in available],
        )
        raise ShiftGenerationError(issue)
    
    shifts = []
    for employee, pattern_id in assignments:
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
            employment_pattern_id=pattern_id,
        )
        shifts.append(shift)
        work_count[employee.id] += 1
    
    return shifts


def _process_daily_slots(
    date_str: str,
    daily_slots: List[TimeSlot],
    employees: Sequence[Employee],
    schedule: List[GeneratedShift],
    work_count: Dict[int, int],
    optimisation_mode: str,
    time_slots: Sequence[TimeSlot],
    pattern_usage_count: Dict[Tuple[int, str], int],
) -> List[GeneratedShift]:
    """Process all slots for a single day and return generated shifts."""
    morning_slots = [s for s in daily_slots if s.period == "morning"]
    afternoon_slots = [s for s in daily_slots if s.period == "afternoon"]
    
    morning_workers_by_area: Dict[str, List[int]] = {}
    daily_assignments: List[GeneratedShift] = []

    # Process morning slots
    for slot in morning_slots:
        shifts = _process_time_slot(
            slot, date_str, employees, schedule, work_count, optimisation_mode, [], pattern_usage_count
        )
        schedule.extend(shifts)
        daily_assignments.extend(shifts)
        # Track morning workers by area
        for shift in shifts:
            morning_workers_by_area.setdefault(slot.area, []).append(shift.employee_id)

    # Process afternoon slots with morning worker preference
    for slot in afternoon_slots:
        morning_workers = morning_workers_by_area.get(slot.area, [])
        shifts = _process_time_slot(
            slot, date_str, employees, schedule, work_count, optimisation_mode, morning_workers, pattern_usage_count
        )
        schedule.extend(shifts)
        daily_assignments.extend(shifts)

    # Validate part-time rule for the day
    if daily_assignments:
        violation = _evaluate_part_time_rule(daily_assignments, time_slots)
        if violation:
            raise ShiftGenerationError(violation)
    
    return daily_assignments


def generate_shifts(
    employees: Sequence[Employee],
    time_slots: Sequence[TimeSlot],
    start_date: str,
    end_date: str,
    *,
    optimisation_mode: str = "balance",
) -> List[GeneratedShift]:
    _validate_shift_inputs(employees, time_slots, start_date, end_date)

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    schedule: List[GeneratedShift] = []
    work_count: Dict[int, int] = {emp.id: 0 for emp in employees}
    pattern_usage_count: Dict[Tuple[int, str], int] = {}

    all_slots_by_day: Dict[int, List[TimeSlot]] = {}
    for slot in time_slots:
        all_slots_by_day.setdefault(slot.day_of_week, []).append(slot)

    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        weekday = current.weekday()
        daily_slots = all_slots_by_day.get(weekday, [])

        _process_daily_slots(
            date_str, daily_slots, employees, schedule, work_count, optimisation_mode, time_slots, pattern_usage_count
        )

        current += timedelta(days=1)

    return schedule


def calculate_skill_balance(shifts: Sequence[GeneratedShift], time_slots: Sequence[TimeSlot]) -> Dict[str, float]:
    """スキルバランスの統計を計算する。
    
    各時間帯のスキル合計を計算し、その平均値と標準偏差を算出する。
    標準偏差が小さいほど、日によるスキル能力の偏りが少なく、
    安定したサービス品質が提供できることを示す。
    """
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


def calculate_pattern_distribution(shifts: Sequence[GeneratedShift]) -> Dict[int, Dict[str, int]]:
    """勤務パターンの分布を計算する。
    
    各職員がどのパターンを何回使用しているかを集計し、
    パターンの偏りを検証するための統計情報を提供する。
    
    Args:
        shifts: 生成されたシフトのリスト
    
    Returns:
        {employee_id: {pattern_id: count}} の辞書
        例: {1: {"weekday_full_A": 3, "weekday_full_B": 2, "weekday_full_C": 2}}
    """
    distribution: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    for shift in shifts:
        if shift.employment_pattern_id and shift.employee_id:
            distribution[shift.employee_id][shift.employment_pattern_id] += 1
    
    # defaultdictを通常のdictに変換
    return {emp_id: dict(patterns) for emp_id, patterns in distribution.items()}
