"""CSV出力・取り込み機能のテスト"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from shift_scheduler import init_database, list_employees
import csv
import io

def export_employees_to_csv(employees):
    """職員データをCSV形式で出力"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # ヘッダー行
    writer.writerow([
        '名前', '職員タイプ', '雇用形態', '勤務パターンID',
        'パターン固定', 'リハ室スキル', '受付午前スキル',
        '受付午後スキル', '総合対応力'
    ])
    
    # データ行
    for emp in employees:
        writer.writerow([
            emp.name,
            emp.employee_type,
            emp.employment_type,
            emp.employment_pattern_id or '',
            'True' if getattr(emp, 'is_pattern_fixed', False) else 'False',
            emp.skill_reha,
            emp.skill_reception_am,
            emp.skill_reception_pm,
            emp.skill_general
        ])
    
    return output.getvalue()

if __name__ == "__main__":
    init_database()
    
    employees = list_employees()
    print(f"職員数: {len(employees)}名")
    
    if employees:
        csv_data = export_employees_to_csv(employees)
        
        # CSVファイルに保存
        output_file = Path(__file__).parent / "employees_export.csv"
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            f.write(csv_data)
        
        print(f"\nCSVファイルを出力しました: {output_file}")
        print("\n--- CSV内容（先頭5行） ---")
        lines = csv_data.split('\n')
        for line in lines[:6]:
            if line:
                print(line)
    else:
        print("職員データが見つかりません")
