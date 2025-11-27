"""
シフト作成システム - データベース管理
"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# データベースファイルのパス
# PyInstallerでビルドされた場合
if getattr(sys, 'frozen', False):
    # PyInstallerの一時フォルダ（読み取り専用）からユーザーディレクトリにコピー
    if hasattr(sys, '_MEIPASS'):
        # パッケージ内のデータベーステンプレート
        TEMPLATE_DB = Path(sys._MEIPASS) / "data" / "shift.db"
        # ユーザーディレクトリのデータベース（書き込み可能）
        USER_DATA_DIR = Path.home() / ".shift_scheduler"
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        DB_PATH = USER_DATA_DIR / "shift.db"
        
        # 初回起動時: テンプレートをコピー
        if not DB_PATH.exists() and TEMPLATE_DB.exists():
            import shutil
            shutil.copy2(TEMPLATE_DB, DB_PATH)
    else:
        # フォールバック
        BASE_DIR = Path(sys.executable).parent
        DB_PATH = BASE_DIR / "data" / "shift.db"
else:
    # 開発環境
    BASE_DIR = Path(__file__).parent.parent
    DB_PATH = BASE_DIR / "data" / "shift.db"


def get_connection():
    """データベース接続を取得"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """データベースの初期化（テーブル作成）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 職員テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            skill_score INTEGER NOT NULL CHECK(skill_score >= 1 AND skill_score <= 100),
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 時間帯テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            required_employees INTEGER DEFAULT 2,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # シフトテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            time_slot_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (time_slot_id) REFERENCES time_slots(id),
            FOREIGN KEY (employee_id) REFERENCES employees(id),
            UNIQUE(date, time_slot_id, employee_id)
        )
    """)
    
    # 勤務可能情報テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date DATE NOT NULL,
            time_slot_id INTEGER NOT NULL,
            is_available BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id),
            FOREIGN KEY (time_slot_id) REFERENCES time_slots(id),
            UNIQUE(employee_id, date, time_slot_id)
        )
    """)
    
    # 設定テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    conn.commit()
    conn.close()


# ========== 職員管理 ==========

def get_all_employees(include_inactive=False) -> List[Dict[str, Any]]:
    """全職員を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM employees"
    if not include_inactive:
        query += " WHERE is_active = 1"
    query += " ORDER BY name"
    
    cursor.execute(query)
    employees = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return employees


def get_employee_by_id(employee_id: int) -> Optional[Dict[str, Any]]:
    """IDで職員を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_employee(
    name: str, 
    skill_score: int = None,
    employee_type: str = 'TYPE_A',
    employment_type: str = '正職員',
    work_type: str = 'フルタイム',
    work_pattern: str = 'P1',
    skill_reha_room: int = 0,
    skill_reception_am: int = 0,
    skill_reception_pm: int = 0,
    skill_flexibility: int = 0
) -> int:
    """職員を新規登録（V2対応）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # V1互換性のため、skill_scoreが指定されている場合は4項目に反映
    if skill_score is not None:
        skill_reha_room = skill_score if skill_reha_room == 0 else skill_reha_room
        skill_reception_am = skill_score if skill_reception_am == 0 else skill_reception_am
        skill_reception_pm = skill_score if skill_reception_pm == 0 else skill_reception_pm
        skill_flexibility = skill_score if skill_flexibility == 0 else skill_flexibility
    else:
        skill_score = max(skill_reha_room, skill_reception_am, skill_reception_pm, skill_flexibility)
    
    cursor.execute("""
        INSERT INTO employees (
            name, skill_score, employee_type, employment_type, work_type, work_pattern,
            skill_reha_room, skill_reception_am, skill_reception_pm, skill_flexibility
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, skill_score, employee_type, employment_type, work_type, work_pattern,
          skill_reha_room, skill_reception_am, skill_reception_pm, skill_flexibility))
    
    employee_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return employee_id


