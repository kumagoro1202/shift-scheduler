"""Test suite for availability module with comprehensive coverage."""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from src.shift_scheduler.models import Employee, TimeSlot, Absence, EmploymentPattern
from src.shift_scheduler.availability import (
    _parse_date,
    is_employee_available,
    describe_unavailability,
    available_time_slots,
)


@pytest.fixture
def sample_employee():
    """Create a sample employee."""
    return Employee(
        id=1,
        name="テスト職員",
        employee_type="TYPE_A",
        employment_type="常勤",
        employment_pattern_id="full_early",
        skill_reha=80,
        skill_reception_am=70,
        skill_reception_pm=75,
        skill_general=60,
        is_active=True,
    )


@pytest.fixture
def sample_time_slot():
    """Create a sample time slot."""
    return TimeSlot(
        id="mon_am_reha",
        day_of_week=0,  # Monday
        period="morning",
        start_time="08:30",
        end_time="12:30",
        is_active=True,
        required_staff=2,
        area="リハ室",
        display_name="月曜午前リハ室",
    )


@pytest.fixture
def sample_pattern():
    """Create a sample employment pattern."""
    return EmploymentPattern(
        id="full_early",
        name="フルタイム早番",
        category="常勤",
        start_time="08:30",
        end_time="17:00",
        break_hours=1.0,
        work_hours=7.5,
        can_work_afternoon=True,
    )


class TestParseDate:
    """Test date parsing utility."""

    def test_parse_date_valid(self):
        """Test parsing valid date string."""
        result = _parse_date("2025-12-08")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 8

    def test_parse_date_monday(self):
        """Test weekday detection for Monday."""
        result = _parse_date("2025-12-08")  # Monday
        assert result.weekday() == 0

    def test_parse_date_sunday(self):
        """Test weekday detection for Sunday."""
        result = _parse_date("2025-12-07")  # Sunday
        assert result.weekday() == 6


