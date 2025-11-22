#!/usr/bin/env python3
"""
Calendar Data Models
Data classes for rescue squad scheduling system.
"""

from dataclasses import dataclass, field, asdict
from datetime import time
from typing import List, Optional, Dict, Any
import json


@dataclass
class Squad:
    """Represents a rescue squad with ID and assigned territories."""
    id: int
    territories: List[int] = field(default_factory=list)
    active: bool = True  # False means "No Crew" - squad is listed but not active
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'territories': self.territories,
            'active': self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Squad':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            territories=data.get('territories', []),
            active=data.get('active', True)
        )
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Squad':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ShiftSegment:
    """Represents a segment of a shift with specific squads assigned."""
    start_time: time
    end_time: time
    squads: List[Squad]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'squads': [squad.to_dict() for squad in self.squads]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ShiftSegment':
        """Create from dictionary."""
        start_parts = data['start_time'].split(':')
        end_parts = data['end_time'].split(':')
        return cls(
            start_time=time(int(start_parts[0]), int(start_parts[1])),
            end_time=time(int(end_parts[0]), int(end_parts[1])),
            squads=[Squad.from_dict(s) for s in data['squads']]
        )
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ShiftSegment':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Shift:
    """Represents a complete shift with name, times, segments, and tango designation."""
    name: str
    start_time: time
    end_time: time
    segments: List[ShiftSegment] = field(default_factory=list)
    tango: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'segments': [seg.to_dict() for seg in self.segments],
            'tango': self.tango
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Shift':
        """Create from dictionary."""
        start_parts = data['start_time'].split(':')
        end_parts = data['end_time'].split(':')
        return cls(
            name=data['name'],
            start_time=time(int(start_parts[0]), int(start_parts[1])),
            end_time=time(int(end_parts[0]), int(end_parts[1])),
            segments=[ShiftSegment.from_dict(s) for s in data.get('segments', [])],
            tango=data.get('tango')
        )
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Shift':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class DaySchedule:
    """Represents a full day's schedule with all shifts."""
    day: str
    shifts: List[Shift] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'day': self.day,
            'shifts': [shift.to_dict() for shift in self.shifts]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DaySchedule':
        """Create from dictionary."""
        return cls(
            day=data['day'],
            shifts=[Shift.from_dict(s) for s in data.get('shifts', [])]
        )
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DaySchedule':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class WeekSchedule:
    """Represents a week's schedule."""
    week_number: int
    days: List[DaySchedule] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'week_number': self.week_number,
            'days': [day.to_dict() for day in self.days]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WeekSchedule':
        """Create from dictionary."""
        return cls(
            week_number=data['week_number'],
            days=[DaySchedule.from_dict(d) for d in data.get('days', [])]
        )
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WeekSchedule':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))
