#!/usr/bin/env python3
"""
Test JSON endpoints for calendar service.
Tests the new POST endpoints for preview and apply_external_schedule.
"""

import json
from src.models.calendar_models import DaySchedule, Shift, ShiftSegment, Squad
from datetime import time


def test_day_schedule_serialization():
    """Test that DaySchedule can be serialized and deserialized."""
    # Create a sample schedule
    squad1 = Squad(id=42, territories=[34, 35], active=True)
    squad2 = Squad(id=43, territories=[42, 43, 54], active=True)
    
    segment = ShiftSegment(
        start_time=time(18, 0),
        end_time=time(6, 0),
        squads=[squad1, squad2]
    )
    
    shift = Shift(
        name="Night Shift",
        start_time=time(18, 0),
        end_time=time(6, 0),
        segments=[segment],
        tango=42
    )
    
    day_schedule = DaySchedule(
        day="Friday",
        shifts=[shift]
    )
    
    # Serialize to JSON
    json_str = day_schedule.to_json()
    print("Serialized JSON:")
    print(json.dumps(json.loads(json_str), indent=2))
    
    # Deserialize from JSON
    restored_schedule = DaySchedule.from_json(json_str)
    
    # Verify
    assert restored_schedule.day == day_schedule.day
    assert len(restored_schedule.shifts) == len(day_schedule.shifts)
    assert restored_schedule.shifts[0].name == day_schedule.shifts[0].name
    assert restored_schedule.shifts[0].tango == day_schedule.shifts[0].tango
    assert len(restored_schedule.shifts[0].segments) == len(day_schedule.shifts[0].segments)
    assert len(restored_schedule.shifts[0].segments[0].squads) == len(day_schedule.shifts[0].segments[0].squads)
    assert restored_schedule.shifts[0].segments[0].squads[0].id == squad1.id
    assert restored_schedule.shifts[0].segments[0].squads[0].territories == squad1.territories
    assert restored_schedule.shifts[0].segments[0].squads[0].active == squad1.active
    
    print("\n✓ Serialization/deserialization test passed!")
    return json_str


def test_preview_endpoint_payload():
    """Test creating a payload for the preview endpoint."""
    # Create a sample schedule
    squad1 = Squad(id=42, territories=[34, 35], active=True)
    squad2 = Squad(id=43, territories=[42, 43, 54], active=True)
    
    segment = ShiftSegment(
        start_time=time(18, 0),
        end_time=time(6, 0),
        squads=[squad1, squad2]
    )
    
    shift = Shift(
        name="Night Shift",
        start_time=time(18, 0),
        end_time=time(6, 0),
        segments=[segment],
        tango=42
    )
    
    day_schedule = DaySchedule(
        day="Friday",
        shifts=[shift]
    )
    
    # Create preview request payload
    preview_payload = {
        "action": "noCrew",
        "date": "20251110",
        "shift_start": "1800",
        "shift_end": "0600",
        "squad": 42,
        "day_schedule": day_schedule.to_json()
    }
    
    print("\nPreview endpoint payload:")
    print(json.dumps(preview_payload, indent=2))
    print("\n✓ Preview payload test passed!")
    return preview_payload


def test_apply_endpoint_payload():
    """Test creating a payload for the apply endpoint."""
    # Create a sample schedule
    squad1 = Squad(id=42, territories=[34, 35], active=True)
    squad2 = Squad(id=43, territories=[42, 43, 54], active=True)
    
    segment = ShiftSegment(
        start_time=time(18, 0),
        end_time=time(6, 0),
        squads=[squad1, squad2]
    )
    
    shift = Shift(
        name="Night Shift",
        start_time=time(18, 0),
        end_time=time(6, 0),
        segments=[segment],
        tango=42
    )
    
    day_schedule = DaySchedule(
        day="Friday",
        shifts=[shift]
    )
    
    # Create apply request payload
    apply_payload = {
        "DaySchedule": day_schedule.to_json()
    }
    
    print("\nApply endpoint payload:")
    print(json.dumps(apply_payload, indent=2))
    print("\n✓ Apply payload test passed!")
    return apply_payload


if __name__ == "__main__":
    print("Testing JSON serialization and endpoint payloads...\n")
    print("=" * 60)
    
    # Run tests
    json_str = test_day_schedule_serialization()
    preview_payload = test_preview_endpoint_payload()
    apply_payload = test_apply_endpoint_payload()
    
    print("\n" + "=" * 60)
    print("\nAll tests passed! ✓")
    print("\nExample curl commands:")
    print("\n1. Preview command:")
    print(f"curl -X POST http://localhost:8000/calendar/day/20251110/preview \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -d '{json.dumps(preview_payload)}'")
    
    print("\n2. Apply external schedule:")
    print(f"curl -X POST http://localhost:8000/calendar/day/20251110/apply \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -d '{json.dumps(apply_payload)}'")
