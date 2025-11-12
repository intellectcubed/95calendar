#!/usr/bin/env python3
"""
Calendar Data Models
Data classes for rescue squad scheduling system.
"""

from dataclasses import dataclass, field
from datetime import time
from typing import List, Optional


@dataclass
class Squad:
    """Represents a rescue squad with ID and assigned territories."""
    id: int
    territories: List[int] = field(default_factory=list)
    active: bool = True  # False means "No Crew" - squad is listed but not active


@dataclass
class ShiftSegment:
    """Represents a segment of a shift with specific squads assigned."""
    start_time: time
    end_time: time
    squads: List[Squad]


@dataclass
class Shift:
    """Represents a complete shift with name, times, segments, and tango designation."""
    name: str
    start_time: time
    end_time: time
    segments: List[ShiftSegment] = field(default_factory=list)
    tango: Optional[int] = None


@dataclass
class DaySchedule:
    """Represents a full day's schedule with all shifts."""
    day: str
    shifts: List[Shift] = field(default_factory=list)


@dataclass
class WeekSchedule:
    """Represents a week's schedule."""
    week_number: int
    days: List[DaySchedule] = field(default_factory=list)
