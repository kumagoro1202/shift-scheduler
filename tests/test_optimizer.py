"""Test suite for optimizer module with comprehensive coverage."""
import pytest
from datetime import datetime
from src.shift_scheduler.models import Employee, TimeSlot, EmploymentPattern
from src.shift_scheduler.optimizer import (
    _time_to_minutes,
    check_time_overlap,
    calculate_skill_score,
    _can_assign_to_area,
    _select_employees_for_slot,
    _evaluate_part_time_rule,
    generate_shifts,
    calculate_skill_balance,
    ShiftGenerationError,
)


@pytest.fixture
def sample_employees():
    """Create sample employees for testing."""
    return [
        Employee(
            id=1,
            name="職員A",
            employee_type="TYPE_A",
            employment_type="常勤",
            employment_pattern_id="full_early",
            skill_reha=80,
            skill_reception_am=70,
            skill_reception_pm=75,
            skill_general=60,
            is_active=True,
        ),
        Employee(
            id=2,
            name="職員B",
            employee_type="TYPE_B",
            employment_type="常勤",
            employment_pattern_id="full_mid",
            skill_reha=0,
            skill_reception_am=85,
            skill_reception_pm=80,
            skill_general=65,
            is_active=True,
        ),
        Employee(
            id=3,
            name="職員C",
            employee_type="TYPE_C",
            employment_type="非常勤",
            employment_pattern_id="part_morning",
            skill_reha=75,
            skill_reception_am=0,
            skill_reception_pm=0,
            skill_general=55,
            is_active=True,
        ),
        Employee(
            id=4,
            name="職員D",
            employee_type="TYPE_D",
            employment_type="パート",
            employment_pattern_id="part_morning",
            skill_reha=60,
            skill_reception_am=0,
            skill_reception_pm=0,
            skill_general=50,
            is_active=True,
        ),
    ]


@pytest.fixture
def sample_time_slots():
    """Create sample time slots for testing."""
    return [
        TimeSlot(
            id="mon_am_reha",
            day_of_week=0,
            period="morning",
            start_time="08:30",
            end_time="12:30",
            is_active=True,
            required_staff=2,
            area="リハ室",
            display_name="月曜午前リハ室",
            target_skill_score=300,
        ),
        TimeSlot(
            id="mon_am_reception",
            day_of_week=0,
            period="morning",
            start_time="08:30",
            end_time="12:30",
            is_active=True,
            required_staff=3,
            area="受付",
            display_name="月曜午前受付",
            target_skill_score=450,
        ),
        TimeSlot(
            id="mon_pm_reception",
            day_of_week=0,
            period="afternoon",
            start_time="13:30",
            end_time="19:00",
            is_active=True,
            required_staff=3,
            area="受付",
            display_name="月曜午後受付",
            target_skill_score=450,
        ),
    ]


class TestTimeUtilities:
    """Test time manipulation utility functions."""

    def test_time_to_minutes_standard(self):
        """Test conversion of standard time to minutes."""
        assert _time_to_minutes("00:00") == 0
        assert _time_to_minutes("01:00") == 60
        assert _time_to_minutes("12:30") == 750
        assert _time_to_minutes("23:59") == 1439

    def test_time_to_minutes_edge_cases(self):
        """Test edge cases for time conversion."""
        assert _time_to_minutes("00:01") == 1
        assert _time_to_minutes("08:30") == 510
        assert _time_to_minutes("19:00") == 1140


