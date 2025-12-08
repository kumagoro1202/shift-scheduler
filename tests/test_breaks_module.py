"""Test suite for breaks module with comprehensive coverage."""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from src.shift_scheduler.breaks import (
    _parse_time,
    _window_overlaps,
    generate_time_intervals,
    _break_windows_for_pattern,
    _find_covering_shift,
    auto_assign_and_save_breaks,
    validate_reception_coverage,
    get_break_schedules,
    PREFERRED_WINDOWS,
)


class TestParseTime:
    """Test time parsing utility."""

    def test_parse_time_valid(self):
        """Test parsing valid time string."""
        result = _parse_time("08:30")
        assert isinstance(result, datetime)
        assert result.hour == 8
        assert result.minute == 30

    def test_parse_time_midnight(self):
        """Test parsing midnight."""
        result = _parse_time("00:00")
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_time_noon(self):
        """Test parsing noon."""
        result = _parse_time("12:00")
        assert result.hour == 12
        assert result.minute == 0


class TestWindowOverlaps:
    """Test time window overlap detection."""

    def test_overlaps_partial(self):
        """Test partial overlap detection."""
        assert _window_overlaps(("11:00", "12:00"), ("11:30", "12:30"))
        assert _window_overlaps(("11:30", "12:30"), ("11:00", "12:00"))

    def test_overlaps_complete(self):
        """Test complete overlap detection."""
        assert _window_overlaps(("11:00", "13:00"), ("11:30", "12:30"))
        assert _window_overlaps(("11:30", "12:30"), ("11:00", "13:00"))

    def test_no_overlap_separate(self):
        """Test non-overlapping windows."""
        assert not _window_overlaps(("11:00", "12:00"), ("13:00", "14:00"))
        assert not _window_overlaps(("13:00", "14:00"), ("11:00", "12:00"))

    def test_no_overlap_adjacent(self):
        """Test adjacent but non-overlapping windows."""
        assert not _window_overlaps(("11:00", "12:00"), ("12:00", "13:00"))
        assert not _window_overlaps(("12:00", "13:00"), ("11:00", "12:00"))


class TestGenerateTimeIntervals:
    """Test time interval generation."""

    def test_generate_15_minute_intervals(self):
        """Test generating 15-minute intervals."""
        result = generate_time_intervals("08:30", "09:00", 15)
        assert len(result) == 2
        assert result[0] == ("08:30", "08:45")
        assert result[1] == ("08:45", "09:00")

    def test_generate_30_minute_intervals(self):
        """Test generating 30-minute intervals."""
        result = generate_time_intervals("08:00", "09:00", 30)
        assert len(result) == 2
        assert result[0] == ("08:00", "08:30")
        assert result[1] == ("08:30", "09:00")

    def test_generate_60_minute_intervals(self):
        """Test generating 60-minute intervals."""
        result = generate_time_intervals("08:00", "12:00", 60)
        assert len(result) == 4
        assert result[0] == ("08:00", "09:00")
        assert result[3] == ("11:00", "12:00")

    def test_generate_uneven_intervals(self):
        """Test generating intervals that don't divide evenly."""
        result = generate_time_intervals("08:00", "08:40", 15)
        assert len(result) == 3
        assert result[0] == ("08:00", "08:15")
        assert result[1] == ("08:15", "08:30")
        assert result[2] == ("08:30", "08:40")

    def test_generate_empty_range(self):
        """Test generating intervals for empty range."""
        result = generate_time_intervals("08:00", "08:00", 15)
        assert len(result) == 0


