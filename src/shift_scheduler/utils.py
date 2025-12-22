"""Generic utility helpers used throughout the application."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List, Sequence

import pandas as pd


def generate_date_list(start_date: str, end_date: str) -> List[str]:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    if end < start:
        raise ValueError("end_date must be on or after start_date")

    result = []
    current = start
    while current <= end:
        result.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return result


def get_month_range(year: int, month: int, closing_day: int = 20) -> tuple[str, str]:
    """Return the scheduling period for a month based on the closing day."""

    start = datetime(year, month, closing_day)

    if month == 12:
        next_month_year = year + 1
        next_month = 1
    else:
        next_month_year = year
        next_month = month + 1

    end = datetime(next_month_year, next_month, closing_day)

    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def format_time(time_str: str) -> str:
    try:
        return datetime.strptime(time_str, "%H:%M").strftime("%H:%M")
    except ValueError:
        return time_str


def validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_time(time_str: str) -> bool:
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


def get_weekday_jp(date_str: str) -> str:
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return weekdays[dt.weekday()]


def export_to_excel(shifts: Sequence[dict], filepath: str) -> bool:
    """シフトデータをExcel形式でエクスポートする。
    
    勤務形態、各スキルスコア詳細、休憩時間を含む。
    """
    try:
        if not shifts:
            return False
        df = pd.DataFrame(shifts)
        
        # 職員情報とスキル詳細を展開
        df['employment_pattern'] = df['employee'].apply(
            lambda e: e.get('employment_pattern_id', '') if isinstance(e, dict) else ''
        )
        df['skill_reha'] = df['employee'].apply(
            lambda e: e.get('skill_reha', 0) if isinstance(e, dict) else 0
        )
        df['skill_reception_am'] = df['employee'].apply(
            lambda e: e.get('skill_reception_am', 0) if isinstance(e, dict) else 0
        )
        df['skill_reception_pm'] = df['employee'].apply(
            lambda e: e.get('skill_reception_pm', 0) if isinstance(e, dict) else 0
        )
        df['skill_general'] = df['employee'].apply(
            lambda e: e.get('skill_general', 0) if isinstance(e, dict) else 0
        )
        
        # エクスポート用カラムを選択
        columns = [
            "date",
            "time_slot_name",
            "start_time",
            "end_time",
            "employee_name",
            "employment_pattern",
            "skill_reha",
            "skill_reception_am",
            "skill_reception_pm",
            "skill_general",
            "skill_score",
        ]
        df = df[columns]
        df.columns = [
            "日付",
            "時間帯",
            "開始時刻",
            "終了時刻",
            "職員名",
            "勤務形態",
            "リハ室スキル",
            "受付午前スキル",
            "受付午後スキル",
            "総合対応力",
            "スキルスコア",
        ]
        df.to_excel(filepath, index=False, engine="openpyxl")
        return True
    except Exception:
        return False