class TestTimeOverlap:
    """Test time overlap detection."""

    def test_no_overlap_separate(self, sample_time_slots):
        """Test non-overlapping time slots."""
        slot_am = sample_time_slots[0]  # 08:30-12:30
        slot_pm = sample_time_slots[2]  # 13:30-19:00
        assert not check_time_overlap(slot_am, slot_pm)

    def test_overlap_partial(self):
        """Test partially overlapping slots."""
        slot_a = TimeSlot(
            id="a", day_of_week=0, period="morning", start_time="08:30", end_time="12:30",
            is_active=True, required_staff=2, area="リハ室", display_name="A"
        )
        slot_b = TimeSlot(
            id="b", day_of_week=0, period="morning", start_time="11:00", end_time="14:00",
            is_active=True, required_staff=2, area="リハ室", display_name="B"
        )
        assert check_time_overlap(slot_a, slot_b)

    def test_overlap_complete(self):
        """Test completely overlapping slots."""
        slot_a = TimeSlot(
            id="a", day_of_week=0, period="morning", start_time="08:30", end_time="17:00",
            is_active=True, required_staff=2, area="リハ室", display_name="A"
        )
        slot_b = TimeSlot(
            id="b", day_of_week=0, period="morning", start_time="09:00", end_time="12:00",
            is_active=True, required_staff=2, area="リハ室", display_name="B"
        )
        assert check_time_overlap(slot_a, slot_b)

    def test_no_overlap_adjacent(self):
        """Test adjacent but non-overlapping slots."""
        slot_a = TimeSlot(
            id="a", day_of_week=0, period="morning", start_time="08:30", end_time="12:30",
            is_active=True, required_staff=2, area="リハ室", display_name="A"
        )
        slot_b = TimeSlot(
            id="b", day_of_week=0, period="afternoon", start_time="12:30", end_time="17:00",
            is_active=True, required_staff=2, area="リハ室", display_name="B"
        )
        assert not check_time_overlap(slot_a, slot_b)


class TestSkillScoreCalculation:
    """Test skill score calculation logic."""

    def test_skill_score_reha(self, sample_employees, sample_time_slots):
        """Test skill calculation for rehab area."""
        emp = sample_employees[0]  # TYPE_A with reha=80, general=60
        slot = sample_time_slots[0]  # リハ室
        score = calculate_skill_score(emp, slot)
        assert score == 140  # 80 + 60

    def test_skill_score_reception_am(self, sample_employees, sample_time_slots):
        """Test skill calculation for morning reception."""
        emp = sample_employees[1]  # TYPE_B with reception_am=85, general=65
        slot = sample_time_slots[1]  # 午前受付
        score = calculate_skill_score(emp, slot)
        assert score == 150  # 85 + 65

    def test_skill_score_reception_pm(self, sample_employees, sample_time_slots):
        """Test skill calculation for afternoon reception."""
        emp = sample_employees[1]  # TYPE_B with reception_pm=80, general=65
        slot = sample_time_slots[2]  # 午後受付
        score = calculate_skill_score(emp, slot)
        assert score == 145  # 80 + 65

    def test_skill_score_no_area_skill(self, sample_employees):
        """Test skill calculation when no specific area skill."""
        emp = sample_employees[0]
        slot = TimeSlot(
            id="other", day_of_week=0, period="morning", start_time="08:30", end_time="12:30",
            is_active=True, required_staff=2, area="その他", display_name="その他"
        )
        score = calculate_skill_score(emp, slot)
        assert score == emp.skill_general


class TestAreaAssignment:
    """Test area assignment validation."""

    def test_can_assign_type_a_to_reha(self, sample_employees, sample_time_slots):
        """TYPE_A can work in rehab area."""
        emp = sample_employees[0]  # TYPE_A with reha skill
        slot = sample_time_slots[0]  # リハ室
        assert _can_assign_to_area(emp, slot)

    def test_cannot_assign_type_b_to_reha(self, sample_employees, sample_time_slots):
        """TYPE_B cannot work in rehab area."""
        emp = sample_employees[1]  # TYPE_B
        slot = sample_time_slots[0]  # リハ室
        assert not _can_assign_to_area(emp, slot)

    def test_can_assign_type_b_to_reception(self, sample_employees, sample_time_slots):
        """TYPE_B can work in reception area."""
        emp = sample_employees[1]  # TYPE_B with reception skill
        slot = sample_time_slots[1]  # 受付
        assert _can_assign_to_area(emp, slot)

    def test_cannot_assign_type_c_to_reception(self, sample_employees, sample_time_slots):
        """TYPE_C cannot work in reception area."""
        emp = sample_employees[2]  # TYPE_C
        slot = sample_time_slots[1]  # 受付
        assert not _can_assign_to_area(emp, slot)

    def test_cannot_assign_without_skill(self, sample_employees, sample_time_slots):
        """Cannot assign if skill is zero."""
        emp = Employee(
            id=99, name="無スキル", employee_type="TYPE_A", employment_type="常勤",
            employment_pattern_id=None, skill_reha=0, skill_reception_am=0,
            skill_reception_pm=0, skill_general=50, is_active=True
        )
        slot = sample_time_slots[0]  # リハ室
        assert not _can_assign_to_area(emp, slot)


