"""
シフト作成システム - 休憩時間自動割り当て機能
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from src.database import (
    get_work_pattern_by_id,
    create_break_schedule,
    get_break_schedules_by_date
)


def parse_time(time_str: str) -> datetime:
    """時刻文字列をdatetimeオブジェクトに変換"""
    return datetime.strptime(time_str, "%H:%M")


def format_time(dt: datetime) -> str:
    """datetimeオブジェクトを時刻文字列に変換"""
    return dt.strftime("%H:%M")


def generate_time_intervals(start_time: str, end_time: str, interval_minutes: int = 15) -> List[Tuple[str, str]]:
    """
    指定された時間範囲を指定間隔で分割
    
    Args:
        start_time: 開始時刻 (例: "08:30")
        end_time: 終了時刻 (例: "19:00")
        interval_minutes: 分割間隔（分）
    
    Returns:
        時間帯のリスト [(開始, 終了), ...]
    """
    start_dt = parse_time(start_time)
    end_dt = parse_time(end_time)
    intervals = []
    
    current = start_dt
    while current < end_dt:
        next_time = current + timedelta(minutes=interval_minutes)
        if next_time > end_dt:
            next_time = end_dt
        intervals.append((format_time(current), format_time(next_time)))
        current = next_time
    
    return intervals


def generate_break_slots(break_hours: float, break_division: int) -> List[Dict[str, Any]]:
    """
    休憩時間の候補時間帯を生成
    
    Args:
        break_hours: 総休憩時間（時間）
        break_division: 休憩分割回数
    
    Returns:
        休憩候補のリスト
    """
    if break_hours == 0 or break_division == 0:
        return []
    
    # 休憩可能時間帯: 11:00-14:00
    break_start = parse_time("11:00")
    break_end = parse_time("14:00")
    
    # 1回あたりの休憩時間（分）
    break_minutes_per_slot = int((break_hours / break_division) * 60)
    
    slots = []
    
    if break_division == 1:
        # 1回休憩: 中央付近
        slot_start = parse_time("12:00")
        slot_end = slot_start + timedelta(minutes=break_minutes_per_slot)
        slots.append({
            'number': 1,
            'start': format_time(slot_start),
            'end': format_time(slot_end)
        })
    
    elif break_division == 2:
        # 2回休憩: 均等配置
        # 1回目: 11:00-12:00
        slot1_start = parse_time("11:00")
        slot1_end = slot1_start + timedelta(minutes=break_minutes_per_slot)
        slots.append({
            'number': 1,
            'start': format_time(slot1_start),
            'end': format_time(slot1_end)
        })
        
        # 2回目: 13:00-14:00
        slot2_start = parse_time("13:00")
        slot2_end = slot2_start + timedelta(minutes=break_minutes_per_slot)
        slots.append({
            'number': 2,
            'start': format_time(slot2_start),
            'end': format_time(slot2_end)
        })
    
    return slots


def is_overlapping(time1_start: str, time1_end: str, time2_start: str, time2_end: str) -> bool:
    """
    2つの時間帯が重複しているかチェック
    
    Returns:
        True: 重複している / False: 重複していない
    """
    t1_start = parse_time(time1_start)
    t1_end = parse_time(time1_end)
    t2_start = parse_time(time2_start)
    t2_end = parse_time(time2_end)
    
    return not (t1_end <= t2_start or t2_end <= t1_start)


def assign_non_overlapping_breaks(
    employee: Dict[str, Any],
    break_slots: List[Dict[str, Any]],
    existing_breaks: List[Dict[str, Any]],
    reception_staff: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    他の職員と重複しないように休憩時間を割り当て
    
    Args:
        employee: 対象職員
        break_slots: 休憩候補時間帯
        existing_breaks: 既に割り当てられた休憩スケジュール
        reception_staff: 受付に配置されている全職員
    
    Returns:
        割り当てられた休憩スケジュール
    """
    assigned = []
    
    for slot in break_slots:
        # この時間帯に休憩している職員数をカウント
        overlapping_count = 0
        for existing in existing_breaks:
            if is_overlapping(slot['start'], slot['end'], 
                            existing['break_start_time'], existing['break_end_time']):
                overlapping_count += 1
        
        # 受付職員数から休憩中の職員を引いた人数が2名以上必要
        # 受付職員が3名以上いる場合のみ、1名が休憩可能
        reception_count = len(reception_staff)
        
        if reception_count - overlapping_count - 1 >= 2:  # この職員が休憩しても2名以上残る
            assigned.append({
                'employee_id': employee['id'],
                'break_number': slot['number'],
                'break_start_time': slot['start'],
                'break_end_time': slot['end']
            })
    
    return assigned


def count_working_staff(
    time_interval: Tuple[str, str],
    shifts_on_date: List[Dict[str, Any]],
    break_schedules: List[Dict[str, Any]]
) -> int:
    """
    指定時間帯に実働している受付職員数をカウント
    
    Args:
        time_interval: チェックする時間帯 (開始, 終了)
        shifts_on_date: その日のシフト
        break_schedules: 休憩スケジュール
    
    Returns:
        実働人数
    """
    interval_start, interval_end = time_interval
    working_count = 0
    
    # 受付に配置されている職員を抽出
    reception_shifts = [
        s for s in shifts_on_date
        if s.get('time_slot', {}).get('area_type') == '受付'
    ]
    
    for shift in reception_shifts:
        employee_id = shift['employee_id']
        
        # この職員がこの時間帯に休憩中かチェック
        is_on_break = False
        for break_sch in break_schedules:
            if break_sch['employee_id'] == employee_id:
                if is_overlapping(interval_start, interval_end,
                                break_sch['break_start_time'], break_sch['break_end_time']):
                    is_on_break = True
                    break
        
        if not is_on_break:
            working_count += 1
    
    return working_count


