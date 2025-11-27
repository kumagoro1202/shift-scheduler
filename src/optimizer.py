"""
シフト最適化エンジン
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import random


def check_time_overlap(ts1: Dict[str, Any], ts2: Dict[str, Any]) -> bool:
    """2つの時間帯が重なっているかチェック"""
    # 時刻を分に変換
    def time_to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    
    start1 = time_to_minutes(ts1['start_time'])
    end1 = time_to_minutes(ts1['end_time'])
    start2 = time_to_minutes(ts2['start_time'])
    end2 = time_to_minutes(ts2['end_time'])
    
    # 夜勤など日をまたぐ場合の処理
    if end1 < start1:  # ts1が日をまたぐ
        end1 += 24 * 60
    if end2 < start2:  # ts2が日をまたぐ
        end2 += 24 * 60
    
    # 重複チェック
    return not (end1 <= start2 or end2 <= start1)


def generate_shift(
    employees: List[Dict[str, Any]],
    time_slots: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
    availability_func=None
) -> Optional[List[Dict[str, Any]]]:
    """
    シフトを最適化して生成（グリーディアルゴリズム）
    
    Args:
        employees: 職員リスト
        time_slots: 時間帯リスト
        start_date: 開始日 (YYYY-MM-DD)
        end_date: 終了日 (YYYY-MM-DD)
        availability_func: 勤務可能チェック関数
    
    Returns:
        生成されたシフトのリスト（失敗時はNone）
    """
    try:
        if not employees or not time_slots:
            print("❌ エラー: 職員または時間帯が空です")
            return None
        
        print(f"📊 最適化開始: 職員{len(employees)}名, 時間帯{len(time_slots)}個")
    
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
        
        # 時間帯名から種類を判定（午前、午後、1日通し）
        def get_slot_type(ts_name: str) -> str:
            if '午前' in ts_name:
                return 'morning'
            elif '午後' in ts_name:
                return 'afternoon'
            elif '1日' in ts_name or '通し' in ts_name:
                return 'fullday'
            return 'other'
        
        # 各日付について処理（時間帯の順序を制御）
        for date in dates:
            # まず1日通しを割り当て
            fullday_slots = [ts for ts in time_slots if get_slot_type(ts['name']) == 'fullday']
            morning_slots = [ts for ts in time_slots if get_slot_type(ts['name']) == 'morning']
            afternoon_slots = [ts for ts in time_slots if get_slot_type(ts['name']) == 'afternoon']
            
            # 1日通しの割り当て数を記録
            fullday_assigned = 0
            
            # 処理順序: 1日通し → 午前 → 午後
            ordered_slots = fullday_slots + morning_slots + afternoon_slots
            
            for ts in ordered_slots:
                slot_type = get_slot_type(ts['name'])
                
                # 動的に必要人数を計算
                required = ts['required_employees']
                
                if slot_type == 'morning' or slot_type == 'afternoon':
                    # 午前・午後は、1日通しの人数に応じて必要人数を調整
                    # 目標: 各時間帯に合計2名
                    required = max(0, 2 - fullday_assigned)
                elif slot_type == 'fullday':
                    # 1日通しは最大2名
                    required = min(ts['required_employees'], 2)
                
                # 必要人数が0の場合はスキップ
                if required == 0:
                    continue
                
                # この時間帯に勤務可能な職員リスト
                available_employees = []
                for emp in employees:
                    # すでにこの日の時間が重なるシフトに勤務しているかチェック
                    conflicting_shift = any(
                        s['employee_id'] == emp['id'] and 
                        s['date'] == date and
                        check_time_overlap(ts, {'start_time': s['start_time'], 'end_time': s['end_time']})
                        for s in shifts
                    )
                    if conflicting_shift:
                        continue
                    
                    # 勤務可能かチェック
                    if availability_func and not availability_func(emp['id'], date, ts['id']):
                        continue
                    
                    available_employees.append(emp)
                
                # 必要人数に満たない場合はエラー
                if len(available_employees) < required:
                    print(f"❌ {date} {ts['name']}: 勤務可能{len(available_employees)}名 < 必要{required}名")
                    
                    # 診断情報を出力
                    print(f"\n🔍 診断情報:")
                    print(f"   職員総数: {len(employees)}名")
                    print(f"   この時間帯と時間が重なる他のシフト:")
                    for s in shifts:
                        if s['date'] == date:
                            s_ts = {'start_time': s['start_time'], 'end_time': s['end_time']}
                            if check_time_overlap(ts, s_ts):
                                print(f"     - {s['time_slot_name']} ({s['start_time']}-{s['end_time']}): {s['employee_name']}")
                    
                    print(f"\n💡 ヒント:")
                    print(f"   1. 時間が重なる時間帯の必要人数の合計が職員数を超えています")
                    print(f"   2. 解決方法:")
                    print(f"      - 職員を追加する")
                    print(f"      - 勤務可能情報で「勤務不可」の設定を見直す")
                    
                    return None
                
                # 勤務回数が少ない順にソート（スキルスコアも考慮）
                selected_employees = []
                
                # 必要人数だけ選択
                for _ in range(required):
                    if not available_employees:
                        break
                    
                    # 勤務回数が最も少ない職員を選択
                    # 同じ勤務回数の場合は、現在のシフトのスキルバランスを考慮
                    min_work_count = min(work_count[emp['id']] for emp in available_employees)
                    candidates = [emp for emp in available_employees if work_count[emp['id']] == min_work_count]
                    
                    # 平均スキルに近い職員を選択
                    avg_skill = sum(emp['skill_score'] for emp in employees) / len(employees)
                    target_skill = avg_skill
                    
                    if selected_employees:
                        # すでに選択された職員のスキル平均を考慮
                        current_avg = sum(e['skill_score'] for e in selected_employees) / len(selected_employees)
                        # 目標との差を埋める
                        target_skill = avg_skill * (len(selected_employees) + 1) - current_avg * len(selected_employees)
                    
                    # 目標スキルに最も近い職員を選択
                    selected = min(candidates, key=lambda e: abs(e['skill_score'] - target_skill))
                    
                    selected_employees.append(selected)
                    available_employees.remove(selected)
                    work_count[selected['id']] += 1
                
                # シフトに追加
                for emp in selected_employees:
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
                
                # 1日通しを割り当てた場合は、その人数を記録
                if slot_type == 'fullday':
                    fullday_assigned += len(selected_employees)
        
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
