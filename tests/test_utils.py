"""Tests for generic utility helpers."""

from datetime import date
from src.shift_scheduler.utils import (
    get_month_range,
    generate_date_list,
    format_time,
    validate_date,
    validate_time,
    get_weekday_jp,
)


def test_get_month_range_crosses_year_boundary() -> None:
    start, end = get_month_range(2025, 12)
    assert start == "2025-12-20"
    assert end == "2026-01-20"


def test_get_month_range_normal_month() -> None:
    start, end = get_month_range(2025, 6)
    assert start == "2025-06-20"
    assert end == "2025-07-20"


def test_generate_date_list() -> None:
    dates = generate_date_list("2025-01-01", "2025-01-03")
    assert dates == ["2025-01-01", "2025-01-02", "2025-01-03"]


def test_generate_date_list_single_day() -> None:
    dates = generate_date_list("2025-01-01", "2025-01-01")
    assert dates == ["2025-01-01"]


def test_format_time() -> None:
    assert format_time("08:30") == "08:30"
    assert format_time("23:59") == "23:59"


def test_validate_date_valid() -> None:
    assert validate_date("2025-01-15") is True


def test_validate_date_invalid() -> None:
    assert validate_date("2025-13-01") is False
    assert validate_date("invalid") is False


def test_validate_time_valid() -> None:
    assert validate_time("08:30") is True
    assert validate_time("23:59") is True


def test_validate_time_invalid() -> None:
    assert validate_time("25:00") is False
    assert validate_time("invalid") is False


def test_get_weekday_jp() -> None:
    assert get_weekday_jp("2025-01-06") == "月"  # Monday
    assert get_weekday_jp("2025-01-07") == "火"  # Tuesday
    assert get_weekday_jp("2025-01-08") == "水"  # Wednesday
    assert get_weekday_jp("2025-01-09") == "木"  # Thursday
    assert get_weekday_jp("2025-01-10") == "金"  # Friday
    assert get_weekday_jp("2025-01-11") == "土"  # Saturday
    assert get_weekday_jp("2025-01-12") == "日"  # Sunday