def validate_reception_coverage(
    date: str,
    shifts_on_date: List[Dict[str, Any]],
    break_schedules: List[Dict[str, Any]]
) -> Tuple[bool, List[str]]:
    """
    受付窓口の常駐人数が常に2名以上であることを検証
    
    Args:
        date: 対象日
        shifts_on_date: その日のシフト
        break_schedules: 休憩スケジュール
    
    Returns:
        (検証結果, 警告メッセージリスト)
    """
    warnings = []
    
    # 業務時間を15分刻みで分割
    time_intervals = generate_time_intervals("08:30", "19:00", 15)
    
    all_valid = True
    for interval in time_intervals:
        working_count = count_working_staff(interval, shifts_on_date, break_schedules)
        
        if working_count < 2:
            all_valid = False
            warnings.append(
                f"⚠️ {interval[0]}-{interval[1]}: 窓口人数不足 ({working_count}名)"
            )
    
    return all_valid, warnings


def assign_break_times(
    date: str,
    shifts_on_date: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], bool, List[str]]:
    """
    1日分のシフトに対して休憩時間を自動割り当て
    
    制約:
    1. 受付窓口には常に2名以上が実働
    2. フルタイム: 1時間×2回の休憩
    3. 時短勤務: 1時間×1回の休憩
    4. パート: 休憩なし
    5. 休憩時間は11:00-14:00の間で分散
    
    Args:
        date: 対象日 (YYYY-MM-DD形式)
        shifts_on_date: その日のシフトリスト
    
    Returns:
        (休憩スケジュールリスト, 検証結果, 警告メッセージリスト)
    """
    break_schedules = []
    
    # 受付に配置されている職員を抽出
    reception_staff = [
        s for s in shifts_on_date
        if s.get('time_slot', {}).get('area_type') == '受付'
    ]
    
    # 受付職員が2名未満の場合は休憩割り当て不可
    if len(reception_staff) < 3:
        # 2名のみの場合は休憩を割り当てない（またはシフトで交代）
        return [], True, ["受付職員が3名未満のため、休憩時間は手動調整が必要です"]
    
    # 各職員の勤務パターンを取得して休憩を割り当て
    for shift in reception_staff:
        emp = shift.get('employee', {})
        work_pattern_id = emp.get('work_pattern')
        
        if not work_pattern_id:
            continue
        
        pattern = get_work_pattern_by_id(work_pattern_id)
        if not pattern or pattern['break_hours'] == 0:
            continue  # パートは休憩なし
        
        # 休憩時間帯の候補を生成
        break_slots = generate_break_slots(
            pattern['break_hours'],
            pattern['break_division']
        )
        
        # 他の職員と重複しないよう調整
        assigned_breaks = assign_non_overlapping_breaks(
            emp, break_slots, break_schedules, reception_staff
        )
        
        break_schedules.extend(assigned_breaks)
    
    # 窓口常駐人数の検証
    is_valid, warnings = validate_reception_coverage(date, shifts_on_date, break_schedules)
    
    return break_schedules, is_valid, warnings


def save_break_schedules(
    date: str,
    shifts_on_date: List[Dict[str, Any]],
    break_schedules: List[Dict[str, Any]]
) -> int:
    """
    休憩スケジュールをデータベースに保存
    
    Args:
        date: 対象日
        shifts_on_date: その日のシフト
        break_schedules: 保存する休憩スケジュール
    
    Returns:
        保存された件数
    """
    saved_count = 0
    
    for break_sch in break_schedules:
        # 対応するシフトIDを取得
        shift = next(
            (s for s in shifts_on_date 
             if s['employee_id'] == break_sch['employee_id']),
            None
        )
        
        if shift:
            try:
                create_break_schedule(
                    shift_id=shift['id'],
                    employee_id=break_sch['employee_id'],
                    date=date,
                    break_number=break_sch['break_number'],
                    break_start_time=break_sch['break_start_time'],
                    break_end_time=break_sch['break_end_time']
                )
                saved_count += 1
            except Exception as e:
                print(f"休憩スケジュール保存エラー: {e}")
    
    return saved_count


def auto_assign_and_save_breaks(
    date: str,
    shifts_on_date: List[Dict[str, Any]]
) -> Tuple[int, bool, List[str]]:
    """
    休憩時間を自動割り当てしてデータベースに保存
    
    Args:
        date: 対象日
        shifts_on_date: その日のシフト
    
    Returns:
        (保存件数, 検証結果, 警告メッセージ)
    """
    # 休憩時間を自動割り当て
    break_schedules, is_valid, warnings = assign_break_times(date, shifts_on_date)
    
    # データベースに保存
    saved_count = save_break_schedules(date, shifts_on_date, break_schedules)
    
    return saved_count, is_valid, warnings
