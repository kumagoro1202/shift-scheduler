"""
シフト作成システム - データベースマイグレーション (V1.0 → V2.0)
"""
import sqlite3
from pathlib import Path
from typing import Optional

try:
    from .database import get_connection, DB_PATH
except ImportError:
    from database import get_connection, DB_PATH


def check_migration_needed() -> bool:
    """マイグレーションが必要かチェック"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # employee_typeカラムの存在確認
    cursor.execute("PRAGMA table_info(employees)")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    
    return 'employee_type' not in columns


def migrate_to_v2() -> bool:
    """
    V1.0 → V2.0 へのデータベースマイグレーション
    
    Returns:
        bool: マイグレーション成功時True
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # バックアップ作成
        backup_path = DB_PATH.parent / f"shift_backup_{Path(DB_PATH).stem}_v1.db"
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✓ バックアップ作成: {backup_path}")
        
        # ========== employeesテーブル拡張 ==========
        print("職員テーブルを拡張中...")
        
        # 職員タイプ
        cursor.execute("""
            ALTER TABLE employees ADD COLUMN employee_type TEXT DEFAULT 'TYPE_A' 
            CHECK(employee_type IN ('TYPE_A', 'TYPE_B', 'TYPE_C', 'TYPE_D'))
        """)
        
        # 雇用形態
        cursor.execute("""
            ALTER TABLE employees ADD COLUMN employment_type TEXT DEFAULT '正職員' 
            CHECK(employment_type IN ('正職員', 'パート'))
        """)
        
        # 勤務形態
        cursor.execute("""
            ALTER TABLE employees ADD COLUMN work_type TEXT DEFAULT 'フルタイム' 
            CHECK(work_type IN ('フルタイム', '時短勤務', 'パートタイム'))
        """)
        
        # 勤務パターン
        cursor.execute("""
            ALTER TABLE employees ADD COLUMN work_pattern TEXT DEFAULT 'P1'
        """)
        
        # スキルスコア（4項目）
        cursor.execute("""
            ALTER TABLE employees ADD COLUMN skill_reha_room INTEGER DEFAULT 0 
            CHECK(skill_reha_room >= 0 AND skill_reha_room <= 100)
        """)
        
        cursor.execute("""
            ALTER TABLE employees ADD COLUMN skill_reception_am INTEGER DEFAULT 0 
            CHECK(skill_reception_am >= 0 AND skill_reception_am <= 100)
        """)
        
        cursor.execute("""
            ALTER TABLE employees ADD COLUMN skill_reception_pm INTEGER DEFAULT 0 
            CHECK(skill_reception_pm >= 0 AND skill_reception_pm <= 100)
        """)
        
        cursor.execute("""
            ALTER TABLE employees ADD COLUMN skill_flexibility INTEGER DEFAULT 0 
            CHECK(skill_flexibility >= 0 AND skill_flexibility <= 100)
        """)
        
        # 既存データの移行（skill_score → skill_reha_room）
        cursor.execute("""
            UPDATE employees 
            SET skill_reha_room = skill_score,
                skill_reception_am = skill_score,
                skill_reception_pm = skill_score,
                skill_flexibility = skill_score
        """)
        
        print("✓ 職員テーブルの拡張完了")
        
        # ========== time_slotsテーブル拡張 ==========
        print("時間帯テーブルを拡張中...")
        
        cursor.execute("""
            ALTER TABLE time_slots ADD COLUMN area_type TEXT DEFAULT '受付' 
            CHECK(area_type IN ('受付', 'リハ室'))
        """)
        
        cursor.execute("""
            ALTER TABLE time_slots ADD COLUMN time_period TEXT 
            CHECK(time_period IN ('午前', '午後', '終日'))
        """)
        
        cursor.execute("""
            ALTER TABLE time_slots ADD COLUMN required_employees_min INTEGER DEFAULT 1
        """)
        
        cursor.execute("""
            ALTER TABLE time_slots ADD COLUMN required_employees_max INTEGER DEFAULT 2
        """)
        
        cursor.execute("""
            ALTER TABLE time_slots ADD COLUMN target_skill_score INTEGER DEFAULT 150
        """)
        
        cursor.execute("""
            ALTER TABLE time_slots ADD COLUMN skill_weight REAL DEFAULT 1.0
        """)
        
        # 既存データの移行
        cursor.execute("""
            UPDATE time_slots 
            SET required_employees_min = 1,
                required_employees_max = required_employees
        """)
        
        print("✓ 時間帯テーブルの拡張完了")
        
        # ========== work_patternsテーブル作成 ==========
        print("勤務パターンテーブルを作成中...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_patterns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                work_type TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                break_hours REAL NOT NULL,
                break_division INTEGER DEFAULT 1,
                work_hours REAL NOT NULL,
                employment_type TEXT NOT NULL
            )
        """)
        
        # マスタデータ投入
        patterns = [
            ('P1', '基本パターン1', 'フルタイム', '08:30', '18:30', 2.0, 2, 8.0, '正職員'),
            ('P2', '基本パターン2', 'フルタイム', '08:45', '18:45', 2.0, 2, 8.0, '正職員'),
            ('P3', '基本パターン3', 'フルタイム', '09:00', '19:00', 2.0, 2, 8.0, '正職員'),
            ('P4', '時短勤務', '時短勤務', '08:45', '16:45', 1.0, 1, 7.0, '正職員'),
            ('PT1', '午前パート', 'パートタイム', '08:45', '12:45', 0.0, 0, 4.0, 'パート'),
            ('PT2', '午前延長パート', 'パートタイム', '08:45', '13:45', 0.0, 0, 5.0, 'パート'),
        ]
        
        cursor.executemany("""
            INSERT OR IGNORE INTO work_patterns 
            (id, name, work_type, start_time, end_time, break_hours, break_division, work_hours, employment_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, patterns)
        
        print("✓ 勤務パターンテーブルの作成完了")
        
        # ========== break_schedulesテーブル作成 ==========
        print("休憩スケジュールテーブルを作成中...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS break_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                date DATE NOT NULL,
                break_number INTEGER NOT NULL CHECK(break_number IN (1, 2)),
                break_start_time TEXT NOT NULL,
                break_end_time TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shift_id) REFERENCES shifts(id),
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
        """)
        
        print("✓ 休憩スケジュールテーブルの作成完了")
        
        # バージョン情報を設定テーブルに保存
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) 
            VALUES ('db_version', '2.0')
        """)
        
        conn.commit()
        print("\n✓✓✓ マイグレーション完了 ✓✓✓")
        print(f"データベースバージョン: V2.0")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ マイグレーション失敗: {e}")
        print("データベースはロールバックされました")
        return False
        
    finally:
        conn.close()


def get_db_version() -> str:
    """データベースのバージョンを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT value FROM settings WHERE key = 'db_version'")
        row = cursor.fetchone()
        version = row['value'] if row else '1.0'
    except sqlite3.OperationalError:
        # settingsテーブルが存在しない場合
        version = '1.0'
    
    conn.close()
    return version


if __name__ == "__main__":
    print("=" * 60)
    print("シフト管理システム データベースマイグレーション")
    print("V1.0 → V2.0")
    print("=" * 60)
    print()
    
    current_version = get_db_version()
    print(f"現在のバージョン: {current_version}")
    
    if current_version == '2.0':
        print("既にV2.0にマイグレーション済みです")
    elif check_migration_needed():
        print("\nマイグレーションを開始します...")
        print()
        success = migrate_to_v2()
        if success:
            print("\nマイグレーションが正常に完了しました！")
        else:
            print("\nマイグレーションに失敗しました")
    else:
        print("マイグレーションは不要です")