def update_employee(
    employee_id: int, 
    name: str = None, 
    skill_score: int = None,
    employee_type: str = None,
    employment_type: str = None,
    work_type: str = None,
    work_pattern: str = None,
    skill_reha_room: int = None,
    skill_reception_am: int = None,
    skill_reception_pm: int = None,
    skill_flexibility: int = None
) -> bool:
    """職員情報を更新（V2対応）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 更新するフィールドを動的に構築
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if skill_score is not None:
        updates.append("skill_score = ?")
        params.append(skill_score)
    if employee_type is not None:
        updates.append("employee_type = ?")
        params.append(employee_type)
    if employment_type is not None:
        updates.append("employment_type = ?")
        params.append(employment_type)
    if work_type is not None:
        updates.append("work_type = ?")
        params.append(work_type)
    if work_pattern is not None:
        updates.append("work_pattern = ?")
        params.append(work_pattern)
    if skill_reha_room is not None:
        updates.append("skill_reha_room = ?")
        params.append(skill_reha_room)
    if skill_reception_am is not None:
        updates.append("skill_reception_am = ?")
        params.append(skill_reception_am)
    if skill_reception_pm is not None:
        updates.append("skill_reception_pm = ?")
        params.append(skill_reception_pm)
    if skill_flexibility is not None:
        updates.append("skill_flexibility = ?")
        params.append(skill_flexibility)
    
    if not updates:
        conn.close()
        return False
    
    params.append(employee_id)
    query = f"UPDATE employees SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(query, params)
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_employee(employee_id: int) -> bool:
    """職員を削除（論理削除）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE employees SET is_active = 0 WHERE id = ?",
        (employee_id,)
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


# ========== 時間帯管理 ==========

def get_all_time_slots() -> List[Dict[str, Any]]:
    """全時間帯を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM time_slots ORDER BY start_time")
    time_slots = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return time_slots


# ========== 勤務パターン管理 ==========

def get_all_work_patterns() -> List[Dict[str, Any]]:
    """全勤務パターンを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM work_patterns ORDER BY id")
        patterns = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return patterns
    except sqlite3.OperationalError:
        # テーブルが存在しない場合は空リストを返す
        conn.close()
        return []


def get_work_pattern_by_id(pattern_id: str) -> Optional[Dict[str, Any]]:
    """IDで勤務パターンを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM work_patterns WHERE id = ?", (pattern_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        conn.close()
        return None


def get_work_patterns_by_type(work_type: str) -> List[Dict[str, Any]]:
    """勤務形態で勤務パターンをフィルタ"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM work_patterns WHERE work_type = ? ORDER BY id",
            (work_type,)
        )
        patterns = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return patterns
    except sqlite3.OperationalError:
        conn.close()
        return []


def get_work_patterns_by_employment_type(employment_type: str) -> List[Dict[str, Any]]:
    """雇用形態で勤務パターンをフィルタ"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM work_patterns WHERE employment_type = ? ORDER BY id",
            (employment_type,)
        )
        patterns = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return patterns
    except sqlite3.OperationalError:
        conn.close()
        return []


# ========== 時間帯管理 ==========


def create_time_slot(
    name: str, 
    start_time: str, 
    end_time: str, 
    required_employees: int = 2,
    area_type: str = '受付',
    time_period: str = '終日',
    required_employees_min: int = 1,
    required_employees_max: int = None,
    target_skill_score: int = 150,
    skill_weight: float = 1.0
) -> int:
    """時間帯を新規登録（V2対応）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # required_employees_maxが指定されていない場合はrequired_employeesを使用
    if required_employees_max is None:
        required_employees_max = required_employees
    
    cursor.execute("""
        INSERT INTO time_slots (
            name, start_time, end_time, required_employees,
            area_type, time_period, required_employees_min, required_employees_max,
            target_skill_score, skill_weight
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, start_time, end_time, required_employees,
          area_type, time_period, required_employees_min, required_employees_max,
          target_skill_score, skill_weight))
    
    time_slot_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return time_slot_id


def update_time_slot(
    time_slot_id: int, 
    name: str = None, 
    start_time: str = None, 
    end_time: str = None, 
    required_employees: int = None,
    area_type: str = None,
    time_period: str = None,
    required_employees_min: int = None,
    required_employees_max: int = None,
    target_skill_score: int = None,
    skill_weight: float = None
) -> bool:
    """時間帯情報を更新（V2対応）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 更新するフィールドを動的に構築
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if start_time is not None:
        updates.append("start_time = ?")
        params.append(start_time)
    if end_time is not None:
        updates.append("end_time = ?")
        params.append(end_time)
    if required_employees is not None:
        updates.append("required_employees = ?")
        params.append(required_employees)
    if area_type is not None:
        updates.append("area_type = ?")
        params.append(area_type)
    if time_period is not None:
        updates.append("time_period = ?")
        params.append(time_period)
    if required_employees_min is not None:
        updates.append("required_employees_min = ?")
        params.append(required_employees_min)
    if required_employees_max is not None:
        updates.append("required_employees_max = ?")
        params.append(required_employees_max)
    if target_skill_score is not None:
        updates.append("target_skill_score = ?")
        params.append(target_skill_score)
    if skill_weight is not None:
        updates.append("skill_weight = ?")
        params.append(skill_weight)
    
    if not updates:
        conn.close()
        return False
    
    params.append(time_slot_id)
    query = f"UPDATE time_slots SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(query, params)
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_time_slot(time_slot_id: int) -> bool:
    """時間帯を削除"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM time_slots WHERE id = ?", (time_slot_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


# ========== シフト管理 ==========

def get_shifts_by_date_range(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """期間指定でシフトを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, e.name as employee_name, e.skill_score,
               ts.name as time_slot_name, ts.start_time, ts.end_time
        FROM shifts s
        JOIN employees e ON s.employee_id = e.id
        JOIN time_slots ts ON s.time_slot_id = ts.id
        WHERE s.date BETWEEN ? AND ?
        ORDER BY s.date, ts.start_time
    """, (start_date, end_date))
    shifts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return shifts


def create_shift(date: str, time_slot_id: int, employee_id: int) -> Optional[int]:
    """シフトを登録"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO shifts (date, time_slot_id, employee_id) VALUES (?, ?, ?)",
            (date, time_slot_id, employee_id)
        )
        shift_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return shift_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def delete_shift(shift_id: int) -> bool:
    """シフトを削除"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_shifts_by_date_range(start_date: str, end_date: str) -> int:
    """期間指定でシフトを削除"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM shifts WHERE date BETWEEN ? AND ?",
        (start_date, end_date)
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


