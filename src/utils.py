"""
ユーティリティ関数
"""
from datetime import datetime, timedelta
from typing import List
import pandas as pd


def generate_date_list(start_date: str, end_date: str) -> List[str]:
    """開始日から終了日までの日付リストを生成"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return dates


def get_month_range(year: int, month: int) -> tuple:
    """指定月の開始日と終了日を取得"""
    start_date = datetime(year, month, 1)
    
    # 次の月の1日を取得して1日引く
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    return (
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )


def format_time(time_str: str) -> str:
    """時刻文字列を整形 (HH:MM)"""
    try:
        dt = datetime.strptime(time_str, "%H:%M")
        return dt.strftime("%H:%M")
    except:
        return time_str


def validate_date(date_str: str) -> bool:
    """日付文字列が有効かチェック"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except:
        return False


def validate_time(time_str: str) -> bool:
    """時刻文字列が有効かチェック"""
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except:
        return False


def get_weekday_jp(date_str: str) -> str:
    """日付から曜日を取得（日本語）"""
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return weekdays[date.weekday()]


def export_to_excel(shifts: List[dict], filepath: str) -> bool:
    """シフトをExcelファイルに出力"""
    try:
        if not shifts:
            return False
        
        df = pd.DataFrame(shifts)
        
        # 列の順序を整理
        columns = ['date', 'time_slot_name', 'start_time', 'end_time', 
                   'employee_name', 'skill_score']
        df = df[columns]
        
        # 列名を日本語に
        df.columns = ['日付', '時間帯', '開始時刻', '終了時刻', '職員名', 'スキル']
        
        # Excelに出力
        df.to_excel(filepath, index=False, engine='openpyxl')
        return True
    except Exception as e:
        print(f"Excel出力エラー: {e}")
        return False
