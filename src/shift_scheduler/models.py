"""Domain model definitions for the shift scheduler application."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(slots=True)
class EmploymentPattern:
    """Represents a pre-defined employment pattern template."""

    id: str
    name: str
    category: str
    start_time: str
    end_time: str
    break_hours: float
    work_hours: float
    can_work_afternoon: bool
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Employee:
    """Represents an employee record."""

    id: int
    name: str
    employee_type: str
    employment_type: str
    employment_pattern_id: Optional[str]
    skill_reha: int
    skill_reception_am: int
    skill_reception_pm: int
    skill_general: int
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Absence:
    """Represents a registered employee absence."""

    id: int
    employee_id: int
    absence_date: str
    absence_type: str
    reason: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TimeSlot:
    """Represents a fixed operational time slot."""

    id: str
    day_of_week: int
    period: str
    start_time: str
    end_time: str
    is_active: bool
    required_staff: int
    area: str
    display_name: str
    skill_weight: float = 1.0
    target_skill_score: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        base = asdict(self)
        base["area_type"] = self.area
        base["time_period"] = "午前" if self.period == "morning" else "午後"
        if self.target_skill_score is None:
            base["target_skill_score"] = self.required_staff * 150
        return base


@dataclass(slots=True)
class Shift:
    """Represents a stored shift assignment."""

    id: int
    date: str
    time_slot_id: str
    employee_id: int
    employee_name: Optional[str] = None
    time_slot_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    skill_score: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BreakSchedule:
    """Represents a break assignment for a shift."""

    id: int
    shift_id: int
    employee_id: int
    date: str
    break_number: int
    break_start_time: str
    break_end_time: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GeneratedShift:
    """Represents a shift proposal produced by the optimiser before persistence."""

    date: str
    time_slot_id: str
    employee_id: int
    employee_name: str
    time_slot_name: str
    start_time: str
    end_time: str
    skill_score: int
    employee: Employee
    time_slot: TimeSlot

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["employee"] = self.employee.to_dict()
        payload["time_slot"] = self.time_slot.to_dict()
        return payload
