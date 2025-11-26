"""
シフト最適化エンジン
"""
from pulp import *
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd


def generate_shift(
    employees: List[Dict[str, Any]],
    time_slots: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
    availability_func=None
) -> Optional[List[Dict[str, Any]]]:
    """
    シフトを最適化して生成
    
    Args:
        employees: 職員リスト
        time_slots: 時間帯リスト
        start_date: 開始日 (YYYY-MM-DD)
        end_date: 終了日 (YYYY-MM-DD)
        availability_func: 勤務可能チェック関数
    
    Returns:
        生成されたシフトのリスト（失敗時はNone）
    """
    if not employees or not time_slots:
        return None
    
    # 日付リストを生成
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    # 問題の定義
    prob = LpProblem("ShiftScheduling", LpMinimize)
    
    # 決定変数: x[employee_id][date][time_slot_id] = 0 or 1
    x = {}
    for emp in employees:
        x[emp['id']] = {}
        for date in dates:
            x[emp['id']][date] = {}
            for ts in time_slots:
                var_name = f"x_{emp['id']}_{date}_{ts['id']}"
                x[emp['id']][date][ts['id']] = LpVariable(var_name, cat='Binary')
    
    # 目標スキルスコアの計算（全職員の平均）
    total_skill = sum(emp['skill_score'] for emp in employees)
    avg_skill = total_skill / len(employees) if employees else 50
    
    # 目的関数: 各時間帯のスキルスコアの偏差を最小化
    # 各日・各時間帯のスキル合計と目標値の差の絶対値を最小化
    deviations = []
    for date in dates:
        for ts in time_slots:
            # この時間帯のスキル合計
            skill_sum = lpSum([
                x[emp['id']][date][ts['id']] * emp['skill_score']
                for emp in employees
            ])
            # 目標値（必要人数 × 平均スキル）
            target = ts['required_employees'] * avg_skill
            
            # 偏差変数（正と負）
            dev_pos = LpVariable(f"dev_pos_{date}_{ts['id']}", lowBound=0)
            dev_neg = LpVariable(f"dev_neg_{date}_{ts['id']}", lowBound=0)
            
            # skill_sum - target = dev_pos - dev_neg
            prob += skill_sum - target == dev_pos - dev_neg
            
            deviations.append(dev_pos + dev_neg)
    
    prob += lpSum(deviations)
    
    # 制約1: 各時間帯の必要人数を満たす
    for date in dates:
        for ts in time_slots:
            prob += lpSum([
                x[emp['id']][date][ts['id']]
                for emp in employees
            ]) == ts['required_employees'], f"Required_{date}_{ts['id']}"
    
    # 制約2: 1人1日1シフトまで
    for emp in employees:
        for date in dates:
            prob += lpSum([
                x[emp['id']][date][ts['id']]
                for ts in time_slots
            ]) <= 1, f"OneShiftPerDay_{emp['id']}_{date}"
    
    # 制約3: 勤務可能時間のみ割り当て
    if availability_func:
        for emp in employees:
            for date in dates:
                for ts in time_slots:
                    if not availability_func(emp['id'], date, ts['id']):
                        prob += x[emp['id']][date][ts['id']] == 0, \
                            f"Availability_{emp['id']}_{date}_{ts['id']}"
    
    # ソルバー実行
    solver = PULP_CBC_CMD(msg=0, timeLimit=60)
    status = prob.solve(solver)
    
    # 結果の取得
    if status != LpStatusOptimal:
        return None
    
    # シフトリストの作成
    shifts = []
    for emp in employees:
        for date in dates:
            for ts in time_slots:
                if value(x[emp['id']][date][ts['id']]) == 1:
                    shifts.append({
                        'date': date,
                        'time_slot_id': ts['id'],
                        'employee_id': emp['id'],
                        'employee_name': emp['name'],
                        'skill_score': emp['skill_score'],
                        'time_slot_name': ts['name'],
                        'start_time': ts['start_time'],
                        'end_time': ts['end_time']
                    })
    
    return shifts


def calculate_skill_balance(shifts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    シフトのスキルバランスを計算
    
    Returns:
        統計情報（平均、標準偏差など）
    """
    if not shifts:
        return {
            'avg_skill': 0,
            'std_skill': 0,
            'min_skill': 0,
            'max_skill': 0
        }
    
    df = pd.DataFrame(shifts)
    
    # 日時・時間帯ごとのグループ化
    grouped = df.groupby(['date', 'time_slot_id'])['skill_score'].sum()
    
    return {
        'avg_skill': grouped.mean(),
        'std_skill': grouped.std(),
        'min_skill': grouped.min(),
        'max_skill': grouped.max(),
        'balance_score': grouped.std() / grouped.mean() if grouped.mean() > 0 else 0
    }
