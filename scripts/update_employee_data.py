"""
職員情報を更新するスクリプト

このスクリプトは実際の職員データをCSVファイルから読み込んで更新します。
実名は data/employees.csv ファイルに記載し、このスクリプトにはハードコードしません。

CSVファイル形式（data/employees.csv）:
name,employment_type,can_reha,can_reception,special_info
末廣,正職員,0,1,
森,正職員,1,1,
新倉,パート,0,1,火曜日のみ16時45分までの時短勤務
井澤,時短,0,1,
松本,パート,1,0,

注意: data/employees.csv は .gitignore で除外されており、Gitリポジトリにコミットされません。
"""
import sys
import csv
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from shift_scheduler.database import (
    get_connection,
    list_employees,
    delete_employee,
    create_employee,
)


def update_employee_types_in_schema():
    """データベースのemployee_typeのCHECK制約を更新"""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # 既存のテーブル構造を確認
        cur.execute("PRAGMA table_info(employees)")
        columns = cur.fetchall()
        print("現在のテーブル構造:")
        for col in columns:
            print(f"  {col['name']}: {col['type']}")
        
        # 一時テーブルを作成して既存データを移行
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                employee_type TEXT NOT NULL CHECK(employee_type IN ('TYPE_A', 'TYPE_B', 'TYPE_C', 'TYPE_D', 'TYPE_E', 'TYPE_F')),
                employment_type TEXT NOT NULL CHECK(employment_type IN ('正職員', 'パート', '時短')),
                employment_pattern_id TEXT REFERENCES employment_patterns(id),
                skill_reha INTEGER DEFAULT 50 CHECK(skill_reha BETWEEN 0 AND 100),
                skill_reception_am INTEGER DEFAULT 50 CHECK(skill_reception_am BETWEEN 0 AND 100),
                skill_reception_pm INTEGER DEFAULT 50 CHECK(skill_reception_pm BETWEEN 0 AND 100),
                skill_general INTEGER DEFAULT 50 CHECK(skill_general BETWEEN 0 AND 100),
                is_active BOOLEAN DEFAULT 1,
                is_pattern_fixed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 既存データをコピー
        cur.execute("""
            INSERT INTO employees_new 
            SELECT * FROM employees
        """)
        
        # 古いテーブルを削除
        cur.execute("DROP TABLE employees")
        
        # 新しいテーブルをリネーム
        cur.execute("ALTER TABLE employees_new RENAME TO employees")
        
        conn.commit()
        print("✓ データベーススキーマを更新しました（TYPE_E, TYPE_F, 時短を追加）")


def determine_employee_type(name: str, info: dict) -> str:
    """職員タイプを決定"""
    is_reha = info.get('can_reha', False)
    is_reception = info.get('can_reception', False)
    employment = info.get('employment_type', '正職員')
    
    if is_reha and is_reception and employment == '正職員':
        return 'TYPE_A'
    elif not is_reha and is_reception and employment == '正職員':
        return 'TYPE_B'
    elif is_reha and not is_reception and employment == '正職員':
        return 'TYPE_C'
    elif is_reha and not is_reception and employment == 'パート':
        return 'TYPE_D'
    elif not is_reha and is_reception and employment == 'パート':
        return 'TYPE_E'
    elif not is_reha and is_reception and employment == '時短':
        return 'TYPE_F'
    else:
        return 'TYPE_B'  # デフォルト


def get_employment_pattern_id(name: str, employment_type: str, special_info: str = None) -> str:
    """勤務パターンIDを決定"""
    if employment_type == '正職員':
        return 'full_time_default'
    elif employment_type == '時短':
        return 'short_time_default'
    elif employment_type == 'パート':
        if special_info and '火曜' in special_info:
            # 新倉さんの特殊ケース - 火曜日のみ16:45まで
            return 'part_time_tue_special'
        return 'part_time_default'
    return 'full_time_default'


