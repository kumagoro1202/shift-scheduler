"""
シフト最適化エンジン
4項目スキルスコア、職員タイプ制約、休暇管理対応
V3.0仕様: availability_checkerを使用した勤務可否判定
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
from availability_checker import is_employee_available


def check_time_overlap(ts1: Dict[str, Any], ts2: Dict[str, Any]) -> bool:
    """2つの時間帯が重なっているかチェック"""
    def time_to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    
    start1 = time_to_minutes(ts1['start_time'])
    end1 = time_to_minutes(ts1['end_time'])
    start2 = time_to_minutes(ts2['start_time'])
    end2 = time_to_minutes(ts2['end_time'])
    
    # 夜勤など日をまたぐ場合の処理
    if end1 < start1:
        end1 += 24 * 60
    if end2 < start2:
        end2 += 24 * 60
    
    return not (end1 <= start2 or end2 <= start1)


def calculate_skill_score(employee: Dict[str, Any], time_slot: Dict[str, Any]) -> int:
    """
    時間帯に適したスキルスコアを計算
    
    仕様書 § 6.2:
    - リハ室: リハ室スキル + 総合対応力
    - 受付（午前）: 受付午前スキル + 総合対応力
    - 受付（午後）: 受付午後スキル + 総合対応力
    
    Args:
        employee: 職員情報
        time_slot: 時間帯情報
    
    Returns:
        適用されるスキルスコア
    """
    area_type = time_slot.get('area_type', '受付')
    time_period = time_slot.get('time_period', '終日')
    general_skill = employee.get('skill_general', employee.get('skill_score', 0))
    
    if area_type == 'リハ室':
        reha_skill = employee.get('skill_reha', employee.get('skill_score', 0))
        return reha_skill + general_skill
    elif area_type == '受付':
        if time_period == '午前':
            am_skill = employee.get('skill_reception_am', employee.get('skill_score', 0))
            return am_skill + general_skill
        elif time_period == '午後':
            pm_skill = employee.get('skill_reception_pm', employee.get('skill_score', 0))
            return pm_skill + general_skill
        else:  # 終日
            # 午前と午後の平均 + 総合対応力
            am_skill = employee.get('skill_reception_am', employee.get('skill_score', 0))
            pm_skill = employee.get('skill_reception_pm', employee.get('skill_score', 0))
            return ((am_skill + pm_skill) // 2) + general_skill
    
    # フォールバック: 総合対応力
    return general_skill


def can_assign_to_area(employee: Dict[str, Any], time_slot: Dict[str, Any]) -> bool:
    """
    職員が時間帯に配置可能かチェック
    
    Args:
        employee: 職員情報
        time_slot: 時間帯情報
    
    Returns:
        配置可能ならTrue
    """
    area_type = time_slot.get('area_type', '受付')
    emp_type = employee.get('employee_type', 'TYPE_A')
    
    if area_type == 'リハ室':
        # リハ室にはTYPE_A, TYPE_C, TYPE_Dのみ
        if emp_type not in ['TYPE_A', 'TYPE_C', 'TYPE_D']:
            return False
        # リハ室スキルが0以下は不可
        if employee.get('skill_reha', 0) <= 0:
            return False
    
    elif area_type == '受付':
        # 受付にはTYPE_A, TYPE_Bのみ
        if emp_type not in ['TYPE_A', 'TYPE_B']:
            return False
        # 受付スキル（午前または午後）が0以下は不可
        am_skill = employee.get('skill_reception_am', 0)
        pm_skill = employee.get('skill_reception_pm', 0)
        if am_skill <= 0 and pm_skill <= 0:
            return False
    
    return True


def calculate_objective_value(
    shifts_for_slot: List[Dict[str, Any]],
    time_slot: Dict[str, Any],
    employees_data: List[Dict[str, Any]]
) -> float:
    """
    時間帯のシフトの目的関数値を計算（小さいほど良い）
    
    Args:
        shifts_for_slot: この時間帯のシフトリスト
        time_slot: 時間帯情報
        employees_data: 職員データ（シフトに紐づいている）
    
    Returns:
        目的関数値（目標値との差分 × 重み）
    """
    # 実際のスキルスコア合計を計算
    actual_score = sum(
        calculate_skill_score(emp, time_slot)
        for emp in employees_data
    )
    
    # 目標値を動的に計算
    # V3.0仕様: スキルスコアは基礎スキル + 総合対応力で最大200点/人
    # 目標値 = 必要人数 × 平均目標スキル（例：150点/人）
    required_staff = time_slot.get('required_staff', 2)
    target_per_person = 150  # 基礎スキル75点 + 総合対応力75点
    target_score = time_slot.get('target_skill_score', required_staff * target_per_person)
    
    weight = time_slot.get('skill_weight', 1.0)
    
    # 差分の絶対値 × 重み
    deviation = weight * abs(actual_score - target_score)
    
    return deviation
    weight = time_slot.get('skill_weight', 1.0)
    
    # 差分の絶対値 × 重み
    deviation = weight * abs(actual_score - target_score)
    
    return deviation


def apply_part_time_rule(
    date: str,
    time_slots: List[Dict[str, Any]],
    shifts_for_date: List[Dict[str, Any]]
) -> bool:
    """
    パート職員（TYPE_D）出勤時の特殊ルールをチェック
    
    ルール:
    - TYPE_Dがリハ室に配置される日は、
    - リハ室: TYPE_C or TYPE_A (1名) + TYPE_D (1名)
    - 受付: TYPE_A (1名) または TYPE_B (1名)
    
    Args:
        date: 日付
        time_slots: 時間帯リスト
        shifts_for_date: この日のシフトリスト
    
    Returns:
        ルールを満たしていればTrue
    """
    # TYPE_Dの出勤チェック
    type_d_shifts = [
        s for s in shifts_for_date
        if s['employee'].get('employee_type') == 'TYPE_D'
    ]
    
    if not type_d_shifts:
        return True  # TYPE_Dがいない場合は問題なし
    
    # リハ室のTYPE_Dシフトを取得
    reha_type_d = [
        s for s in type_d_shifts
        if s['time_slot'].get('area_type') == 'リハ室'
    ]
    
    if not reha_type_d:
        return True  # リハ室にTYPE_Dがいない場合は問題なし
    
    # リハ室シフトの構成をチェック
    for ts in time_slots:
        if ts.get('area_type') != 'リハ室':
            continue
        
        slot_shifts = [
            s for s in shifts_for_date
            if s['time_slot_id'] == ts['id']
        ]
        
        if not slot_shifts:
            continue
        
        emp_types = [s['employee'].get('employee_type') for s in slot_shifts]
        
        # TYPE_Dがいる場合、TYPE_AまたはTYPE_Cも必要
        if 'TYPE_D' in emp_types:
            if 'TYPE_A' not in emp_types and 'TYPE_C' not in emp_types:
                return False
    
    return True


def generate_shift_v2(
    employees: List[Dict[str, Any]],
    time_slots: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
    availability_func=None,
    optimization_mode: str = 'balance'
) -> Optional[List[Dict[str, Any]]]:
    """
    シフトを最適化して生成（V2.0 - グリーディアルゴリズム）
    
    Args:
        employees: 職員リスト
        time_slots: 時間帯リスト
        start_date: 開始日 (YYYY-MM-DD)
        end_date: 終了日 (YYYY-MM-DD)
        availability_func: 勤務可能チェック関数
        optimization_mode: 最適化モード ('balance', 'skill', 'days')
    
    Returns:
        生成されたシフトのリスト（失敗時はNone）
    """
    try:
        if not employees or not time_slots:
            print("❌ エラー: 職員または時間帯が空です")
            return None
        
        print(f"📊 最適化開始 (V2.0): 職員{len(employees)}名, 時間帯{len(time_slots)}個")
        print(f"🎯 最適化モード: {optimization_mode}")
        
        # 日付リストを生成
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        print(f"📅 期間: {start_date} 〜 {end_date} ({len(dates)}日間)")
        
        # 勤務回数を記録
        work_count = {emp['id']: 0 for emp in employees}
        shifts = []
        
        # 各日付について処理
        for date in dates:
            # 日ごとのシフトリスト（パートタイム特殊ルールチェック用）
            shifts_for_date = []
            
            # V3: 日付の曜日を取得して、該当する時間帯のみをフィルタリング
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            day_of_week = date_obj.weekday()  # 月曜=0, 日曜=6
            
            # この日付に該当する時間帯を抽出
            # V3スキーマ（day_of_weekカラムあり）とV2互換（なし）を両対応
            if time_slots and 'day_of_week' in time_slots[0]:
                # V3モード: day_of_weekでフィルタリング
                daily_time_slots = [ts for ts in time_slots if ts.get('day_of_week') == day_of_week and ts.get('is_active', True)]
            else:
                # V2互換モード: 全時間帯を使用
                daily_time_slots = time_slots
            
            # 各時間帯について処理
            for ts in daily_time_slots:
                # 必要人数の範囲
                req_min = ts.get('required_employees_min', 1)
                req_max = ts.get('required_employees_max', ts.get('required_employees', 2))
                
                # この時間帯に勤務可能な職員リスト
                available_employees = []
                for emp in employees:
                    # 職員タイプとエリアの整合性チェック
                    if not can_assign_to_area(emp, ts):
                        continue
                    
                    # 時間が重なるシフトに勤務しているかチェック
                    conflicting_shift = any(
                        s['employee_id'] == emp['id'] and 
                        s['date'] == date and
                        check_time_overlap(ts, s['time_slot'])
                        for s in shifts
                    )
                    if conflicting_shift:
                        continue
                    
                    # V3.0: availability_checkerを使用した勤務可否チェック
                    # availability_funcが指定されている場合は従来の方法（V2互換）
                    # 指定されていない場合はavailability_checkerを使用（V3）
                    if availability_func:
                        # V2互換モード: 従来のavailability_func使用
                        if not availability_func(emp['id'], date, ts['id']):
                            continue
                    else:
                        # V3モード: availability_checkerを使用
                        if not is_employee_available(emp, date, ts):
                            continue
                    
                    available_employees.append(emp)
                
                # 最小人数に満たない場合はエラー
                if len(available_employees) < req_min:
                    print(f"❌ {date} {ts.get('display_name', ts.get('name', ts['id']))}: 勤務可能{len(available_employees)}名 < 最小必要{req_min}名")
                    return None
                
                # 最適な人数を決定（req_min 〜 req_max の範囲）
                # モードによって選択基準を変更
                best_count = req_min
                best_employees = []
                best_score = float('inf')
                
                for count in range(req_min, min(req_max + 1, len(available_employees) + 1)):
                    # この人数で最適な組み合わせを探索
                    candidates = select_employees_for_slot(
                        available_employees,
                        ts,
                        count,
                        work_count,
                        optimization_mode
                    )
                    
                    if not candidates:
                        continue
                    
                    # 目的関数値を計算
                    score = calculate_objective_value([], ts, candidates)
                    
                    if score < best_score:
                        best_score = score
                        best_count = count
                        best_employees = candidates
                
                # 選択された職員でシフトを追加
                for emp in best_employees:
                    shift = {
                        'date': date,
                        'time_slot_id': ts['id'],
                        'employee_id': emp['id'],
                        'employee_name': emp['name'],
                        'skill_score': calculate_skill_score(emp, ts),
                        'time_slot_name': ts.get('display_name', ts.get('name', 'Unknown')),
                        'start_time': ts['start_time'],
                        'end_time': ts['end_time'],
                        'employee': emp,  # チェック用
                        'time_slot': ts  # チェック用
                    }
                    shifts.append(shift)
                    shifts_for_date.append(shift)
                    work_count[emp['id']] += 1
            
            # パートタイム特殊ルールのチェック
            if not apply_part_time_rule(date, time_slots, shifts_for_date):
                print(f"⚠️ {date}: パートタイム特殊ルールに違反")
                # ここでは警告のみ（必要に応じて調整）
        
        # employee, time_slotフィールドを削除（永続化用）
        for s in shifts:
            s.pop('employee', None)
            s.pop('time_slot', None)
        
        print(f"✅ シフト生成成功: {len(shifts)}件")
        
        # 勤務回数の統計
        work_counts = list(work_count.values())
        print(f"📊 勤務回数: 最小{min(work_counts)}回, 最大{max(work_counts)}回, 平均{sum(work_counts)/len(work_counts):.1f}回")
        
        return shifts
    
    except Exception as e:
        print(f"❌ エラー発生: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def select_employees_for_slot(
    available_employees: List[Dict[str, Any]],
    time_slot: Dict[str, Any],
    count: int,
    work_count: Dict[int, int],
    optimization_mode: str
) -> List[Dict[str, Any]]:
    """
    時間帯に配置する職員を選択
    
    Args:
        available_employees: 候補職員リスト
        time_slot: 時間帯情報
        count: 選択する人数
        work_count: 各職員の勤務回数
        optimization_mode: 最適化モード
    
    Returns:
        選択された職員リスト
    """
    if len(available_employees) < count:
        return []
    
    selected = []
    remaining = available_employees.copy()
    
    for _ in range(count):
        if not remaining:
            break
        
        # 最適化モードに応じて選択
        if optimization_mode == 'days':
            # 勤務回数重視: 最も少ない人を優先
            min_work = min(work_count[emp['id']] for emp in remaining)
            candidates = [emp for emp in remaining if work_count[emp['id']] == min_work]
            selected_emp = candidates[0]
        
        elif optimization_mode == 'skill':
            # スキル重視: 目標値に近づける
            target_score = time_slot.get('target_skill_score', 150)
            current_score = sum(calculate_skill_score(e, time_slot) for e in selected)
            target_next = (target_score - current_score) / (count - len(selected))
            
            selected_emp = min(
                remaining,
                key=lambda e: abs(calculate_skill_score(e, time_slot) - target_next)
            )
        
        else:  # 'balance'
            # バランス重視: 勤務回数とスキルの両方を考慮
            min_work = min(work_count[emp['id']] for emp in remaining)
            candidates = [emp for emp in remaining if work_count[emp['id']] == min_work]
            
            target_score = time_slot.get('target_skill_score', 150)
            current_score = sum(calculate_skill_score(e, time_slot) for e in selected)
            target_next = (target_score - current_score) / (count - len(selected)) if count > len(selected) else 0
            
            selected_emp = min(
                candidates,
                key=lambda e: abs(calculate_skill_score(e, time_slot) - target_next)
            )
        
        selected.append(selected_emp)
        remaining.remove(selected_emp)
    
    return selected


def calculate_skill_balance_v2(shifts: List[Dict[str, Any]], time_slots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    シフトのスキルバランスを計算（V2.0）
    
    Args:
        shifts: シフトリスト
        time_slots: 時間帯リスト
    
    Returns:
        統計情報
    """
    if not shifts:
        return {
            'avg_skill': 0,
            'std_skill': 0,
            'min_skill': 0,
            'max_skill': 0
        }
    
    # 時間帯ごとのスキルスコア合計を計算
    slot_scores = {}
    for ts in time_slots:
        ts_shifts = [s for s in shifts if s['time_slot_id'] == ts['id']]
        if ts_shifts:
            total_score = sum(s['skill_score'] for s in ts_shifts)
            slot_scores[ts['id']] = total_score
    
    if not slot_scores:
        return {
            'avg_skill': 0,
            'std_skill': 0,
            'min_skill': 0,
            'max_skill': 0
        }
    
    scores = list(slot_scores.values())
    avg = sum(scores) / len(scores)
    variance = sum((x - avg) ** 2 for x in scores) / len(scores)
    std = variance ** 0.5
    
    return {
        'avg_skill': avg,
        'std_skill': std,
        'min_skill': min(scores),
        'max_skill': max(scores),
        'balance_score': std / avg if avg > 0 else 0
    }
