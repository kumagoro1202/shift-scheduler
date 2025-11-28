"""
サンプルデータ投入スクリプト
V3.0仕様に準拠したテストデータを登録します
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import (
    init_database,
    create_employee,
    add_absence,
    get_all_employees
)


def init_sample_data():
    """サンプルデータを投入"""
    
    print("=" * 60)
    print("シフト管理システム - サンプルデータ投入")
    print("=" * 60)
    
    # データベース初期化
    print("\n📦 データベースを初期化中...")
    init_database()
    print("  ✅ データベーステーブルを作成しました")
    
    # 既存データチェック
    existing_employees = get_all_employees()
    if existing_employees:
        print(f"\n⚠️  既に {len(existing_employees)} 名の職員が登録されています")
        response = input("既存データを上書きしますか？ (y/N): ")
        if response.lower() != 'y':
            print("キャンセルしました")
            return
    
    print("\n👥 職員データ投入中...")
    
    # 職員データ（V3.0仕様）
    employees_data = [
        {
            'name': '山田太郎',
            'employee_type': 'TYPE_A',
            'employment_type': '正職員',
            'employment_pattern_id': 'full_early',
            'skill_reha': 85,
            'skill_reception_am': 90,
            'skill_reception_pm': 85,
            'skill_general': 90
        },
        {
            'name': '佐藤花子',
            'employee_type': 'TYPE_A',
            'employment_type': '正職員',
            'employment_pattern_id': 'full_mid',
            'skill_reha': 80,
            'skill_reception_am': 85,
            'skill_reception_pm': 90,
            'skill_general': 85
        },
        {
            'name': '鈴木一郎',
            'employee_type': 'TYPE_B',
            'employment_type': '正職員',
            'employment_pattern_id': 'full_late',
            'skill_reha': 0,
            'skill_reception_am': 95,
            'skill_reception_pm': 95,
            'skill_general': 80
        },
        {
            'name': '田中美咲',
            'employee_type': 'TYPE_C',
            'employment_type': '正職員',
            'employment_pattern_id': 'short_time',
            'skill_reha': 90,
            'skill_reception_am': 0,
            'skill_reception_pm': 0,
            'skill_general': 75
        },
        {
            'name': '高橋健太',
            'employee_type': 'TYPE_D',
            'employment_type': 'パート',
            'employment_pattern_id': 'part_morning',
            'skill_reha': 70,
            'skill_reception_am': 0,
            'skill_reception_pm': 0,
            'skill_general': 60
        },
        {
            'name': '伊藤さくら',
            'employee_type': 'TYPE_D',
            'employment_type': 'パート',
            'employment_pattern_id': 'part_morning_ext',
            'skill_reha': 75,
            'skill_reception_am': 0,
            'skill_reception_pm': 0,
            'skill_general': 65
        },
    ]
    
    employee_ids = []
    for emp_data in employees_data:
        emp_id = create_employee(**emp_data)
        employee_ids.append(emp_id)
        print(f"  ✓ {emp_data['name']} を登録しました（ID: {emp_id}）")
    
    print("\n🏖️ 休暇データ投入中...")
    
    # サンプル休暇データ（2025年12月）
    base_date = datetime(2025, 12, 1)
    absences = [
        # 山田太郎の休暇
        (employee_ids[0], base_date + timedelta(days=4), 'full_day', '年次有給休暇'),
        (employee_ids[0], base_date + timedelta(days=18), 'afternoon', '半休'),
        
        # 佐藤花子の休暇
        (employee_ids[1], base_date + timedelta(days=11), 'morning', '通院'),
        (employee_ids[1], base_date + timedelta(days=25), 'full_day', '年次有給休暇'),
        
        # 鈴木一郎の休暇
        (employee_ids[2], base_date + timedelta(days=19), 'full_day', '年次有給休暇'),
        
        # 田中美咲の休暇
        (employee_ids[3], base_date + timedelta(days=10), 'full_day', '子の看護休暇'),
        (employee_ids[3], base_date + timedelta(days=24), 'full_day', '年次有給休暇'),
        
        # 高橋健太の休暇
        (employee_ids[4], base_date + timedelta(days=15), 'morning', '私用'),
        
        # 伊藤さくらの休暇
        (employee_ids[5], base_date + timedelta(days=20), 'morning', '私用'),
    ]
    
    for idx, (emp_id, date_obj, absence_type, reason) in enumerate(absences):
        add_absence(emp_id, date_obj.strftime("%Y-%m-%d"), absence_type, reason)
        emp_name = employees_data[employee_ids.index(emp_id)]['name']
        type_jp = {'full_day': '終日休暇', 'morning': '午前休', 'afternoon': '午後休'}[absence_type]
        print(f"  ✓ {emp_name} の {type_jp} ({date_obj.strftime('%m/%d')}) を登録しました")
    
    print("\n" + "=" * 60)
    print("✅ サンプルデータの投入が完了しました")
    print("=" * 60)
    print()
    print("次のステップ:")
    print("  1. アプリケーションを起動: streamlit run main.py")
    print("  2. 職員管理ページで職員を確認")
    print("  3. 休暇管理ページで休暇を確認")
    print("  4. シフト生成ページでシフトを生成")
    print()


if __name__ == "__main__":
    init_sample_data()