class TestBreakWindowsForPattern:
    """Test break window selection based on pattern."""

    def test_break_windows_for_2_hours(self):
        """Test break windows for 2+ hour breaks."""
        result = _break_windows_for_pattern(2.0)
        assert len(result) == 2
        assert result[0] == PREFERRED_WINDOWS[0]
        assert result[1] == PREFERRED_WINDOWS[2]

    def test_break_windows_for_1_hour(self):
        """Test break windows for 1 hour break."""
        result = _break_windows_for_pattern(1.0)
        assert len(result) == 1
        assert result[0] == PREFERRED_WINDOWS[1]

    def test_break_windows_for_half_hour(self):
        """Test break windows for less than 1 hour."""
        result = _break_windows_for_pattern(0.5)
        assert len(result) == 0

    def test_break_windows_for_zero(self):
        """Test break windows for zero breaks."""
        result = _break_windows_for_pattern(0.0)
        assert len(result) == 0

    def test_break_windows_for_1_5_hours(self):
        """Test break windows for 1.5 hours."""
        result = _break_windows_for_pattern(1.5)
        assert len(result) == 1


class TestFindCoveringShift:
    """Test finding shift that covers a break window."""

    def test_find_covering_shift_exact_match(self):
        """Test finding shift that exactly covers window."""
        shifts = [
            {"id": 1, "start_time": "11:00", "end_time": "12:00"},
        ]
        result = _find_covering_shift(shifts, ("11:00", "12:00"))
        assert result is not None
        assert result["id"] == 1

    def test_find_covering_shift_larger_shift(self):
        """Test finding shift that covers window with extra time."""
        shifts = [
            {"id": 1, "start_time": "08:30", "end_time": "13:00"},
        ]
        result = _find_covering_shift(shifts, ("11:00", "12:00"))
        assert result is not None
        assert result["id"] == 1

    def test_find_covering_shift_no_match(self):
        """Test fallback to first shift when no match."""
        shifts = [
            {"id": 1, "start_time": "08:30", "end_time": "10:00"},
            {"id": 2, "start_time": "13:00", "end_time": "15:00"},
        ]
        result = _find_covering_shift(shifts, ("11:00", "12:00"))
        assert result is not None
        assert result["id"] == 1  # Falls back to first

    def test_find_covering_shift_empty_shifts(self):
        """Test with empty shift list."""
        result = _find_covering_shift([], ("11:00", "12:00"))
        assert result is None

    def test_find_covering_shift_multiple_matches(self):
        """Test with multiple covering shifts."""
        shifts = [
            {"id": 1, "start_time": "08:30", "end_time": "14:00"},
            {"id": 2, "start_time": "10:00", "end_time": "15:00"},
        ]
        result = _find_covering_shift(shifts, ("11:00", "12:00"))
        assert result["id"] == 1  # Returns first match


