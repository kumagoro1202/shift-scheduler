"""
V2.0 → V3.0 マイグレーション
"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from database import get_connection, DB_PATH


def check_v3_migration_needed() -> bool:
    """V3マイグレーションが必要かチェック"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # employment_patternsテーブルの存在確認
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='employment_patterns'
        """)
        return cursor.fetchone() is None
    finally:
        conn.close()


def migrate_to_v3():
    """V2.0からV3.0へマイグレーション"""
    print("🔄 V3.0へのマイグレーションを開始します...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Phase 1: 新テーブル作成
        print("📦 Phase 1: 新テーブルを作成中...")
        from database import (
            init_employment_patterns_table,
            init_employee_absences_table,
            init_fixed_time_slots,
            add_employment_pattern_to_employees
        )
        
        init_employment_patterns_table()
        init_employee_absences_table()
        add_employment_pattern_to_employees()
        
        # Phase 2: work_pattern → employment_pattern_id マッピング
        print("🔄 Phase 2: 勤務形態データを移行中...")
        pattern_mapping = {
            'P1': 'full_early',
            'P2': 'full_mid',
            'P3': 'full_late',
            'P4': 'short_time',
            'PT1': 'part_morning',
            'PT2': 'part_morning_ext',
        }
        
        for old_pattern, new_pattern in pattern_mapping.items():
            cursor.execute("""
                UPDATE employees 
                SET employment_pattern_id = ? 
                WHERE work_pattern = ?
            """, (new_pattern, old_pattern))
        
        # デフォルト値設定（work_patternが未設定の場合）
        cursor.execute("""
            UPDATE employees 
            SET employment_pattern_id = 'full_early' 
            WHERE employment_pattern_id IS NULL
        """)
        
        conn.commit()
        
        # Phase 3: availability → employee_absences 変換
        print("🔄 Phase 3: 勤務可否データを休暇データに変換中...")
        
        # availabilityテーブルが存在する場合のみ処理
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='availability'
        """)
        
        if cursor.fetchone():
            migrate_availability_to_absences(cursor)
            conn.commit()
        
        # Phase 4: 時間帯マスタの固定化
        print("🔄 Phase 4: 時間帯マスタを固定化中...")
        init_fixed_time_slots()
        
        # Phase 5: 設定バージョンの更新
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) 
            VALUES ('schema_version', '3.0')
        """)
        
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) 
            VALUES ('migration_date_v3', ?)
        """, (datetime.now().isoformat(),))
        
        conn.commit()
        print("✅ V3.0へのマイグレーションが完了しました")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ マイグレーション中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()


def migrate_availability_to_absences(cursor):
    """availability → employee_absences データ変換"""
    
    # 日付ごとにグループ化して処理
    cursor.execute("""
        SELECT employee_id, date, 
               GROUP_CONCAT(time_slot_id) as slots,
               GROUP_CONCAT(is_available) as availabilities
        FROM availability
        GROUP BY employee_id, date
    """)
    
    converted_count = 0
    for row in cursor.fetchall():
        employee_id = row[0]
        date = row[1]
        slots = row[2].split(',') if row[2] else []
        availabilities = [int(x) for x in row[3].split(',')] if row[3] else []
        
        # is_available=0のスロットを特定
        unavailable_slots = [
            slot for slot, avail in zip(slots, availabilities) 
            if avail == 0
        ]
        
        if not unavailable_slots:
            continue
        
        # スロットIDから午前/午後を判定
        # V2のtime_slotsテーブルから期間情報を取得
        morning_unavailable = False
        afternoon_unavailable = False
        
        for slot in unavailable_slots:
            # スロットIDから判定（数値の場合はtime_slotsテーブルを参照）
            try:
                slot_id = int(slot)
                cursor.execute("""
                    SELECT name, start_time FROM time_slots WHERE id = ?
                """, (slot_id,))
                slot_info = cursor.fetchone()
                if slot_info:
                    name = slot_info[0].lower() if slot_info[0] else ''
                    start_time = slot_info[1] if slot_info[1] else ''
                    # 午前/午後を判定
                    if '午前' in name or 'am' in name or (start_time and start_time < '12:00'):
                        morning_unavailable = True
                    else:
                        afternoon_unavailable = True
            except (ValueError, TypeError):
                # 文字列IDの場合
                slot_str = str(slot).lower()
                if '午前' in slot_str or 'am' in slot_str or 'morning' in slot_str:
                    morning_unavailable = True
                elif '午後' in slot_str or 'pm' in slot_str or 'afternoon' in slot_str:
                    afternoon_unavailable = True
        
        # 休暇種別の決定
        if morning_unavailable and afternoon_unavailable:
            absence_type = 'full_day'
        elif morning_unavailable:
            absence_type = 'morning'
        elif afternoon_unavailable:
            absence_type = 'afternoon'
        else:
            continue
        
        # 休暇データ挿入
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO employee_absences 
                (employee_id, absence_date, absence_type, reason)
                VALUES (?, ?, ?, ?)
            """, (employee_id, date, absence_type, 'V2データから移行'))
            if cursor.rowcount > 0:
                converted_count += 1
        except sqlite3.IntegrityError:
            # 既に存在する場合はスキップ
            pass
    
    print(f"  ✓ {converted_count}件の休暇データを変換しました")


def backup_v2_data():
    """V2データのバックアップ"""
    import shutil
    
    backup_path = DB_PATH.parent / f"shift_v2_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ V2データをバックアップしました: {backup_path}")
    return backup_path