class TestEmployeeSelection:
    """Test employee selection logic."""

    def test_select_days_mode(self, sample_employees, sample_time_slots):
        """Test selection in days mode (minimize work count)."""
        candidates = sample_employees[:3]
        slot = sample_time_slots[0]
        work_count = {1: 5, 2: 3, 3: 3}  # emp2 and emp3 have fewer days
        
        # Only emp1 and emp3 can work in reha
        reha_capable = [e for e in candidates if _can_assign_to_area(e, slot)]
        selected = _select_employees_for_slot(reha_capable, slot, 2, work_count, "days")
        
        assert len(selected) == 2
        # Should select emp3 (3 days) over emp1 (5 days)
        assert sample_employees[2] in selected

    def test_select_skill_mode(self, sample_employees, sample_time_slots):
        """Test selection in skill mode."""
        candidates = sample_employees[:2]
        slot = sample_time_slots[1]  # reception
        work_count = {1: 0, 2: 0}
        
        reception_capable = [e for e in candidates if _can_assign_to_area(e, slot)]
        selected = _select_employees_for_slot(reception_capable, slot, 2, work_count, "skill")
        
        assert len(selected) == 2

    def test_select_balance_mode(self, sample_employees, sample_time_slots):
        """Test selection in balance mode."""
        candidates = sample_employees[:2]
        slot = sample_time_slots[1]  # reception
        work_count = {1: 2, 2: 5}
        
        reception_capable = [e for e in candidates if _can_assign_to_area(e, slot)]
        selected = _select_employees_for_slot(reception_capable, slot, 2, work_count, "balance")
        
        assert len(selected) == 2
        # Should prefer emp1 (fewer days)
        assert sample_employees[0] in selected

    def test_select_insufficient_candidates(self, sample_employees, sample_time_slots):
        """Test selection when not enough candidates."""
        candidates = sample_employees[:1]
        slot = sample_time_slots[0]
        work_count = {1: 0}
        
        selected = _select_employees_for_slot(candidates, slot, 3, work_count, "balance")
        
        assert len(selected) == 0  # Returns empty if insufficient


class TestPartTimeRule:
    """Test part-time staff pairing rule validation."""

    def test_no_violation_with_type_a(self, sample_employees, sample_time_slots):
        """No violation when TYPE_D is paired with TYPE_A."""
        from src.shift_scheduler.models import GeneratedShift
        
        shifts = [
            GeneratedShift(
                date="2025-12-08",
                time_slot_id="mon_am_reha",
                employee_id=1,
                employee_name="職員A",
                time_slot_name="月曜午前リハ室",
                start_time="08:30",
                end_time="12:30",
                skill_score=140,
                employee=sample_employees[0],
                time_slot=sample_time_slots[0],
            ),
            GeneratedShift(
                date="2025-12-08",
                time_slot_id="mon_am_reha",
                employee_id=4,
                employee_name="職員D",
                time_slot_name="月曜午前リハ室",
                start_time="08:30",
                end_time="12:30",
                skill_score=110,
                employee=sample_employees[3],
                time_slot=sample_time_slots[0],
            ),
        ]
        
        result = _evaluate_part_time_rule(shifts, sample_time_slots)
        assert result is None

    def test_violation_type_d_only(self, sample_employees, sample_time_slots):
        """Violation when only TYPE_D in rehab slot."""
        from src.shift_scheduler.models import GeneratedShift
        
        type_d_only_emp = Employee(
            id=5, name="職員D2", employee_type="TYPE_D", employment_type="パート",
            employment_pattern_id="part_morning", skill_reha=65,
            skill_reception_am=0, skill_reception_pm=0, skill_general=50, is_active=True
        )
        
        shifts = [
            GeneratedShift(
                date="2025-12-08",
                time_slot_id="mon_am_reha",
                employee_id=4,
                employee_name="職員D",
                time_slot_name="月曜午前リハ室",
                start_time="08:30",
                end_time="12:30",
                skill_score=110,
                employee=sample_employees[3],
                time_slot=sample_time_slots[0],
            ),
            GeneratedShift(
                date="2025-12-08",
                time_slot_id="mon_am_reha",
                employee_id=5,
                employee_name="職員D2",
                time_slot_name="月曜午前リハ室",
                start_time="08:30",
                end_time="12:30",
                skill_score=115,
                employee=type_d_only_emp,
                time_slot=sample_time_slots[0],
            ),
        ]
        
        result = _evaluate_part_time_rule(shifts, sample_time_slots)
        assert result is not None
        assert result.code == "part_time_rule"

    def test_no_issue_non_reha_area(self, sample_employees, sample_time_slots):
        """No rule check for non-rehab areas."""
        from src.shift_scheduler.models import GeneratedShift
        
        shifts = [
            GeneratedShift(
                date="2025-12-08",
                time_slot_id="mon_am_reception",
                employee_id=1,
                employee_name="職員A",
                time_slot_name="月曜午前受付",
                start_time="08:30",
                end_time="12:30",
                skill_score=130,
                employee=sample_employees[0],
                time_slot=sample_time_slots[1],
            ),
        ]
        
        result = _evaluate_part_time_rule(shifts, sample_time_slots)
        assert result is None


