"""CSV取り込み機能のテスト"""
import sys
from pathlib import Path
import csv
import io

sys.path.append(str(Path(__file__).parent.parent / "src"))

from shift_scheduler import init_database, list_employees, create_employee

def parse_csv_employees(csv_content):
    """CSVコンテンツをパースして職員データのリストを返す"""
    employees = []
    reader = csv.DictReader(io.StringIO(csv_content))
    
    for row in reader:
        try:
            employee_data = {
                'name': row['名前'].strip(),
                'employee_type': row['職員タイプ'].strip(),
                'employment_type': row['雇用形態'].strip(),
                'employment_pattern_id': row['勤務パターンID'].strip() or None,
                'is_pattern_fixed': row['パターン固定'].strip().lower() == 'true',
                'skill_reha': int(row['リハ室スキル']),
                'skill_reception_am': int(row['受付午前スキル']),
                'skill_reception_pm': int(row['受付午後スキル']),
                'skill_general': int(row['総合対応力'])
            }
            
            # バリデーション
            if not employee_data['name']:
                continue
                
            if employee_data['employee_type'] not in ['TYPE_A', 'TYPE_B', 'TYPE_C', 'TYPE_D', 'TYPE_E', 'TYPE_F']:
                print(f"警告: 無効な職員タイプ: {employee_data['employee_type']}")
                continue
                
            if employee_data['employment_type'] not in ['正職員', 'パート']:
                print(f"警告: 無効な雇用形態: {employee_data['employment_type']}")
                continue
            
            employees.append(employee_data)
        except (KeyError, ValueError) as e:
            print(f"警告: データ解析エラー: {e}")
            continue
    
    return employees

if __name__ == "__main__":
    init_database()
    
    # テスト用のCSVファイルを作成
    test_csv_content = """名前,職員タイプ,雇用形態,勤務パターンID,パターン固定,リハ室スキル,受付午前スキル,受付午後スキル,総合対応力
テスト太郎,TYPE_A,正職員,full_early,False,80,75,75,70
テスト花子,TYPE_B,パート,part_morning,True,0,85,85,60
テスト三郎,TYPE_C,正職員,full_late,False,90,0,0,80"""
    
    print("=== CSV取り込みテスト ===\n")
    
    # パース
    parsed_employees = parse_csv_employees(test_csv_content)
    print(f"パース結果: {len(parsed_employees)}名\n")
    
    for emp_data in parsed_employees:
        print(f"名前: {emp_data['name']}")
        print(f"  職員タイプ: {emp_data['employee_type']}")
        print(f"  雇用形態: {emp_data['employment_type']}")
        print(f"  勤務パターンID: {emp_data['employment_pattern_id']}")
        print(f"  パターン固定: {emp_data['is_pattern_fixed']}")
        print(f"  スキル: リハ={emp_data['skill_reha']}, 受付AM={emp_data['skill_reception_am']}, 受付PM={emp_data['skill_reception_pm']}, 総合={emp_data['skill_general']}")
        print()
    
    print("\n=== 実データでのテスト ===")
    csv_file = Path(__file__).parent / "employees_export.csv"
    if csv_file.exists():
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        parsed = parse_csv_employees(csv_content)
        print(f"既存CSVから {len(parsed)}名のデータをパースしました")
        
        # 最初の3名を表示
        print("\n先頭3名:")
        for emp_data in parsed[:3]:
            print(f"  - {emp_data['name']} ({emp_data['employee_type']}, {emp_data['employment_type']})")
    
    print("\n✅ テスト完了")