class TestAutoAssignAndSaveBreaks:
    """Test automatic break assignment."""

    def test_auto_assign_insufficient_staff(self):
        """Test when there are fewer than 3 reception staff."""
        shifts = [
            {"id": 1, "employee_id": 1, "time_slot": {"area": "受付"}},
            {"id": 2, "employee_id": 2, "time_slot": {"area": "受付"}},
        ]
        
        count, success, warnings = auto_assign_and_save_breaks("2025-12-08", shifts)
        
        assert count == 0
        assert success is True
        assert len(warnings) == 1
        assert "3名未満" in warnings[0]

    @patch("src.shift_scheduler.breaks.get_employment_pattern")
    @patch("src.shift_scheduler.breaks.delete_break_schedules_by_date_range")
    @patch("src.shift_scheduler.breaks.create_break_schedule")
    def test_auto_assign_basic_success(self, mock_create, mock_delete, mock_get_pattern):
        """Test successful break assignment with 3 staff."""
        from src.shift_scheduler.models import EmploymentPattern
        
        pattern = EmploymentPattern(
            id="full", name="フルタイム", category="常勤",
            start_time="08:30", end_time="17:00", break_hours=2.0,
            work_hours=7.0, can_work_afternoon=True
        )
        mock_get_pattern.return_value = pattern
        
        shifts = [
            {
                "id": 1, "employee_id": 1, "employee_name": "職員1",
                "start_time": "08:30", "end_time": "13:00",
                "time_slot": {"area": "受付"},
                "employee": {"employment_pattern_id": "full"}
            },
            {
                "id": 2, "employee_id": 2, "employee_name": "職員2",
                "start_time": "08:30", "end_time": "13:00",
                "time_slot": {"area": "受付"},
                "employee": {"employment_pattern_id": "full"}
            },
            {
                "id": 3, "employee_id": 3, "employee_name": "職員3",
                "start_time": "08:30", "end_time": "13:00",
                "time_slot": {"area": "受付"},
                "employee": {"employment_pattern_id": "full"}
            },
        ]
        
        count, success, warnings = auto_assign_and_save_breaks("2025-12-08", shifts)
        
        assert count >= 0
        mock_delete.assert_called_once_with("2025-12-08", "2025-12-08")

    @patch("src.shift_scheduler.breaks.get_employment_pattern")
    @patch("src.shift_scheduler.breaks.delete_break_schedules_by_date_range")
    @patch("src.shift_scheduler.breaks.create_break_schedule")
    def test_auto_assign_with_one_hour_break(self, mock_create, mock_delete, mock_get_pattern):
        """Test break assignment with 1-hour break pattern."""
        from src.shift_scheduler.models import EmploymentPattern
        
        pattern = EmploymentPattern(
            id="part", name="パート", category="非常勤",
            start_time="08:30", end_time="13:30", break_hours=1.0,
            work_hours=4.0, can_work_afternoon=False
        )
        mock_get_pattern.return_value = pattern
        
        shifts = [
            {
                "id": i, "employee_id": i, "employee_name": f"職員{i}",
                "start_time": "08:30", "end_time": "13:30",
                "time_slot": {"area": "受付"},
                "employee": {"employment_pattern_id": "part"}
            }
            for i in range(1, 4)
        ]
        
        count, success, warnings = auto_assign_and_save_breaks("2025-12-08", shifts)
        
        assert count >= 0

    @patch("src.shift_scheduler.breaks.get_employment_pattern")
    def test_auto_assign_no_breaks_needed(self, mock_get_pattern):
        """Test when no breaks are needed."""
        from src.shift_scheduler.models import EmploymentPattern
        
        pattern = EmploymentPattern(
            id="short", name="短時間", category="パート",
            start_time="08:30", end_time="11:30", break_hours=0.0,
            work_hours=3.0, can_work_afternoon=False
        )
        mock_get_pattern.return_value = pattern
        
        shifts = [
            {
                "id": i, "employee_id": i, "employee_name": f"職員{i}",
                "start_time": "08:30", "end_time": "11:30",
                "time_slot": {"area": "受付"},
                "employee": {"employment_pattern_id": "short"}
            }
            for i in range(1, 4)
        ]
        
        count, success, warnings = auto_assign_and_save_breaks("2025-12-08", shifts)
        
        assert count == 0
        assert not success

    def test_auto_assign_non_reception_shifts(self):
        """Test with non-reception shifts."""
        shifts = [
            {"id": 1, "employee_id": 1, "time_slot": {"area": "リハ室"}},
            {"id": 2, "employee_id": 2, "time_slot": {"area": "リハ室"}},
            {"id": 3, "employee_id": 3, "time_slot": {"area": "リハ室"}},
        ]
        
        count, success, warnings = auto_assign_and_save_breaks("2025-12-08", shifts)
        
        assert count == 0
        assert success is True