class TestEmployeeAvailability:
    """Test employee availability checking."""

    def test_available_basic_match(self, sample_employee, sample_time_slot, sample_pattern):
        """Test basic availability when all conditions match."""
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=sample_pattern):
            result = is_employee_available(sample_employee, "2025-12-08", sample_time_slot)
            assert result is True

    def test_unavailable_inactive_slot(self, sample_employee):
        """Test unavailable when time slot is inactive."""
        inactive_slot = TimeSlot(
            id="inactive", day_of_week=0, period="morning", start_time="08:30",
            end_time="12:30", is_active=False, required_staff=2, area="リハ室",
            display_name="休診"
        )
        result = is_employee_available(sample_employee, "2025-12-08", inactive_slot)
        assert result is False

    def test_unavailable_wrong_weekday(self, sample_employee, sample_time_slot):
        """Test unavailable when weekday doesn't match."""
        # sample_time_slot is Monday (0), but date is Tuesday
        result = is_employee_available(sample_employee, "2025-12-09", sample_time_slot)
        assert result is False

    def test_unavailable_sunday(self, sample_employee):
        """Test unavailable on Sunday (clinic closed)."""
        sunday_slot = TimeSlot(
            id="sun", day_of_week=6, period="morning", start_time="08:30",
            end_time="12:30", is_active=True, required_staff=2, area="リハ室",
            display_name="日曜午前"
        )
        result = is_employee_available(sample_employee, "2025-12-07", sunday_slot)
        assert result is False

    def test_unavailable_full_day_absence(self, sample_employee, sample_time_slot):
        """Test unavailable with full day absence."""
        absence = Absence(
            id=1, employee_id=1, absence_date="2025-12-08",
            absence_type="full_day", reason="休暇"
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=absence):
            result = is_employee_available(sample_employee, "2025-12-08", sample_time_slot)
            assert result is False

    def test_unavailable_morning_absence(self, sample_employee, sample_time_slot):
        """Test unavailable with morning absence for morning slot."""
        absence = Absence(
            id=1, employee_id=1, absence_date="2025-12-08",
            absence_type="morning", reason="通院"
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=absence):
            result = is_employee_available(sample_employee, "2025-12-08", sample_time_slot)
            assert result is False

    def test_available_morning_absence_afternoon_slot(self, sample_employee, sample_pattern):
        """Test available with morning absence but afternoon slot."""
        afternoon_slot = TimeSlot(
            id="mon_pm", day_of_week=0, period="afternoon", start_time="13:30",
            end_time="17:00", is_active=True, required_staff=2, area="リハ室",
            display_name="月曜午後"
        )
        absence = Absence(
            id=1, employee_id=1, absence_date="2025-12-08",
            absence_type="morning", reason="通院"
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=absence), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=sample_pattern):
            result = is_employee_available(sample_employee, "2025-12-08", afternoon_slot)
            assert result is True

    def test_unavailable_afternoon_absence(self, sample_employee, sample_pattern):
        """Test unavailable with afternoon absence for afternoon slot."""
        afternoon_slot = TimeSlot(
            id="mon_pm", day_of_week=0, period="afternoon", start_time="13:30",
            end_time="19:00", is_active=True, required_staff=2, area="リハ室",
            display_name="月曜午後"
        )
        absence = Absence(
            id=1, employee_id=1, absence_date="2025-12-08",
            absence_type="afternoon", reason="早退"
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=absence):
            result = is_employee_available(sample_employee, "2025-12-08", afternoon_slot)
            assert result is False

    def test_unavailable_no_afternoon_work_pattern(self, sample_employee):
        """Test unavailable when pattern doesn't allow afternoon work."""
        afternoon_slot = TimeSlot(
            id="mon_pm", day_of_week=0, period="afternoon", start_time="13:30",
            end_time="19:00", is_active=True, required_staff=2, area="リハ室",
            display_name="月曜午後"
        )
        morning_only_pattern = EmploymentPattern(
            id="part_morning", name="午前のみ", category="パート",
            start_time="08:30", end_time="12:30", break_hours=0.0,
            work_hours=4.0, can_work_afternoon=False
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=morning_only_pattern):
            result = is_employee_available(sample_employee, "2025-12-08", afternoon_slot)
            assert result is False

    def test_unavailable_slot_before_pattern_start(self, sample_employee):
        """Test unavailable when slot starts before pattern start time."""
        early_slot = TimeSlot(
            id="early", day_of_week=0, period="morning", start_time="07:00",
            end_time="11:00", is_active=True, required_staff=2, area="リハ室",
            display_name="早朝"
        )
        pattern = EmploymentPattern(
            id="late_start", name="遅番", category="常勤",
            start_time="09:00", end_time="17:30", break_hours=1.0,
            work_hours=7.5, can_work_afternoon=True
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=pattern):
            result = is_employee_available(sample_employee, "2025-12-08", early_slot)
            assert result is False

    def test_unavailable_slot_after_pattern_end(self, sample_employee):
        """Test unavailable when slot ends after pattern end time."""
        late_slot = TimeSlot(
            id="late", day_of_week=0, period="afternoon", start_time="17:00",
            end_time="20:00", is_active=True, required_staff=2, area="リハ室",
            display_name="夜間"
        )
        pattern = EmploymentPattern(
            id="early", name="早番", category="常勤",
            start_time="08:30", end_time="17:00", break_hours=1.0,
            work_hours=7.5, can_work_afternoon=True
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=pattern):
            result = is_employee_available(sample_employee, "2025-12-08", late_slot)
            assert result is False

    def test_unavailable_pattern_not_found(self, sample_employee, sample_time_slot):
        """Test unavailable when employment pattern not found."""
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=None):
            result = is_employee_available(sample_employee, "2025-12-08", sample_time_slot)
            assert result is False

    def test_available_no_pattern_id(self, sample_time_slot):
        """Test available when employee has no pattern ID."""
        employee = Employee(
            id=1, name="パターンなし", employee_type="TYPE_A", employment_type="常勤",
            employment_pattern_id=None, skill_reha=80, skill_reception_am=70,
            skill_reception_pm=75, skill_general=60, is_active=True
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=None):
            result = is_employee_available(employee, "2025-12-08", sample_time_slot)
            assert result is True


