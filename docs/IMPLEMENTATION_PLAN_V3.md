# シフト作成システム V3.0 改修実装計画書

## 作成日: 2025年11月27日

---

## 📋 目次

1. [概要](#1-概要)
2. [実装スケジュール](#2-実装スケジュール)
3. [詳細実装計画](#3-詳細実装計画)
4. [テスト計画](#4-テスト計画)
5. [リスク管理](#5-リスク管理)

---

## 1. 概要

### 1.1 改修の目的
- 時間帯ごとの勤務可否登録を廃止し、日付単位の休暇登録に簡素化
- 診療時間を固定化し、システムの堅牢性を向上
- 勤務形態マスタを整備し、運用の柔軟性を確保

### 1.2 主な変更点
1. **データベーススキーマの変更**
   - `employee_absences` テーブルの新規作成
   - `employment_patterns` テーブルの新規作成
   - `time_slots` テーブルの固定化
   - `availability` テーブルの廃止

2. **UI/UX の変更**
   - 時間帯設定ページの廃止
   - 勤務可能情報ページ → 休暇管理ページに改名・機能変更
   - 職員管理ページの勤務形態選択UI改修

3. **ロジックの変更**
   - 勤務可否判定ロジックの全面改修
   - シフト生成アルゴリズムの調整

---

## 2. 実装スケジュール

### 2.1 タイムライン（全9日間）

```
Day 1-2: Phase 1 - データベース基盤
Day 3-4: Phase 2 - マイグレーション機能
Day 5-6: Phase 3 - UI改修
Day 7-8: Phase 4 - ロジック改修とテスト
Day 9:   Phase 5 - サンプルデータとドキュメント
```

### 2.2 各Phaseの詳細

| Phase | タスク | 成果物 | 日数 |
|-------|--------|--------|------|
| Phase 1 | データベース設計・実装 | スキーマ定義、マスタデータ | 2日 |
| Phase 2 | マイグレーション実装 | migration_v3.py | 2日 |
| Phase 3 | UI改修 | 休暇管理ページ、職員管理改修 | 2日 |
| Phase 4 | ロジック改修・テスト | optimizer改修、テストコード | 2日 |
| Phase 5 | 最終調整 | サンプルDB、ドキュメント | 1日 |

---

## 3. 詳細実装計画

### Phase 1: データベース基盤整備（Day 1-2）

#### Task 1.1: 勤務形態マスタテーブルの作成

**ファイル**: `src/database.py`

**実装内容**:
```python
def init_employment_patterns_table():
    """勤務形態マスタテーブルを作成"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employment_patterns (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            break_hours REAL NOT NULL,
            work_hours REAL NOT NULL,
            can_work_afternoon BOOLEAN DEFAULT 1,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK(category IN ('full_time', 'short_time', 'part_time'))
        )
    """)
    
    # 初期データ投入
    patterns = [
        ('full_early', 'フルタイム（早番）', 'full_time', '08:30', '18:30', 2.0, 8.0, 1, '正職員・早番'),
        ('full_mid', 'フルタイム（中番）', 'full_time', '08:45', '18:45', 2.0, 8.0, 1, '正職員・中番'),
        ('full_late', 'フルタイム（遅番）', 'full_time', '09:00', '19:00', 2.0, 8.0, 1, '正職員・遅番'),
        ('short_time', '時短勤務', 'short_time', '08:45', '16:45', 1.0, 7.0, 0, '正職員・時短'),
        ('part_morning', 'パート午前', 'part_time', '08:45', '12:45', 0.0, 4.0, 0, 'パート・午前4時間'),
        ('part_morning_ext', 'パート午前延長', 'part_time', '08:45', '13:45', 0.0, 5.0, 0, 'パート・午前5時間'),
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO employment_patterns 
        (id, name, category, start_time, end_time, break_hours, work_hours, can_work_afternoon, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, patterns)
    
    conn.commit()
    conn.close()
```

**関連関数**:
```python
def get_all_employment_patterns() -> List[Dict[str, Any]]:
    """全勤務形態を取得"""
    
def get_employment_pattern_by_id(pattern_id: str) -> Optional[Dict[str, Any]]:
    """IDで勤務形態を取得"""
    
def get_employment_patterns_by_category(category: str) -> List[Dict[str, Any]]:
    """カテゴリで勤務形態を取得"""
```

**予定工数**: 4時間

---

#### Task 1.2: 時間帯マスタの固定化

**ファイル**: `src/database.py`

**実装内容**:
```python
def init_fixed_time_slots():
    """固定時間帯マスタを作成"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 既存のtime_slotsテーブルをバックアップ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_slots_backup AS 
        SELECT * FROM time_slots
    """)
    
    # time_slotsテーブルを再作成
    cursor.execute("DROP TABLE IF EXISTS time_slots")
    
    cursor.execute("""
        CREATE TABLE time_slots (
            id TEXT PRIMARY KEY,
            day_of_week INTEGER NOT NULL,
            period TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            required_staff INTEGER DEFAULT 2,
            area TEXT DEFAULT '受付',
            display_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK(day_of_week >= 0 AND day_of_week <= 6),
            CHECK(period IN ('morning', 'afternoon'))
        )
    """)
    
    # 固定時間帯データ
    time_slots = [
        # 月曜
        ('mon_am', 0, 'morning', '09:00', '12:30', 1, 2, '受付', '月曜午前'),
        ('mon_pm', 0, 'afternoon', '15:30', '18:30', 1, 2, '受付', '月曜午後'),
        # 火曜
        ('tue_am', 1, 'morning', '09:00', '12:30', 1, 2, '受付', '火曜午前'),
        ('tue_pm', 1, 'afternoon', '15:30', '18:30', 1, 2, '受付', '火曜午後'),
        # 水曜
        ('wed_am', 2, 'morning', '09:00', '12:30', 1, 2, '受付', '水曜午前'),
        ('wed_pm', 2, 'afternoon', '15:30', '17:30', 1, 2, '受付', '水曜午後'),
        # 木曜
        ('thu_am', 3, 'morning', '09:00', '12:30', 1, 2, '受付', '木曜午前'),
        # 金曜
        ('fri_am', 4, 'morning', '09:00', '12:30', 1, 2, '受付', '金曜午前'),
        ('fri_pm', 4, 'afternoon', '15:30', '18:30', 1, 2, '受付', '金曜午後'),
        # 土曜
        ('sat_am', 5, 'morning', '09:00', '13:30', 1, 2, '受付', '土曜午前'),
    ]
    
    cursor.executemany("""
        INSERT INTO time_slots 
        (id, day_of_week, period, start_time, end_time, is_active, required_staff, area, display_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, time_slots)
    
    conn.commit()
    conn.close()
```

**予定工数**: 3時間

---

#### Task 1.3: 休暇テーブルの作成

**ファイル**: `src/database.py`

**実装内容**:
```python
def init_employee_absences_table():
    """休暇登録テーブルを作成"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_absences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            absence_date DATE NOT NULL,
            absence_type TEXT NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            UNIQUE(employee_id, absence_date, absence_type),
            CHECK(absence_type IN ('full_day', 'morning', 'afternoon'))
        )
    """)
    
    # インデックス作成
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_absence_employee_date 
        ON employee_absences(employee_id, absence_date)
    """)
    
    conn.commit()
    conn.close()
```

**休暇管理関数**:
```python
def add_absence(employee_id: int, absence_date: str, absence_type: str, reason: str = None) -> int:
    """休暇を登録"""
    
def remove_absence(employee_id: int, absence_date: str, absence_type: str = None) -> bool:
    """休暇を削除（absence_type未指定の場合は全種別削除）"""
    
def get_absence(employee_id: int, absence_date: str) -> Optional[Dict[str, Any]]:
    """指定日の休暇情報を取得"""
    
def get_absences_by_employee(employee_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """職員の期間内の休暇一覧を取得"""
    
def get_absences_by_date(absence_date: str) -> List[Dict[str, Any]]:
    """指定日の全職員の休暇一覧を取得"""
```

**予定工数**: 4時間

---

#### Task 1.4: employeesテーブルの拡張

**ファイル**: `src/database.py`

**実装内容**:
```python
def add_employment_pattern_to_employees():
    """employeesテーブルにemployment_pattern_idを追加"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            ALTER TABLE employees 
            ADD COLUMN employment_pattern_id TEXT 
            REFERENCES employment_patterns(id)
        """)
        conn.commit()
    except sqlite3.OperationalError as e:
        # カラムが既に存在する場合はスキップ
        if "duplicate column name" not in str(e).lower():
            raise
    finally:
        conn.close()
```

**予定工数**: 1時間

---

### Phase 2: マイグレーション機能実装（Day 3-4）

#### Task 2.1: V2→V3マイグレーションスクリプト

**新規ファイル**: `src/migration_v3.py`

**実装内容**:
```python
"""
V2.0 → V3.0 マイグレーション
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from database import get_connection

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
            init_fixed_time_slots
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
        
        # Phase 3: availability → employee_absences 変換
        print("🔄 Phase 3: 勤務可否データを休暇データに変換中...")
        
        # availabilityテーブルが存在する場合のみ処理
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='availability'
        """)
        
        if cursor.fetchone():
            migrate_availability_to_absences(cursor)
        
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
        morning_unavailable = any('am' in slot or '午前' in slot for slot in unavailable_slots)
        afternoon_unavailable = any('pm' in slot or '午後' in slot for slot in unavailable_slots)
        
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
        cursor.execute("""
            INSERT OR IGNORE INTO employee_absences 
            (employee_id, absence_date, absence_type, reason)
            VALUES (?, ?, ?, ?)
        """, (employee_id, date, absence_type, 'V2データから移行'))
    
    print(f"  ✓ {cursor.rowcount}件の休暇データを変換しました")


def backup_v2_data():
    """V2データのバックアップ"""
    from database import DB_PATH
    import shutil
    
    backup_path = DB_PATH.parent / f"shift_v2_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ V2データをバックアップしました: {backup_path}")
    return backup_path
```

**予定工数**: 8時間

---

#### Task 2.2: マイグレーション実行スクリプト

**新規ファイル**: `scripts/migrate_to_v3.py`

```python
"""
V3.0マイグレーション実行スクリプト
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from migration_v3 import (
    check_v3_migration_needed,
    migrate_to_v3,
    backup_v2_data
)

def main():
    print("=" * 60)
    print("シフト作成システム V3.0 マイグレーション")
    print("=" * 60)
    print()
    
    # マイグレーション必要性チェック
    if not check_v3_migration_needed():
        print("✅ 既にV3.0にマイグレーション済みです")
        return
    
    # 確認プロンプト
    response = input("V2.0からV3.0にマイグレーションしますか？ (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ マイグレーションをキャンセルしました")
        return
    
    # バックアップ
    print()
    backup_path = backup_v2_data()
    print()
    
    # マイグレーション実行
    try:
        migrate_to_v3()
        print()
        print("=" * 60)
        print("✅ マイグレーションが正常に完了しました")
        print(f"📁 バックアップ: {backup_path}")
        print("=" * 60)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ エラー: {e}")
        print(f"📁 バックアップから復元してください: {backup_path}")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**予定工数**: 2時間

---

### Phase 3: UI改修（Day 5-6）

#### Task 3.1: 休暇管理ページの作成

**ファイル名変更**: 
- `pages/3_📅_勤務可能情報.py` → `pages/3_🏖️_休暇管理.py`

**実装内容**:
```python
"""
休暇管理ページ（V3.0）
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
import calendar

sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import (
    get_all_employees,
    add_absence,
    remove_absence,
    get_absence,
    get_absences_by_employee
)

st.set_page_config(page_title="休暇管理", page_icon="🏖️", layout="wide")

st.title("🏖️ 休暇管理")

st.info("💡 **デフォルト動作**: 休暇登録のない日は自動的に「勤務可能」です。休暇を取る日のみ登録してください。")

# 職員選択
employees = get_all_employees()
if not employees:
    st.warning("⚠️ 職員が登録されていません")
    st.stop()

selected_employee = st.selectbox(
    "職員を選択",
    options=employees,
    format_func=lambda x: f"{x['name']} ({x.get('employment_pattern_id', 'フルタイム')})"
)

# 年月選択
col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("年", range(datetime.now().year, datetime.now().year + 2))
with col2:
    month = st.selectbox("月", range(1, 13), index=datetime.now().month - 1)

# カレンダー表示
st.subheader(f"{year}年{month}月 休暇カレンダー")

# 月の日付リスト生成
cal = calendar.monthcalendar(year, month)
weekday_names = ['月', '火', '水', '木', '金', '土', '日']

# ヘッダー
header_cols = st.columns(7)
for idx, day_name in enumerate(weekday_names):
    with header_cols[idx]:
        st.markdown(f"**{day_name}**")

# カレンダー本体
for week in cal:
    cols = st.columns(7)
    for idx, day in enumerate(week):
        with cols[idx]:
            if day == 0:
                st.markdown("&nbsp;")
                continue
            
            date_obj = datetime(year, month, day)
            date_str = date_obj.strftime("%Y-%m-%d")
            is_sunday = idx == 6
            
            # 休暇情報取得
            absence = get_absence(selected_employee['id'], date_str)
            
            # 表示アイコン
            if is_sunday:
                icon = "🌙"
                status = "定休"
            elif absence:
                if absence['absence_type'] == 'full_day':
                    icon = "🏖️"
                    status = "終日休暇"
                elif absence['absence_type'] == 'morning':
                    icon = "🌅"
                    status = "午前休"
                else:
                    icon = "🌆"
                    status = "午後休"
            else:
                icon = "✅"
                status = "勤務可能"
            
            st.markdown(f"**{day}**")
            st.markdown(f"{icon} {status}")
            
            # 設定ボタン
            if not is_sunday:
                with st.expander("設定"):
                    current_type = absence['absence_type'] if absence else None
                    
                    absence_type = st.radio(
                        "状態",
                        ["勤務可能", "終日休暇", "午前休", "午後休"],
                        index=["勤務可能", "終日休暇", "午前休", "午後休"].index(
                            status if status in ["勤務可能", "終日休暇", "午前休", "午後休"] else "勤務可能"
                        ),
                        key=f"absence_{date_str}"
                    )
                    
                    reason = st.text_input("理由", value=absence.get('reason', '') if absence else '', key=f"reason_{date_str}")
                    
                    if st.button("保存", key=f"save_{date_str}"):
                        if absence_type == "勤務可能":
                            remove_absence(selected_employee['id'], date_str)
                            st.success("✅ 勤務可能に設定しました")
                        else:
                            type_map = {
                                "終日休暇": "full_day",
                                "午前休": "morning",
                                "午後休": "afternoon"
                            }
                            add_absence(
                                selected_employee['id'],
                                date_str,
                                type_map[absence_type],
                                reason
                            )
                            st.success(f"✅ {absence_type}を登録しました")
                        st.rerun()
```

**予定工数**: 6時間

---

#### Task 3.2: 時間帯設定ページの廃止

**対応内容**:
1. `pages/2_⏰_時間帯設定.py` を削除
2. `main.py` に診療スケジュール表示を追加

**main.pyへの追加**:
```python
# ホーム画面に診療スケジュール表示
st.subheader("📅 診療スケジュール")

with st.expander("診療時間を確認", expanded=False):
    schedule_data = {
        "曜日": ["月", "火", "水", "木", "金", "土", "日"],
        "午前": ["09:00-12:30", "09:00-12:30", "09:00-12:30", "09:00-12:30", "09:00-12:30", "09:00-13:30", "休診"],
        "午後": ["15:30-18:30", "15:30-18:30", "15:30-17:30", "休診", "15:30-18:30", "休診", "休診"]
    }
    
    import pandas as pd
    st.dataframe(pd.DataFrame(schedule_data), use_container_width=True)
```

**予定工数**: 2時間

---

#### Task 3.3: 職員管理ページの改修

**ファイル**: `pages/1_👥_職員管理.py`

**変更内容**:
- `work_pattern` 選択を `employment_pattern_id` 選択に変更
- 勤務形態マスタから選択肢を取得

```python
# 勤務形態選択（変更後）
from database import get_all_employment_patterns

patterns = get_all_employment_patterns()

# 雇用形態に応じてフィルタ
if employment_type == "正職員":
    available_patterns = [p for p in patterns if p['category'] in ['full_time', 'short_time']]
else:
    available_patterns = [p for p in patterns if p['category'] == 'part_time']

employment_pattern_id = st.selectbox(
    "勤務形態",
    options=[p['id'] for p in available_patterns],
    format_func=lambda x: next(
        f"{p['name']} ({p['start_time']}-{p['end_time']})" 
        for p in available_patterns if p['id'] == x
    )
)
```

**予定工数**: 4時間

---

### Phase 4: ロジック改修とテスト（Day 7-8）

#### Task 4.1: 勤務可否判定ロジックの改修

**新規ファイル**: `src/availability_checker.py`

```python
"""
勤務可否判定ロジック（V3.0）
"""
from datetime import datetime
from typing import Optional
from database import (
    get_employment_pattern_by_id,
    get_absence
)

def is_employee_available(employee, date_str: str, time_slot) -> bool:
    """
    職員が指定日の指定時間帯に勤務可能かを判定
    
    Args:
        employee: 職員情報（dict）
        date_str: 日付文字列 (YYYY-MM-DD)
        time_slot: 時間帯情報（dict）
    
    Returns:
        bool: 勤務可能ならTrue
    """
    # 1. 時間帯が休診の場合
    if not time_slot.get('is_active', True):
        return False
    
    # 2. 日曜日チェック
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    if date_obj.weekday() == 6:  # 日曜日
        return False
    
    # 3. 休暇チェック
    absence = get_absence(employee['id'], date_str)
    if absence:
        if absence['absence_type'] == 'full_day':
            return False
        if absence['absence_type'] == 'morning' and time_slot['period'] == 'morning':
            return False
        if absence['absence_type'] == 'afternoon' and time_slot['period'] == 'afternoon':
            return False
    
    # 4. 勤務形態チェック
    pattern = get_employment_pattern_by_id(employee.get('employment_pattern_id', 'full_early'))
    if not pattern:
        return False
    
    # 午後勤務可否チェック
    if time_slot['period'] == 'afternoon' and not pattern.get('can_work_afternoon', True):
        return False
    
    # 勤務時間範囲チェック
    slot_start = datetime.strptime(time_slot['start_time'], "%H:%M").time()
    slot_end = datetime.strptime(time_slot['end_time'], "%H:%M").time()
    pattern_start = datetime.strptime(pattern['start_time'], "%H:%M").time()
    pattern_end = datetime.strptime(pattern['end_time'], "%H:%M").time()
    
    if slot_start < pattern_start or slot_end > pattern_end:
        return False
    
    return True


def get_available_time_slots_for_date(employee, date_str: str, all_time_slots):
    """指定日に勤務可能な時間帯のリストを取得"""
    return [
        ts for ts in all_time_slots
        if is_employee_available(employee, date_str, ts)
    ]
```

**予定工数**: 4時間

---

#### Task 4.2: シフト生成ロジックの改修

**ファイル**: `src/optimizer_v2.py`

**変更箇所**:
```python
# 旧: availabilityテーブル参照
# is_available = is_employee_available(emp_id, date_str, ts_id)

# 新: availability_checker使用
from availability_checker import is_employee_available

# 職員情報と時間帯情報を渡す
employee = get_employee_by_id(emp_id)
time_slot = get_time_slot_by_id(ts_id)
is_available = is_employee_available(employee, date_str, time_slot)
```

**予定工数**: 4時間

---

#### Task 4.3: テストコードの作成

**新規ファイル**: `tests/test_availability_v3.py`

```python
"""
V3.0 勤務可否判定のテスト
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from availability_checker import is_employee_available
from database import (
    init_database,
    create_employee,
    add_absence,
    get_all_time_slots
)

def test_full_day_absence():
    """終日休暇のテスト"""
    init_database()
    
    emp_id = create_employee(
        name="テスト職員",
        employment_pattern_id="full_early"
    )
    
    employee = {'id': emp_id, 'employment_pattern_id': 'full_early'}
    
    # 終日休暇登録
    add_absence(emp_id, "2025-12-01", "full_day")
    
    time_slots = get_all_time_slots()
    
    # 全時間帯で勤務不可のはず
    for ts in time_slots:
        if ts['id'] == 'mon_am' or ts['id'] == 'mon_pm':
            assert not is_employee_available(employee, "2025-12-01", ts)
    
    print("✅ 終日休暇テスト: PASS")

def test_morning_absence():
    """午前休のテスト"""
    # 実装省略
    pass

def test_afternoon_absence():
    """午後休のテスト"""
    # 実装省略
    pass

def test_part_time_afternoon():
    """パート職員の午後勤務不可テスト"""
    # 実装省略
    pass

if __name__ == "__main__":
    test_full_day_absence()
    test_morning_absence()
    test_afternoon_absence()
    test_part_time_afternoon()
    print("✅ 全テスト完了")
```

**予定工数**: 4時間

---

### Phase 5: サンプルデータとドキュメント（Day 9）

#### Task 5.1: サンプルデータ投入スクリプト

**新規ファイル**: `scripts/init_v3_sample_data.py`

```python
"""
V3.0用サンプルデータ投入
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import (
    init_database,
    create_employee,
    add_absence
)
from migration_v3 import migrate_to_v3, check_v3_migration_needed

def init_sample_data():
    """サンプルデータを投入"""
    
    print("=" * 60)
    print("サンプルデータ投入")
    print("=" * 60)
    
    # データベース初期化
    init_database()
    
    # V3マイグレーション実行
    if check_v3_migration_needed():
        migrate_to_v3()
    
    print("\n職員データ投入中...")
    
    # 職員データ
    employees_data = [
        {
            'name': '山田太郎',
            'employee_type': 'TYPE_A',
            'employment_type': '正職員',
            'employment_pattern_id': 'full_early',
            'skill_reha_room': 85,
            'skill_reception_am': 90,
            'skill_reception_pm': 85,
            'skill_flexibility': 90
        },
        {
            'name': '佐藤花子',
            'employee_type': 'TYPE_A',
            'employment_type': '正職員',
            'employment_pattern_id': 'full_mid',
            'skill_reha_room': 80,
            'skill_reception_am': 85,
            'skill_reception_pm': 90,
            'skill_flexibility': 85
        },
        {
            'name': '鈴木一郎',
            'employee_type': 'TYPE_B',
            'employment_type': '正職員',
            'employment_pattern_id': 'full_late',
            'skill_reha_room': 0,
            'skill_reception_am': 95,
            'skill_reception_pm': 95,
            'skill_flexibility': 80
        },
        {
            'name': '田中美咲',
            'employee_type': 'TYPE_C',
            'employment_type': '正職員',
            'employment_pattern_id': 'short_time',
            'skill_reha_room': 90,
            'skill_reception_am': 0,
            'skill_reception_pm': 0,
            'skill_flexibility': 75
        },
        {
            'name': '高橋健太',
            'employee_type': 'TYPE_D',
            'employment_type': 'パート',
            'employment_pattern_id': 'part_morning',
            'skill_reha_room': 70,
            'skill_reception_am': 0,
            'skill_reception_pm': 0,
            'skill_flexibility': 60
        },
    ]
    
    employee_ids = []
    for emp_data in employees_data:
        emp_id = create_employee(**emp_data)
        employee_ids.append(emp_id)
        print(f"  ✓ {emp_data['name']} を登録しました")
    
    print("\n休暇データ投入中...")
    
    # サンプル休暇データ
    base_date = datetime(2025, 12, 1)
    absences = [
        (employee_ids[0], base_date + timedelta(days=4), 'full_day', '年次有給休暇'),
        (employee_ids[1], base_date + timedelta(days=11), 'morning', '通院'),
        (employee_ids[2], base_date + timedelta(days=19), 'full_day', '年次有給休暇'),
        (employee_ids[3], base_date + timedelta(days=24), 'full_day', '年次有給休暇'),
    ]
    
    for emp_id, date_obj, absence_type, reason in absences:
        add_absence(emp_id, date_obj.strftime("%Y-%m-%d"), absence_type, reason)
        print(f"  ✓ {employees_data[employee_ids.index(emp_id)]['name']} の休暇を登録しました")
    
    print("\n" + "=" * 60)
    print("✅ サンプルデータの投入が完了しました")
    print("=" * 60)

if __name__ == "__main__":
    init_sample_data()
```

**予定工数**: 3時間

---

#### Task 5.2: ドキュメント更新

**更新対象ファイル**:
1. `README.md` - V3.0の新機能説明追加
2. `docs/USER_GUIDE.md` - 休暇管理の使い方追加
3. `docs/MIGRATION_GUIDE_V2_TO_V3.md` - 新規作成

**予定工数**: 3時間

---

#### Task 5.3: サンプルデータベースの作成

**手順**:
```powershell
# 1. 既存DBのバックアップ
Copy-Item data\shift.db data\shift_backup.db

# 2. DBの初期化
Remove-Item data\shift.db

# 3. サンプルデータ投入
python scripts\init_v3_sample_data.py

# 4. 動作確認
streamlit run main.py
```

**予定工数**: 2時間

---

## 4. テスト計画

### 4.1 単体テスト

| テスト項目 | 対象関数 | 期待結果 |
|-----------|---------|---------|
| 終日休暇判定 | `is_employee_available` | 全時間帯で勤務不可 |
| 午前休判定 | `is_employee_available` | 午前のみ勤務不可 |
| 午後休判定 | `is_employee_available` | 午後のみ勤務不可 |
| パート午後勤務 | `is_employee_available` | 午後は常に勤務不可 |
| 時短午後勤務 | `is_employee_available` | 午後は常に勤務不可 |
| 勤務時間範囲外 | `is_employee_available` | 勤務不可 |

### 4.2 結合テスト

| テスト項目 | テストシナリオ |
|-----------|--------------|
| シフト生成（休暇あり） | 休暇登録した職員が該当日のシフトに含まれない |
| シフト生成（パート） | パート職員が午後シフトに含まれない |
| 休暇登録・削除 | 休暇登録後、カレンダーに反映される |
| マイグレーション | V2データが正常にV3に変換される |

### 4.3 E2Eテスト

| テスト項目 | 操作手順 | 期待結果 |
|-----------|---------|---------|
| 休暇登録フロー | 職員選択→日付選択→休暇種別選択→保存 | カレンダーに反映 |
| シフト生成フロー | 休暇登録→シフト生成→結果確認 | 休暇日は勤務なし |
| Excel出力 | シフト生成→Excel出力 | 正常にダウンロード |

---

## 5. リスク管理

### 5.1 技術的リスク

| リスク | 影響度 | 対策 |
|-------|-------|------|
| マイグレーション失敗 | 高 | バックアップ機能の実装、ロールバック手順の整備 |
| データ損失 | 高 | マイグレーション前の自動バックアップ |
| パフォーマンス劣化 | 中 | インデックス作成、クエリ最適化 |
| UI不具合 | 中 | 十分なテスト期間の確保 |

### 5.2 スケジュールリスク

| リスク | 影響度 | 対策 |
|-------|-------|------|
| 実装遅延 | 中 | 優先度を明確化、Phase単位でのマイルストーン設定 |
| テスト不足 | 高 | Phase 4に十分な時間を確保 |
| 仕様変更 | 中 | 要件定義の早期確定 |

### 5.3 運用リスク

| リスク | 影響度 | 対策 |
|-------|-------|------|
| ユーザー混乱 | 中 | 詳細なマイグレーションガイド作成 |
| データ不整合 | 高 | マイグレーション後の検証スクリプト |
| バグ発見 | 中 | ロールバック手順の明示 |

---

## 6. リリース手順

### 6.1 リリース前チェックリスト

- [ ] 全単体テストが合格
- [ ] 全結合テストが合格
- [ ] マイグレーションスクリプトの動作確認
- [ ] サンプルデータの動作確認
- [ ] ドキュメントの更新完了
- [ ] バックアップ・ロールバック手順の検証

### 6.2 リリース作業

1. **バックアップ作成**
   ```powershell
   python scripts/migrate_to_v3.py
   # → 自動でバックアップが作成される
   ```

2. **マイグレーション実行**
   - スクリプトの指示に従う
   - エラーが発生した場合はロールバック

3. **動作確認**
   ```powershell
   streamlit run main.py
   ```
   - 全ページが正常に表示されるか確認
   - サンプルシフトを生成して確認

4. **ユーザーへの引き渡し**
   - マイグレーションガイドの共有
   - 新機能の説明
   - サポート体制の案内

---

## 7. 付録

### 7.1 ファイル構成（変更後）

```
src/
  ├── database.py                  (更新)
  ├── migration_v3.py              (新規)
  ├── availability_checker.py      (新規)
  ├── optimizer_v2.py              (更新)
  └── ...

pages/
  ├── 1_👥_職員管理.py             (更新)
  ├── 2_⏰_時間帯設定.py           (削除)
  ├── 3_🏖️_休暇管理.py            (新規・旧3_📅から改名)
  ├── 4_🎯_シフト生成.py          (番号変更)
  └── 5_📋_シフト表示.py          (番号変更)

scripts/
  ├── migrate_to_v3.py             (新規)
  ├── init_v3_sample_data.py       (新規)
  └── ...

tests/
  ├── test_availability_v3.py      (新規)
  └── ...

docs/
  ├── REQUIREMENTS_V3.md           (新規)
  ├── IMPLEMENTATION_PLAN_V3.md    (本ドキュメント)
  ├── MIGRATION_GUIDE_V2_TO_V3.md  (新規)
  └── ...
```

### 7.2 データベーススキーマ（V3.0最終形）

```sql
-- 勤務形態マスタ
CREATE TABLE employment_patterns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    break_hours REAL NOT NULL,
    work_hours REAL NOT NULL,
    can_work_afternoon BOOLEAN DEFAULT 1,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 時間帯マスタ（固定）
CREATE TABLE time_slots (
    id TEXT PRIMARY KEY,
    day_of_week INTEGER NOT NULL,
    period TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    required_staff INTEGER DEFAULT 2,
    area TEXT DEFAULT '受付',
    display_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 休暇登録
CREATE TABLE employee_absences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    absence_date DATE NOT NULL,
    absence_type TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    UNIQUE(employee_id, absence_date, absence_type)
);

-- 職員マスタ（拡張）
ALTER TABLE employees ADD COLUMN employment_pattern_id TEXT REFERENCES employment_patterns(id);
```

---

**文書管理**
- 版数: 1.0
- 作成日: 2025-11-27
- 最終更新: 2025-11-27