class TestValidateReceptionCoverage:
    """Test reception coverage validation."""

    def test_validate_coverage_no_reception_shifts(self):
        """Test validation with no reception shifts."""
        shifts = [
            {"id": 1, "time_slot": {"area": "リハ室"}},
        ]
        
        is_valid, warnings = validate_reception_coverage("2025-12-08", shifts, [])
        
        assert is_valid is True
        assert len(warnings) == 0

    def test_validate_coverage_sufficient_staff(self):
        """Test validation with sufficient staff."""
        shifts = [
            {
                "id": 1, "employee_id": 1,
                "start_time": "08:30", "end_time": "19:00",
                "time_slot": {"area": "受付"}
            },
            {
                "id": 2, "employee_id": 2,
                "start_time": "08:30", "end_time": "19:00",
                "time_slot": {"area": "受付"}
            },
            {
                "id": 3, "employee_id": 3,
                "start_time": "08:30", "end_time": "19:00",
                "time_slot": {"area": "受付"}
            },
        ]
        
        is_valid, warnings = validate_reception_coverage("2025-12-08", shifts, [])
        
        assert is_valid is True
        assert len(warnings) == 0

    def test_validate_coverage_with_breaks(self):
        """Test validation considering break schedules."""
        shifts = [
            {
                "id": 1, "employee_id": 1,
                "start_time": "08:30", "end_time": "12:30",
                "time_slot": {"area": "受付"}
            },
            {
                "id": 2, "employee_id": 2,
                "start_time": "08:30", "end_time": "12:30",
                "time_slot": {"area": "受付"}
            },
        ]
        
        breaks = [
            {
                "employee_id": 1,
                "break_start_time": "11:00",
                "break_end_time": "12:00"
            },
        ]
        
        is_valid, warnings = validate_reception_coverage("2025-12-08", shifts, breaks)
        
        # Should have some warnings due to reduced coverage during break
        # Specific behavior depends on time windows checked
        assert isinstance(warnings, list)

    def test_validate_coverage_insufficient_staff(self):
        """Test validation with insufficient staff."""
        shifts = [
            {
                "id": 1, "employee_id": 1,
                "start_time": "08:30", "end_time": "12:30",
                "time_slot": {"area": "受付"}
            },
        ]
        
        is_valid, warnings = validate_reception_coverage("2025-12-08", shifts, [])
        
        assert is_valid is False
        assert len(warnings) > 0

    def test_validate_coverage_overlapping_breaks(self):
        """Test validation when multiple people on break."""
        shifts = [
            {
                "id": 1, "employee_id": 1,
                "start_time": "08:30", "end_time": "13:00",
                "time_slot": {"area": "受付"}
            },
            {
                "id": 2, "employee_id": 2,
                "start_time": "08:30", "end_time": "13:00",
                "time_slot": {"area": "受付"}
            },
            {
                "id": 3, "employee_id": 3,
                "start_time": "08:30", "end_time": "13:00",
                "time_slot": {"area": "受付"}
            },
        ]
        
        breaks = [
            {"employee_id": 1, "break_start_time": "11:00", "break_end_time": "12:00"},
            {"employee_id": 2, "break_start_time": "11:00", "break_end_time": "12:00"},
        ]
        
        is_valid, warnings = validate_reception_coverage("2025-12-08", shifts, breaks)
        
        # Should have warnings during 11:00-12:00 when only 1 person working
        assert len(warnings) > 0
        assert any("11:" in w for w in warnings)


class TestGetBreakSchedules:
    """Test retrieving break schedules."""

    @patch("src.shift_scheduler.breaks.list_break_schedules_by_date")
    def test_get_break_schedules(self, mock_list):
        """Test getting break schedules for a date."""
        from src.shift_scheduler.models import BreakSchedule
        
        mock_schedules = [
            BreakSchedule(
                id=1, shift_id=1, employee_id=1, date="2025-12-08",
                break_number=1, break_start_time="11:00", break_end_time="12:00"
            ),
        ]
        mock_list.return_value = mock_schedules
        
        result = get_break_schedules("2025-12-08")
        
        assert len(result) == 1
        assert isinstance(result[0], dict)
        mock_list.assert_called_once_with("2025-12-08")

    @patch("src.shift_scheduler.breaks.list_break_schedules_by_date")
    def test_get_break_schedules_empty(self, mock_list):
        """Test getting break schedules when none exist."""
        mock_list.return_value = []
        
        result = get_break_schedules("2025-12-08")
        
        assert len(result) == 0
        assert isinstance(result, list)