class TestDescribeUnavailability:
    """Test unavailability reason description."""

    def test_describe_inactive_slot(self, sample_employee):
        """Test description for inactive slot."""
        inactive_slot = TimeSlot(
            id="inactive", day_of_week=0, period="morning", start_time="08:30",
            end_time="12:30", is_active=False, required_staff=2, area="リハ室",
            display_name="休診"
        )
        result = describe_unavailability(sample_employee, "2025-12-08", inactive_slot)
        assert result == "時間帯が休診です"

    def test_describe_wrong_weekday(self, sample_employee, sample_time_slot):
        """Test description for wrong weekday."""
        result = describe_unavailability(sample_employee, "2025-12-09", sample_time_slot)
        assert "曜日" in result

    def test_describe_sunday(self, sample_employee):
        """Test description for Sunday."""
        sunday_slot = TimeSlot(
            id="sun", day_of_week=6, period="morning", start_time="08:30",
            end_time="12:30", is_active=True, required_staff=2, area="リハ室",
            display_name="日曜"
        )
        result = describe_unavailability(sample_employee, "2025-12-07", sunday_slot)
        assert result == "日曜日は休診です"

    def test_describe_full_day_absence(self, sample_employee, sample_time_slot):
        """Test description for full day absence."""
        absence = Absence(
            id=1, employee_id=1, absence_date="2025-12-08",
            absence_type="full_day", reason="休暇"
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=absence):
            result = describe_unavailability(sample_employee, "2025-12-08", sample_time_slot)
            assert "終日休暇" in result
            assert "休暇" in result

    def test_describe_morning_absence(self, sample_employee, sample_time_slot):
        """Test description for morning absence."""
        absence = Absence(
            id=1, employee_id=1, absence_date="2025-12-08",
            absence_type="morning", reason="通院"
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=absence):
            result = describe_unavailability(sample_employee, "2025-12-08", sample_time_slot)
            assert "午前休" in result

    def test_describe_afternoon_absence(self, sample_employee):
        """Test description for afternoon absence."""
        afternoon_slot = TimeSlot(
            id="pm", day_of_week=0, period="afternoon", start_time="13:30",
            end_time="19:00", is_active=True, required_staff=2, area="リハ室",
            display_name="午後"
        )
        absence = Absence(
            id=1, employee_id=1, absence_date="2025-12-08",
            absence_type="afternoon", reason=None
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=absence):
            result = describe_unavailability(sample_employee, "2025-12-08", afternoon_slot)
            assert "午後休" in result

    def test_describe_no_afternoon_pattern(self, sample_employee):
        """Test description when pattern doesn't allow afternoon."""
        afternoon_slot = TimeSlot(
            id="pm", day_of_week=0, period="afternoon", start_time="13:30",
            end_time="19:00", is_active=True, required_staff=2, area="リハ室",
            display_name="午後"
        )
        morning_pattern = EmploymentPattern(
            id="morning", name="午前のみ", category="パート",
            start_time="08:30", end_time="12:30", break_hours=0.0,
            work_hours=4.0, can_work_afternoon=False
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=morning_pattern):
            result = describe_unavailability(sample_employee, "2025-12-08", afternoon_slot)
            assert "午後勤務不可" in result

    def test_describe_before_start_time(self, sample_employee, sample_time_slot):
        """Test description when slot is before pattern start."""
        late_pattern = EmploymentPattern(
            id="late", name="遅番", category="常勤",
            start_time="10:00", end_time="18:30", break_hours=1.0,
            work_hours=7.5, can_work_afternoon=True
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=late_pattern):
            result = describe_unavailability(sample_employee, "2025-12-08", sample_time_slot)
            assert "勤務開始前" in result

    def test_describe_after_end_time(self, sample_employee):
        """Test description when slot is after pattern end."""
        late_slot = TimeSlot(
            id="late", day_of_week=0, period="afternoon", start_time="18:00",
            end_time="20:00", is_active=True, required_staff=2, area="リハ室",
            display_name="夜"
        )
        early_pattern = EmploymentPattern(
            id="early", name="早番", category="常勤",
            start_time="08:30", end_time="17:00", break_hours=1.0,
            work_hours=7.5, can_work_afternoon=True
        )
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=early_pattern):
            result = describe_unavailability(sample_employee, "2025-12-08", late_slot)
            assert "勤務終了後" in result

    def test_describe_pattern_not_found(self, sample_employee, sample_time_slot):
        """Test description when pattern not found."""
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=None):
            result = describe_unavailability(sample_employee, "2025-12-08", sample_time_slot)
            assert "勤務パターンが見つかりません" == result

    def test_describe_available_returns_none(self, sample_employee, sample_time_slot, sample_pattern):
        """Test that describe returns None when employee is available."""
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=sample_pattern):
            result = describe_unavailability(sample_employee, "2025-12-08", sample_time_slot)
            assert result is None


class TestAvailableTimeSlots:
    """Test filtering available time slots."""

    def test_filter_available_slots(self, sample_employee, sample_pattern):
        """Test filtering to get only available slots."""
        slots = [
            TimeSlot(
                id="mon_am", day_of_week=0, period="morning", start_time="08:30",
                end_time="12:30", is_active=True, required_staff=2, area="リハ室",
                display_name="月曜午前"
            ),
            TimeSlot(
                id="tue_am", day_of_week=1, period="morning", start_time="08:30",
                end_time="12:30", is_active=True, required_staff=2, area="リハ室",
                display_name="火曜午前"
            ),
            TimeSlot(
                id="sun_am", day_of_week=6, period="morning", start_time="08:30",
                end_time="12:30", is_active=True, required_staff=2, area="リハ室",
                display_name="日曜午前"
            ),
        ]
        
        with patch("src.shift_scheduler.availability.get_absence", return_value=None), \
             patch("src.shift_scheduler.availability.get_employment_pattern", return_value=sample_pattern):
            # Monday 2025-12-08
            result = available_time_slots(sample_employee, "2025-12-08", slots)
            assert len(result) == 1
            assert result[0].id == "mon_am"

    def test_filter_empty_when_all_unavailable(self, sample_employee):
        """Test filtering returns empty when all unavailable."""
        slots = [
            TimeSlot(
                id="sun", day_of_week=6, period="morning", start_time="08:30",
                end_time="12:30", is_active=True, required_staff=2, area="リハ室",
                display_name="日曜"
            ),
        ]
        
        result = available_time_slots(sample_employee, "2025-12-07", slots)
        assert len(result) == 0
