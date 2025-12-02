"""Tests for generic utility helpers."""

from shift_scheduler.utils import get_month_range


def test_get_month_range_crosses_year_boundary() -> None:
    start, end = get_month_range(2025, 12)
    assert start == "2025-12-20"
    assert end == "2026-01-20"


def test_get_month_range_within_same_year() -> None:
    start, end = get_month_range(2025, 1)
    assert start == "2025-01-20"
    assert end == "2025-02-20"
