"""実際のシフト表CSVからテストデータを生成するスクリプト

このスクリプトはreport/20251221-20160120.csvを解析し、
職員情報、休暇情報、シフト情報をデータベースに投入します。

注意: このスクリプトは配布用のテストデータ作成専用です。
CSVファイル自体はGit管理対象外(.gitignore設定済み)です。
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from shift_scheduler import (
    DB_PATH,
    create_employee,
    init_database,
    list_employees,
    record_absence,
    reset_employment_patterns,
    reset_time_slots,
    set_setting,
    create_shift,
)

CSV_SOURCE = REPO_ROOT / "report" / "20251221-20160120.csv"
DIST_DB_PATH = REPO_ROOT / "data" / "shift.db"
TEMPLATE_VERSION = "2026-01-05-realshift"

# 就業パターンID推定マップ（シフト記号 → employment_pattern_id）
PATTERN_MAP = {
    "Ｂ": "full_early",      # 早番パターン
    "Ｃ": "full_late",       # 遅番パターン
    "月火": "part_mon_tue",   # 月火パート
    "月・": "part_mon_other", # 月その他
    "PA": "part_time_a",     # パートタイムA
    "P2": "part_time_2",     # パートタイム2
    "P3": "part_time_3",     # パートタイム3
}

# 雇用形態の推定
EMPLOYMENT_TYPE_MAP = {
    "PA": "パート",
    "P2": "パート",
    "P3": "パート",
    "月火": "パート",
    "月・": "パート",
}

# 職員タイプの推定（デフォルトはTYPE_A）
EMPLOYEE_TYPE_DEFAULT = "TYPE_A"


def parse_period_header(csv_path: Path) -> tuple[date, date]:
    """CSVヘッダーから期間を解析する"""
    with open(csv_path, encoding="utf-8") as f:
        first_line = f.readline().strip()
    
    match = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})\s*～\s*(\d{4})/(\d{1,2})/(\d{1,2})", first_line)
    if not match:
        raise ValueError(f"期間情報が見つかりません: {first_line}")
    
    start_date = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    end_date = date(int(match.group(4)), int(match.group(5)), int(match.group(6)))
    
    return start_date, end_date


def generate_date_list(start: date, end: date) -> list[date]:
    """期間内の日付リストを生成"""
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def parse_shift_symbol(symbol: str) -> dict[str, str | None]:
    """シフト記号を解析して情報を抽出"""
    symbol = symbol.strip()
    
    # 空白またはダミー行
    if not symbol or symbol in ["副", ""]:
        return {"type": "none"}
    
    # 休暇系
    if "有休" in symbol or "休み" in symbol:
        return {"type": "absence", "absence_type": "full_day", "reason": "有給休暇"}
    if "予" in symbol:
        return {"type": "absence", "absence_type": "full_day", "reason": "予定休"}
    
    # 記号の解析
    # 例: Ｂ, Ｃ, 月火, PA, P2, P3, △, 〇, １, ２, ３など
    
    # 主要パターンの判定
    for pattern_key in PATTERN_MAP:
        if pattern_key in symbol:
            return {
                "type": "shift",
                "pattern": pattern_key,
                "original": symbol
            }
    
    # その他の記号（△, 〇, １-３は時短や半休の可能性）
    # 簡易的にnoneとして扱う（必要に応じて拡張）
    return {"type": "other", "original": symbol}


def estimate_employment_pattern(shift_data: list[dict]) -> str:
    """職員のシフトデータから主な就業パターンを推定"""
    pattern_count = {}
    
    for item in shift_data:
        if item.get("type") == "shift" and "pattern" in item:
            pattern = item["pattern"]
            pattern_count[pattern] = pattern_count.get(pattern, 0) + 1
    
    if not pattern_count:
        return "full_early"  # デフォルト
    
    # 最も多く出現するパターンを採用
    most_common = max(pattern_count.items(), key=lambda x: x[1])
    return PATTERN_MAP.get(most_common[0], "full_early")


def estimate_skills(name: str, pattern: str) -> dict[str, int]:
    """職員名とパターンからスキルを推定"""
    # デフォルトスキル
    skills = {
        "skill_reha": 80,
        "skill_reception_am": 80,
        "skill_reception_pm": 80,
        "skill_general": 80,
    }
    
    # パターンごとの調整（リハビリ専門、受付専門など）
    if pattern in ["part_mon_tue", "part_mon_other"]:
        # リハビリ系パートと仮定
        skills["skill_reha"] = 85
        skills["skill_reception_am"] = 0
        skills["skill_reception_pm"] = 0
    elif pattern in ["part_time_a", "part_time_2", "part_time_3"]:
        # 受付系パートと仮定
        skills["skill_reha"] = 0
        skills["skill_reception_am"] = 85
        skills["skill_reception_pm"] = 70
    
    return skills


def load_shift_csv(csv_path: Path) -> dict:
    """CSVファイルを読み込み、職員・シフト・休暇情報を抽出"""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
    
    start_date, end_date = parse_period_header(csv_path)
    date_list = generate_date_list(start_date, end_date)
    
    employees_data = []
    shifts_data = []
    absences_data = []
    
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        
        # ヘッダー行をスキップ
        next(reader)  # 期間行
        date_row = next(reader)  # 日付行（21, 22, 23...）
        weekday_row = next(reader)  # 曜日行（日, 月, 火...）
        
        # 各職員の行を処理
        for row in reader:
            if len(row) < 3:
                continue
            
            row_num = row[0].strip()
            name = row[1].strip()
            
            # 無効な行をスキップ
            if not name or not row_num.isdigit():
                continue
            
            # シフトデータ部分（3列目以降）
            shift_cells = row[2:]
            
            # シフトセルを解析
            shift_records = []
            for idx, cell in enumerate(shift_cells):
                if idx >= len(date_list):
                    break
                parsed = parse_shift_symbol(cell)
                parsed["date"] = date_list[idx]
                shift_records.append(parsed)
            
            # 就業パターンの推定
            employment_pattern = estimate_employment_pattern(shift_records)
            employment_type = EMPLOYMENT_TYPE_MAP.get(
                next((r["pattern"] for r in shift_records if r.get("pattern")), ""),
                "正職員"
            )
            
            # スキルの推定
            skills = estimate_skills(name, employment_pattern)
            
            # 職員データ
            employee_data = {
                "name": name,
                "employee_type": EMPLOYEE_TYPE_DEFAULT,
                "employment_type": employment_type,
                "employment_pattern_id": employment_pattern,
                "is_pattern_fixed": employment_type == "パート",
                **skills
            }
            employees_data.append(employee_data)
            
            # 休暇とシフトの抽出
            employee_index = len(employees_data) - 1
            for record in shift_records:
                if record["type"] == "absence":
                    absences_data.append({
                        "employee_index": employee_index,
                        "date": record["date"],
                        "absence_type": record.get("absence_type", "full_day"),
                        "reason": record.get("reason", "休暇")
                    })
                elif record["type"] == "shift":
                    shifts_data.append({
                        "employee_index": employee_index,
                        "date": record["date"],
                        "pattern": record["pattern"],
                        "original": record.get("original", "")
                    })
    
    return {
        "employees": employees_data,
        "shifts": shifts_data,
        "absences": absences_data,
        "start_date": start_date,
        "end_date": end_date
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="実際のシフト表CSVからテストデータを生成"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="既存のデータを削除してから投入",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=CSV_SOURCE,
        help=f"CSVファイルのパス（デフォルト: {CSV_SOURCE}）",
    )
    return parser.parse_args(argv)


def clear_existing_data() -> None:
    """既存のデータを削除"""
    employees = list_employees(active_only=False)
    removed = len(employees)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM break_schedules")
        conn.execute("DELETE FROM shifts")
        conn.execute("DELETE FROM employee_absences")
        conn.execute("DELETE FROM employees")
        conn.commit()

    if removed:
        print(f"既存の職員データを削除しました: {removed}件")


def reset_sequences() -> None:
    """自動インクリメントカウンタをリセット"""
    with sqlite3.connect(DB_PATH) as conn:
        for table in ("employees", "employee_absences", "shifts", "break_schedules"):
            conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        conn.commit()


def seed_test_data(csv_path: Path, force: bool) -> bool:
    """テストデータの投入"""
    # データベース初期化
    init_database()
    reset_employment_patterns()
    reset_time_slots()
    
    # 既存データの確認
    employees = list_employees(active_only=False)
    if employees and not force:
        response = input(
            f"既存の職員データ({len(employees)}件)が存在します。上書きしますか？ (y/N): "
        )
        if response.lower() != "y":
            print("キャンセルしました")
            return False
    
    if employees:
        clear_existing_data()
        reset_sequences()
    else:
        reset_sequences()
    
    # CSVデータの読み込み
    print(f"CSVファイルを読み込んでいます: {csv_path}")
    data = load_shift_csv(csv_path)
    
    print(f"期間: {data['start_date']} ～ {data['end_date']}")
    print(f"職員数: {len(data['employees'])}")
    print(f"シフト記録数: {len(data['shifts'])}")
    print(f"休暇記録数: {len(data['absences'])}")
    
    # 職員データの投入
    print("\n職員データを登録しています...")
    inserted_ids = []
    for emp in data["employees"]:
        emp_id = create_employee(**emp)
        inserted_ids.append(emp_id)
        print(f"  {emp['name']} (ID={emp_id}, パターン={emp['employment_pattern_id']})")
    
    # 休暇データの投入
    print("\n休暇データを登録しています...")
    for absence in data["absences"]:
        emp_id = inserted_ids[absence["employee_index"]]
        record_absence(
            employee_id=emp_id,
            date=absence["date"].isoformat(),
            absence_type=absence["absence_type"],
            reason=absence["reason"]
        )
        emp_name = data["employees"][absence["employee_index"]]["name"]
        print(f"  {emp_name}: {absence['date']} ({absence['reason']})")
    
    # シフトデータの投入（オプション：既存のtime_slotにマッピングできる場合）
    # 現時点では簡易版なので、シフトは生成画面で作成する想定
    print("\nシフトデータはシフト生成画面で作成してください")
    
    # テンプレートバージョンの記録
    set_setting("template_version", TEMPLATE_VERSION)
    print(f"\nテンプレートバージョンを記録しました: {TEMPLATE_VERSION}")
    
    print("\n✓ テストデータの投入が完了しました")
    return True


def copy_seeded_database() -> Path:
    """シードされたデータベースを配布用フォルダにコピー"""
    DIST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, DIST_DB_PATH)
    return DIST_DB_PATH


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    
    print("=" * 70)
    print("シフトスケジューラー - 実データベースのテストデータ生成")
    print("=" * 70)
    print()
    
    if not args.csv.exists():
        print(f"エラー: CSVファイルが見つかりません: {args.csv}")
        print("report/20251221-20160120.csv が配置されているか確認してください")
        sys.exit(1)
    
    seeded = seed_test_data(args.csv, force=args.force)
    
    if seeded:
        copied_path = copy_seeded_database()
        print(f"\n配布用データベースにコピーしました: {copied_path}")
        print("このデータベースがビルド時にパッケージに含まれます")
    
    print("=" * 70)
    print("完了しました。アプリを起動するには: streamlit run main.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