# ========== 勤務可能情報管理 ==========

def get_availability(employee_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """職員の勤務可能情報を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, ts.name as time_slot_name
        FROM availability a
        JOIN time_slots ts ON a.time_slot_id = ts.id
        WHERE a.employee_id = ? AND a.date BETWEEN ? AND ?
        ORDER BY a.date, ts.start_time
    """, (employee_id, start_date, end_date))
    availability = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return availability


def set_availability(employee_id: int, date: str, time_slot_id: int, is_available: bool = True) -> bool:
    """勤務可能情報を設定"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO availability (employee_id, date, time_slot_id, is_available)
        VALUES (?, ?, ?, ?)
    """, (employee_id, date, time_slot_id, is_available))
    conn.commit()
    conn.close()
    return True


def is_employee_available(employee_id: int, date: str, time_slot_id: int) -> bool:
    """職員が指定日時に勤務可能かチェック"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT is_available FROM availability
        WHERE employee_id = ? AND date = ? AND time_slot_id = ?
    """, (employee_id, date, time_slot_id))
    row = cursor.fetchone()
    conn.close()
    
    # 登録がない場合は可能とみなす
    if row is None:
        return True
    return bool(row['is_available'])


# ========== 設定管理 ==========

def get_setting(key: str, default: str = "") -> str:
    """設定値を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default


def set_setting(key: str, value: str) -> bool:
    """設定値を保存"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value)
    )
    conn.commit()
    conn.close()
    return True


# ========== 休憩スケジュール管理 ==========

def create_break_schedule(
    shift_id: int,
    employee_id: int,
    date: str,
    break_number: int,
    break_start_time: str,
    break_end_time: str
) -> Optional[int]:
    """休憩スケジュールを登録"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO break_schedules 
            (shift_id, employee_id, date, break_number, break_start_time, break_end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (shift_id, employee_id, date, break_number, break_start_time, break_end_time))
        
        break_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return break_id
    except sqlite3.OperationalError:
        # テーブルが存在しない場合
        conn.close()
        return None
    except sqlite3.IntegrityError:
        conn.close()
        return None


def get_break_schedules_by_date(date: str) -> List[Dict[str, Any]]:
    """日付で休憩スケジュールを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT bs.*, e.name as employee_name
            FROM break_schedules bs
            JOIN employees e ON bs.employee_id = e.id
            WHERE bs.date = ?
            ORDER BY bs.break_start_time
        """, (date,))
        schedules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return schedules
    except sqlite3.OperationalError:
        conn.close()
        return []


def get_break_schedules_by_shift(shift_id: int) -> List[Dict[str, Any]]:
    """シフトIDで休憩スケジュールを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM break_schedules 
            WHERE shift_id = ?
            ORDER BY break_number
        """, (shift_id,))
        schedules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return schedules
    except sqlite3.OperationalError:
        conn.close()
        return []


def delete_break_schedules_by_shift(shift_id: int) -> int:
    """シフトIDで休憩スケジュールを削除"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM break_schedules WHERE shift_id = ?", (shift_id,))
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count
    except sqlite3.OperationalError:
        conn.close()
        return 0


def delete_break_schedules_by_date_range(start_date: str, end_date: str) -> int:
    """期間指定で休憩スケジュールを削除"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM break_schedules WHERE date BETWEEN ? AND ?",
            (start_date, end_date)
        )
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count
    except sqlite3.OperationalError:
        conn.close()
        return 0