class TestShiftGeneration:
    """Test main shift generation function."""

    def test_generate_shifts_no_employees(self, sample_time_slots):
        """Raise error when no employees."""
        with pytest.raises(ShiftGenerationError) as exc_info:
            generate_shifts([], sample_time_slots, "2025-12-08", "2025-12-08")
        assert exc_info.value.issue.code == "no_employees"

    def test_generate_shifts_no_time_slots(self, sample_employees):
        """Raise error when no time slots."""
        with pytest.raises(ShiftGenerationError) as exc_info:
            generate_shifts(sample_employees, [], "2025-12-08", "2025-12-08")
        assert exc_info.value.issue.code == "no_time_slots"

    def test_generate_shifts_invalid_date_range(self, sample_employees, sample_time_slots):
        """Raise error when end date before start date."""
        with pytest.raises(ShiftGenerationError) as exc_info:
            generate_shifts(sample_employees, sample_time_slots, "2025-12-10", "2025-12-08")
        assert exc_info.value.issue.code == "invalid_range"


class TestSkillBalance:
    """Test skill balance calculation."""

    def test_calculate_skill_balance_empty(self):
        """Test balance calculation with empty shifts."""
        result = calculate_skill_balance([], [])
        assert result["avg_skill"] == 0.0
        assert result["std_skill"] == 0.0

    def test_calculate_skill_balance_single_shift(self, sample_employees, sample_time_slots):
        """Test balance calculation with single shift."""
        from src.shift_scheduler.models import GeneratedShift
        
        shifts = [
            GeneratedShift(
                date="2025-12-08",
                time_slot_id="mon_am_reha",
                employee_id=1,
                employee_name="職員A",
                time_slot_name="月曜午前リハ室",
                start_time="08:30",
                end_time="12:30",
                skill_score=140,
                employee=sample_employees[0],
                time_slot=sample_time_slots[0],
            ),
        ]
        
        result = calculate_skill_balance(shifts, sample_time_slots)
        assert result["avg_skill"] == 140.0
        assert result["min_skill"] == 140.0
        assert result["max_skill"] == 140.0
        assert result["std_skill"] == 0.0

    def test_calculate_skill_balance_multiple_shifts(self, sample_employees, sample_time_slots):
        """Test balance calculation with multiple shifts."""
        from src.shift_scheduler.models import GeneratedShift
        
        shifts = [
            GeneratedShift(
                date="2025-12-08",
                time_slot_id="mon_am_reha",
                employee_id=1,
                employee_name="職員A",
                time_slot_name="月曜午前リハ室",
                start_time="08:30",
                end_time="12:30",
                skill_score=140,
                employee=sample_employees[0],
                time_slot=sample_time_slots[0],
            ),
            GeneratedShift(
                date="2025-12-08",
                time_slot_id="mon_am_reha",
                employee_id=3,
                employee_name="職員C",
                time_slot_name="月曜午前リハ室",
                start_time="08:30",
                end_time="12:30",
                skill_score=130,
                employee=sample_employees[2],
                time_slot=sample_time_slots[0],
            ),
        ]
        
        result = calculate_skill_balance(shifts, sample_time_slots)
        assert result["avg_skill"] == 270.0  # 140 + 130
        assert result["min_skill"] == 270.0
        assert result["max_skill"] == 270.0