def load_employees_from_csv(csv_path: Path):
    """CSVファイルから職員データを読み込む"""
    if not csv_path.exists():
        print(f"エラー: CSVファイルが見つかりません: {csv_path}")
        print(f"テンプレートファイル (data/employees_template.csv) をコピーして作成してください。")
        return []
    
    employees = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            employees.append({
                'name': row['name'],
                'employment_type': row['employment_type'],
                'can_reha': row['can_reha'] == '1',
                'can_reception': row['can_reception'] == '1',
                'special_info': row['special_info'] if row['special_info'] else None
            })
    
    return employees


def create_new_employees():
    """新しい職員データを作成"""
    
    # CSVファイルから職員情報を読み込む
    csv_path = Path(__file__).parent.parent / "data" / "employees.csv"
    new_employees = load_employees_from_csv(csv_path)
    
    if not new_employees:
        print("職員データが見つかりません。処理を中止します。")
        return
    
    print("\n新しい職員データを作成します...")
    print("-" * 60)
    
    for emp_info in new_employees:
        name = emp_info['name']
        employment_type = emp_info['employment_type']
        employee_type = determine_employee_type(name, emp_info)
        pattern_id = get_employment_pattern_id(
            name, 
            employment_type, 
            emp_info.get('special_info')
        )
        
        # スキル値の設定
        skill_reha = 70 if emp_info['can_reha'] else 0
        skill_reception_am = 70 if emp_info['can_reception'] else 0
        skill_reception_pm = 70 if emp_info['can_reception'] else 0
        skill_general = 70 if emp_info['can_reception'] else 0
        
        try:
            employee_id = create_employee(
                name=name,
                employee_type=employee_type,
                employment_type=employment_type,
                employment_pattern_id=pattern_id,
                skill_reha=skill_reha,
                skill_reception_am=skill_reception_am,
                skill_reception_pm=skill_reception_pm,
                skill_general=skill_general,
                is_pattern_fixed=False
            )
            
            special_note = f" ({emp_info['special_info']})" if emp_info.get('special_info') else ""
            print(f"✓ {name}: {employee_type} | {employment_type} | "
                  f"リハ:{skill_reha} 受付AM:{skill_reception_am} 受付PM:{skill_reception_pm}{special_note}")
            
        except Exception as e:
            print(f"✗ {name} の作成に失敗: {e}")
    
    print("-" * 60)


def clear_existing_employees():
    """既存の職員データをクリア"""
    employees = list_employees()
    print(f"\n既存の職員データ（{len(employees)}名）をクリアします...")
    
    for emp in employees:
        try:
            delete_employee(emp.id)
            print(f"  削除: {emp.name} ({emp.employee_type})")
        except Exception as e:
            print(f"  削除失敗: {emp.name} - {e}")


def display_current_employees():
    """現在の職員データを表示"""
    employees = list_employees()
    print(f"\n現在の職員データ（{len(employees)}名）:")
    print("-" * 80)
    print(f"{'名前':<10} {'タイプ':<10} {'雇用形態':<10} {'リハ':<6} {'受付AM':<8} {'受付PM':<8} {'総合':<6}")
    print("-" * 80)
    
    for emp in employees:
        print(f"{emp.name:<10} {emp.employee_type:<10} {emp.employment_type:<10} "
              f"{emp.skill_reha:<6} {emp.skill_reception_am:<8} "
              f"{emp.skill_reception_pm:<8} {emp.skill_general:<6}")
    
    print("-" * 80)


def main():
    """メイン処理"""
    print("=" * 80)
    print("職員データ更新スクリプト")
    print("=" * 80)
    
    # 1. 現在のデータを表示
    display_current_employees()
    
    # 2. スキーマを更新
    print("\n[ステップ1] データベーススキーマを更新します...")
    update_employee_types_in_schema()
    
    # 3. 既存データをクリア
    print("\n[ステップ2] 既存の職員データをクリアします...")
    clear_existing_employees()
    
    # 4. 新しいデータを作成
    print("\n[ステップ3] 新しい職員データを作成します...")
    create_new_employees()
    
    # 5. 更新後のデータを表示
    print("\n[完了] 更新後の職員データ:")
    display_current_employees()
    
    print("\n✓ すべての処理が完了しました")
    print("=" * 80)


if __name__ == "__main__":
    main()
