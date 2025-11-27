"""
勤務可否判定ロジック（V3.0）
"""
from datetime import datetime
from typing import Optional, Dict, Any
from database import (
    get_employment_pattern_by_id,
    get_absence
)


def is_employee_available(employee: Dict[str, Any], date_str: str, time_slot: Dict[str, Any]) -> bool:
    """
    職員が指定日の指定時間帯に勤務可能かを判定
    
    Args:
        employee: 職員情報（dict）
        date_str: 日付文字列 (YYYY-MM-DD)
        time_slot: 時間帯情報（dict）
    
    Returns:
        bool: 勤務可能ならTrue
    """
    # 1. 時間帯が休診の場合
    if not time_slot.get('is_active', True):
        return False
    
    # 2. 日曜日チェック
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if date_obj.weekday() == 6:  # 日曜日
            return False
    except ValueError:
        return False
    
    # 3. 休暇チェック
    absence = get_absence(employee['id'], date_str)
    if absence:
        if absence['absence_type'] == 'full_day':
            return False
        if absence['absence_type'] == 'morning' and time_slot.get('period') == 'morning':
            return False
        if absence['absence_type'] == 'afternoon' and time_slot.get('period') == 'afternoon':
            return False
    
    # 4. 勤務形態チェック（V3.0）
    pattern_id = employee.get('employment_pattern_id')
    if pattern_id:
        pattern = get_employment_pattern_by_id(pattern_id)
        if not pattern:
            # パターンが見つからない場合は勤務不可
            return False
        
        # 午後勤務可否チェック
        if time_slot.get('period') == 'afternoon' and not pattern.get('can_work_afternoon', True):
            return False
        
        # 勤務時間範囲チェック
        try:
            slot_start = datetime.strptime(time_slot['start_time'], "%H:%M").time()
            slot_end = datetime.strptime(time_slot['end_time'], "%H:%M").time()
            pattern_start = datetime.strptime(pattern['start_time'], "%H:%M").time()
            pattern_end = datetime.strptime(pattern['end_time'], "%H:%M").time()
            
            # スロット開始時刻が勤務可能時間の前、またはスロット終了時刻が勤務可能時間の後の場合は不可
            if slot_start < pattern_start or slot_end > pattern_end:
                return False
        except (ValueError, KeyError):
            # 時刻のパースエラーの場合は安全側に倒して勤務不可
            return False
    
    # V2.0互換: work_patternによるチェック（employment_pattern_idがない場合）
    # 時短勤務やパートは午後勤務不可
    elif employee.get('work_pattern') in ['P4', 'PT1', 'PT2'] or employee.get('work_type') in ['時短勤務', 'パートタイム']:
        if time_slot.get('period') == 'afternoon':
            return False
    
    return True


def get_available_time_slots_for_date(employee: Dict[str, Any], date_str: str, all_time_slots: list) -> list:
    """
    指定日に勤務可能な時間帯のリストを取得
    
    Args:
        employee: 職員情報
        date_str: 日付文字列 (YYYY-MM-DD)
        all_time_slots: 全時間帯のリスト
    
    Returns:
        list: 勤務可能な時間帯のリスト
    """
    return [
        ts for ts in all_time_slots
        if is_employee_available(employee, date_str, ts)
    ]


def get_unavailable_reason(employee: Dict[str, Any], date_str: str, time_slot: Dict[str, Any]) -> Optional[str]:
    """
    勤務不可の理由を取得（デバッグ用）
    
    Args:
        employee: 職員情報
        date_str: 日付文字列
        time_slot: 時間帯情報
    
    Returns:
        str: 勤務不可の理由（勤務可能な場合はNone）
    """
    # 時間帯が休診の場合
    if not time_slot.get('is_active', True):
        return "時間帯が休診"
    
    # 日曜日チェック
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if date_obj.weekday() == 6:
            return "日曜日（定休日）"
    except ValueError:
        return "日付形式エラー"
    
    # 休暇チェック
    absence = get_absence(employee['id'], date_str)
    if absence:
        if absence['absence_type'] == 'full_day':
            return f"終日休暇（{absence.get('reason', '')}）"
        if absence['absence_type'] == 'morning' and time_slot.get('period') == 'morning':
            return f"午前休（{absence.get('reason', '')}）"
        if absence['absence_type'] == 'afternoon' and time_slot.get('period') == 'afternoon':
            return f"午後休（{absence.get('reason', '')}）"
    
    # 勤務形態チェック
    pattern_id = employee.get('employment_pattern_id')
    if pattern_id:
        pattern = get_employment_pattern_by_id(pattern_id)
        if not pattern:
            return "勤務形態が見つかりません"
        
        if time_slot.get('period') == 'afternoon' and not pattern.get('can_work_afternoon', True):
            return f"午後勤務不可（{pattern['name']}）"
        
        try:
            slot_start = datetime.strptime(time_slot['start_time'], "%H:%M").time()
            slot_end = datetime.strptime(time_slot['end_time'], "%H:%M").time()
            pattern_start = datetime.strptime(pattern['start_time'], "%H:%M").time()
            pattern_end = datetime.strptime(pattern['end_time'], "%H:%M").time()
            
            if slot_start < pattern_start:
                return f"勤務開始時刻前（勤務開始: {pattern['start_time']}）"
            if slot_end > pattern_end:
                return f"勤務終了時刻後（勤務終了: {pattern['end_time']}）"
        except (ValueError, KeyError):
            return "時刻フォーマットエラー"
    
    # V2.0互換チェック
    elif employee.get('work_pattern') in ['P4', 'PT1', 'PT2'] or employee.get('work_type') in ['時短勤務', 'パートタイム']:
        if time_slot.get('period') == 'afternoon':
            return f"午後勤務不可（{employee.get('work_type', employee.get('work_pattern'))}）"
    
    return None  # 勤務可能
