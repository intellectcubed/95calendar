# JSON API Documentation

This document describes the JSON-based POST endpoints for the calendar service.

## Overview

The calendar service now supports JSON-based POST endpoints that allow:
1. **Preview Mode**: Test calendar modifications without writing to Google Sheets
2. **Apply External Schedule**: Apply a complete DaySchedule object to the calendar

## Endpoints

### 1. Preview Command

**Endpoint**: `POST /calendar/day/{calendar_date}/preview`

**Purpose**: Preview a calendar command without applying it to Google Sheets. Returns the modified schedule as JSON.

**URL Parameters**:
- `calendar_date`: Date in YYYYMMDD format (e.g., "20251110")

**Request Body**:
```json
{
  "action": "noCrew",
  "date": "20251110",
  "shift_start": "1800",
  "shift_end": "0600",
  "squad": 42,
  "day_schedule": "{\"day\": \"Friday\", \"shifts\": [...]}"
}
```

**Fields**:
- `action` (required): Command action ("noCrew", "addShift", "obliterateShift")
- `date` (required): Date in YYYYMMDD format
- `shift_start` (optional): Start time in HHMM format
- `shift_end` (optional): End time in HHMM format
- `squad` (optional): Squad ID (integer)
- `day_schedule` (required): JSON string of DaySchedule object

**Response**:
```json
{
  "success": true,
  "preview": true,
  "modified_grid": "{\"day\": \"Friday\", \"shifts\": [...]}",
  "action": "noCrew",
  "date": "20251110"
}
```

**Example curl**:
```bash
curl -X POST http://localhost:8000/calendar/day/20251110/preview \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "noCrew",
    "date": "20251110",
    "shift_start": "1800",
    "shift_end": "0600",
    "squad": 42,
    "day_schedule": "{\"day\": \"Friday\", \"shifts\": [...]}"
  }'
```

### 2. Apply External Schedule

**Endpoint**: `POST /calendar/day/{calendar_date}/apply`

**Purpose**: Apply an externally provided DaySchedule to Google Calendar with automatic backup.

**URL Parameters**:
- `calendar_date`: Date in YYYYMMDD format (e.g., "20251110")

**Request Body**:
```json
{
  "DaySchedule": "{\"day\": \"Friday\", \"shifts\": [...]}",
  "commands": "noCrew 1800-2100 squad 42, addShift 0700-0800 squad 54"
}
```

**Fields**:
- `DaySchedule` (required): JSON string of complete DaySchedule object
- `commands` (optional): Description of commands that led to this schedule (stored in backup for audit trail)

**Response**:
```json
{
  "success": true,
  "changeId": "uuid-of-backup",
  "action": "apply_external_schedule",
  "date": "20251110"
}
```

**Example curl**:
```bash
curl -X POST http://localhost:8000/calendar/day/20251110/apply \
  -H 'Content-Type: application/json' \
  -d '{
    "DaySchedule": "{\"day\": \"Friday\", \"shifts\": [...]}",
    "commands": "noCrew 1800-2100 squad 42"
  }'
```

## DaySchedule JSON Format

The DaySchedule object has the following structure:

```json
{
  "day": "Friday",
  "shifts": [
    {
      "name": "Night Shift",
      "start_time": "18:00",
      "end_time": "06:00",
      "segments": [
        {
          "start_time": "18:00",
          "end_time": "06:00",
          "squads": [
            {
              "id": 42,
              "territories": [34, 35],
              "active": true
            },
            {
              "id": 43,
              "territories": [42, 43, 54],
              "active": true
            }
          ]
        }
      ],
      "tango": 42
    }
  ]
}
```

### DaySchedule Fields

- `day` (string): Day name (e.g., "Friday", "Saturday")
- `shifts` (array): List of Shift objects

### Shift Fields

- `name` (string): Shift name (e.g., "Day Shift", "Night Shift")
- `start_time` (string): Start time in HH:MM format (24-hour)
- `end_time` (string): End time in HH:MM format (24-hour)
- `segments` (array): List of ShiftSegment objects
- `tango` (integer or null): Squad ID designated as tango

### ShiftSegment Fields

- `start_time` (string): Segment start time in HH:MM format
- `end_time` (string): Segment end time in HH:MM format
- `squads` (array): List of Squad objects

### Squad Fields

- `id` (integer): Squad ID (e.g., 34, 35, 42, 43, 54)
- `territories` (array): List of territory IDs assigned to this squad
- `active` (boolean): Whether squad is active (false means "No Crew")

## Workflow Examples

### Example 1: Preview a Change

1. Get current schedule:
```bash
curl "http://localhost:8000/?action=get_schedule_day&date=20251110"
```

2. Preview modification:
```bash
curl -X POST http://localhost:8000/calendar/day/20251110/preview \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "noCrew",
    "date": "20251110",
    "shift_start": "1800",
    "shift_end": "2100",
    "squad": 42,
    "day_schedule": "<current_schedule_json>"
  }'
```

3. Review the `modified_grid` in the response

4. If satisfied, apply using the regular endpoint with `preview=false`

### Example 2: Apply External Schedule

1. Create or modify a DaySchedule object in your application

2. Serialize to JSON:
```python
from calendar_models import DaySchedule
schedule_json = day_schedule.to_json()
```

3. Apply to calendar:
```bash
curl -X POST http://localhost:8000/calendar/day/20251110/apply \
  -H 'Content-Type: application/json' \
  -d "{\"DaySchedule\": \"$schedule_json\", \"commands\": \"Custom schedule modification\"}"
```

4. A backup is automatically created with the returned `changeId`

5. If needed, rollback using:
```bash
curl "http://localhost:8000/?action=rollback&date=20251110&change_id=<changeId>"
```

## Python Client Example

```python
import requests
import json
from calendar_models import DaySchedule

# Get current schedule
response = requests.get(
    "http://localhost:8000/",
    params={"action": "get_schedule_day", "date": "20251110"}
)
current_grid = response.json()["grid"]

# Parse to DaySchedule (you'll need to implement grid parsing)
# For this example, assume we have a DaySchedule object
day_schedule = parse_grid_to_schedule(current_grid)

# Preview a change
preview_response = requests.post(
    "http://localhost:8000/calendar/day/20251110/preview",
    json={
        "action": "noCrew",
        "date": "20251110",
        "shift_start": "1800",
        "shift_end": "2100",
        "squad": 42,
        "day_schedule": day_schedule.to_json()
    }
)

# Check preview result
if preview_response.json()["success"]:
    modified_schedule_json = preview_response.json()["modified_grid"]
    modified_schedule = DaySchedule.from_json(modified_schedule_json)
    print("Preview successful!")
    
    # Apply the modified schedule
    apply_response = requests.post(
        "http://localhost:8000/calendar/day/20251110/apply",
        json={
            "DaySchedule": modified_schedule_json,
            "commands": "noCrew 1800-2100 squad 42"
        }
    )
    
    if apply_response.json()["success"]:
        change_id = apply_response.json()["changeId"]
        print(f"Applied successfully! Backup ID: {change_id}")
```

## Error Handling

All endpoints return a JSON response with a `success` field:

**Success Response**:
```json
{
  "success": true,
  ...
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

Common errors:
- Missing required parameters
- Invalid date format
- Invalid JSON in DaySchedule
- Google Sheets API errors
- Backup system errors

## Testing

Run the test suite to verify JSON serialization:

```bash
python3 test_json_endpoints.py
```

This will test:
- DaySchedule serialization/deserialization
- Preview endpoint payload format
- Apply endpoint payload format
- Example curl commands
