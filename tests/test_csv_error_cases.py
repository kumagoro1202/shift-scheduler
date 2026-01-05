"""CSV取り込み - エラーケースのテスト"""
import sys
from pathlib import Path
import csv
import io

sys.path.append(str(Path(__file__).parent.parent / "src"))

from shift_scheduler import init_database

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
                print(f"スキップ: 名前が空")
                continue
                
            if employee_data['employee_type'] not in ['TYPE_A', 'TYPE_B', 'TYPE_C', 'TYPE_D', 'TYPE_E', 'TYPE_F']:
                print(f"スキップ: 無効な職員タイプ: {employee_data['employee_type']}")
                continue
                
            if employee_data['employment_type'] not in ['正職員', 'パート']:
                print(f"スキップ: 無効な雇用形態: {employee_data['employment_type']}")
                continue
            
            employees.append(employee_data)
        except (KeyError, ValueError) as e:
            print(f"スキップ: データ解析エラー: {e}")
            continue
    
    return employees

if __name__ == "__main__":
    init_database()
    
    print("=== エラーケースのテスト ===\n")
    
    # ケース1: 無効な職員タイプ
    print("【ケース1】無効な職員タイプ")
    test_csv1 = """名前,職員タイプ,雇用形態,勤務パターンID,パターン固定,リハ室スキル,受付午前スキル,受付午後スキル,総合対応力
テスト太郎,TYPE_X,正職員,full_early,False,80,75,75,70"""
    result1 = parse_csv_employees(test_csv1)
    print(f"結果: {len(result1)}名パース成功\n")
    
    # ケース2: 無効な雇用形態
    print("【ケース2】無効な雇用形態")
    test_csv2 = """名前,職員タイプ,雇用形態,勤務パターンID,パターン固定,リハ室スキル,受付午前スキル,受付午後スキル,総合対応力
テスト花子,TYPE_A,契約社員,full_early,False,80,75,75,70"""
    result2 = parse_csv_employees(test_csv2)
    print(f"結果: {len(result2)}名パース成功\n")
    
    # ケース3: 数値以外のスキル値
    print("【ケース3】数値以外のスキル値")
    test_csv3 = """名前,職員タイプ,雇用形態,勤務パターンID,パターン固定,リハ室スキル,受付午前スキル,受付午後スキル,総合対応力
テスト三郎,TYPE_A,正職員,full_early,False,abc,75,75,70"""
    result3 = parse_csv_employees(test_csv3)
    print(f"結果: {len(result3)}名パース成功\n")
    
    # ケース4: 名前が空
    print("【ケース4】名前が空")
    test_csv4 = """名前,職員タイプ,雇用形態,勤務パターンID,パターン固定,リハ室スキル,受付午前スキル,受付午後スキル,総合対応力
,TYPE_A,正職員,full_early,False,80,75,75,70"""
    result4 = parse_csv_employees(test_csv4)
    print(f"結果: {len(result4)}名パース成功\n")
    
    # ケース5: 混在データ（正常と異常）
    print("【ケース5】混在データ（正常2名 + 異常2名）")
    test_csv5 = """名前,職員タイプ,雇用形態,勤務パターンID,パターン固定,リハ室スキル,受付午前スキル,受付午後スキル,総合対応力
テスト正常1,TYPE_A,正職員,full_early,False,80,75,75,70
テスト異常1,TYPE_X,正職員,full_early,False,80,75,75,70
テスト正常2,TYPE_B,パート,part_morning,True,0,85,85,60
テスト異常2,TYPE_A,契約社員,full_early,False,80,75,75,70"""
    result5 = parse_csv_employees(test_csv5)
    print(f"結果: {len(result5)}名パース成功")
    for emp in result5:
        print(f"  - {emp['name']}")
    
    print("\n✅ エラーケーステスト完了")
