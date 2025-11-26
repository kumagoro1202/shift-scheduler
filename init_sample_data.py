"""
サンプルデータ初期化スクリプト
テスト用の職員と時間帯を登録します
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).parent / "src"))

from database import (
    create_employee,
    create_time_slot,
    set_availability,
    get_all_employees,
    get_all_time_slots
)

def init_sample_data():
    """サンプルデータを初期化"""
    
    print("=" * 60)
    print("サンプルデータ初期化")
    print("=" * 60)
    
    # 既存データチェック
    existing_employees = get_all_employees()
    existing_time_slots = get_all_time_slots()
    
    if existing_employees:
        print(f"\n⚠️  既に {len(existing_employees)} 名の職員が登録されています")
        response = input("既存データを削除して初期化しますか？ (y/N): ")
        if response.lower() != 'y':
            print("キャンセルしました")
            return
        # 実際の削除は手動で（データベースリセット）
        print("\n注意: データベースファイル shift.db を削除してから再実行してください")
        return
    
    print("\n📝 サンプル職員を登録中...")
    
    # サンプル職員データ
    employees = [
        {"name": "田中 太郎", "skill_score": 90, "email": "tanaka@example.com"},
        {"name": "佐藤 花子", "skill_score": 85, "email": "sato@example.com"},
        {"name": "鈴木 一郎", "skill_score": 75, "email": "suzuki@example.com"},
        {"name": "高橋 次郎", "skill_score": 70, "email": "takahashi@example.com"},
        {"name": "伊藤 三郎", "skill_score": 80, "email": "ito@example.com"},
    ]
    
    employee_ids = []
    for emp in employees:
        emp_id = create_employee(emp["name"], emp["skill_score"], emp["email"])
        if emp_id:
            employee_ids.append(emp_id)
            print(f"  ✅ {emp['name']} (スキル: {emp['skill_score']})")
        else:
            print(f"  ❌ {emp['name']} の登録に失敗")
    
    print(f"\n✅ {len(employee_ids)} 名の職員を登録しました")
    
    print("\n⏰ サンプル時間帯を登録中...")
    
    # サンプル時間帯データ
    time_slots = [
        {"name": "早番", "start_time": "08:00", "end_time": "16:00", "required_staff": 2},
        {"name": "日勤", "start_time": "09:00", "end_time": "17:00", "required_staff": 3},
        {"name": "遅番", "start_time": "12:00", "end_time": "20:00", "required_staff": 2},
        {"name": "夜勤", "start_time": "20:00", "end_time": "08:00", "required_staff": 1},
    ]
    
    time_slot_ids = []
    for ts in time_slots:
        ts_id = create_time_slot(
            ts["name"],
            ts["start_time"],
            ts["end_time"],
            ts["required_staff"]
        )
        if ts_id:
            time_slot_ids.append(ts_id)
            print(f"  ✅ {ts['name']} ({ts['start_time']}-{ts['end_time']}, 必要人数: {ts['required_staff']})")
        else:
            print(f"  ❌ {ts['name']} の登録に失敗")
    
    print(f"\n✅ {len(time_slot_ids)} 個の時間帯を登録しました")
    
    # 勤務可能情報の自動設定（今月と来月）
    print("\n📅 勤務可能情報を自動設定中...")
    
    today = datetime.now()
    
    # 今月と来月の全日を設定
    for month_offset in [0, 1]:
        if month_offset == 0:
            start_date = today.replace(day=1)
        else:
            # 来月の1日
            if today.month == 12:
                start_date = today.replace(year=today.year + 1, month=1, day=1)
            else:
                start_date = today.replace(month=today.month + 1, day=1)
        
        # 月末まで
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
        
        current_date = start_date
        availability_count = 0
        
        while current_date <= end_date:
            for emp_id in employee_ids:
                # 80%の確率で勤務可能に設定（ランダム性を持たせる）
                import random
                if random.random() < 0.8:
                    set_availability(emp_id, current_date.strftime("%Y-%m-%d"), True)
                    availability_count += 1
            
            current_date += timedelta(days=1)
        
        print(f"  ✅ {start_date.strftime('%Y年%m月')}: {availability_count} 件設定")
    
    print("\n" + "=" * 60)
    print("✨ サンプルデータの初期化が完了しました！")
    print("=" * 60)
    print("\n次のステップ:")
    print("  1. アプリケーションを起動: streamlit run main.py")
    print("  2. 職員管理でデータを確認")
    print("  3. シフト生成で最適化を実行")
    print()

if __name__ == "__main__":
    init_sample_data()
