# Calendar Service API

FastAPI service for managing rescue squad shift schedules backed by Google Sheets.

- **Base URL (local)**: `http://localhost:8000`
- **Framework**: FastAPI / Uvicorn
- **Deployment**: Docker or AWS Lambda (via Mangum)

---

## Endpoints

### GET `/health`

Health check for container orchestration.

**Response**
```json
{
  "status": "healthy",
  "service": "calendar-command-service"
}
```

---

### GET `/`

Execute a calendar command via query parameters. Supports preview mode (default) or live writes to Google Sheets.

**Query Parameters**

| Parameter     | Type    | Required | Description |
|---------------|---------|----------|-------------|
| `action`      | string  | yes      | Command to execute (see [Actions](#actions)) |
| `date`        | string  | yes      | Date in `YYYYMMDD` format |
| `shift_start` | string  | no       | Shift start time in `HHMM` format |
| `shift_end`   | string  | no       | Shift end time in `HHMM` format |
| `squad`       | integer | no       | Squad ID (valid: 34, 35, 42, 43, 54) |
| `preview`     | boolean | no       | If `true`, return modified schedule without writing (default: `true`) |
| `change_id`   | string  | no       | Snapshot UUID for `rollback` action |

**Example requests**
```
GET /?action=get_schedule_day&date=20251110
GET /?action=noCrew&date=20251110&shift_start=1800&shift_end=0600&squad=42&preview=false
GET /?action=list_backups&date=20251110
GET /?action=rollback&date=20251110&change_id=<uuid>
```

**Response — live write**
```json
{
  "success": true,
  "action": "noCrew",
  "date": "20251110",
  "changeId": "<uuid>"
}
```

**Response — preview**
```json
{
  "success": true,
  "preview": true,
  "modified_grid": "{...DaySchedule JSON...}",
  "action": "noCrew",
  "date": "20251110"
}
```

**Response — error**
```json
{
  "status": "error",
  "message": "Error description"
}
```

---

### POST `/calendar/day/{calendar_date}/preview`

Preview a command against an existing `DaySchedule` without touching Google Sheets.

**Path Parameters**

| Parameter       | Type   | Description |
|-----------------|--------|-------------|
| `calendar_date` | string | Date in `YYYYMMDD` format |

**Request Body**
```json
{
  "action": "noCrew",
  "date": "20251110",
  "shift_start": "1800",
  "shift_end": "0600",
  "squad": 42,
  "day_schedule": "{...DaySchedule JSON string...}"
}
```

| Field          | Type    | Required | Description |
|----------------|---------|----------|-------------|
| `action`       | string  | yes      | Command to preview |
| `date`         | string  | yes      | `YYYYMMDD` |
| `shift_start`  | string  | no       | `HHMM` |
| `shift_end`    | string  | no       | `HHMM` |
| `squad`        | integer | no       | Squad ID |
| `day_schedule` | string  | yes      | JSON-serialized `DaySchedule` |

**Response — success**
```json
{
  "success": true,
  "preview": true,
  "modified_grid": "{...DaySchedule JSON string...}",
  "action": "noCrew",
  "date": "20251110"
}
```

**Response — error**
```json
{
  "success": false,
  "error": "Error message"
}
```

---

### POST `/calendar/day/{calendar_date}/apply`

Apply an externally provided `DaySchedule` directly to the calendar. Creates a backup snapshot automatically.

**Path Parameters**

| Parameter       | Type   | Description |
|-----------------|--------|-------------|
| `calendar_date` | string | Date in `YYYYMMDD` format |

**Request Body**
```json
{
  "DaySchedule": "{...DaySchedule JSON string...}",
  "commands": "noCrew 1800-2100 squad 42, addShift 0700-0800 squad 54"
}
```

| Field         | Type   | Required | Description |
|---------------|--------|----------|-------------|
| `DaySchedule` | string | yes      | JSON-serialized `DaySchedule` |
| `commands`    | string | no       | Free-text description for the audit trail |

**Response — success**
```json
{
  "success": true,
  "changeId": "<uuid>",
  "action": "apply_external_schedule",
  "date": "20251110"
}
```

**Response — error**
```json
{
  "success": false,
  "error": "Failed to apply external schedule: ..."
}
```

---

## Actions

| Action                    | Params required                                 | Writes | Description |
|---------------------------|-------------------------------------------------|--------|-------------|
| `get_schedule_day`        | `date`                                          | no     | Return current `DaySchedule` |
| `noCrew`                  | `date`, `shift_start`, `shift_end`, `squad`     | yes    | Mark squad inactive (No Crew) for the given hours |
| `addShift`                | `date`, `shift_start`, `shift_end`, `squad`     | yes    | Add or reactivate a squad for the given hours |
| `obliterateShift`         | `date`, `shift_start`, `shift_end`, `squad`     | yes    | Completely remove a squad's shift |
| `list_backups`            | `date`                                          | no     | List backup snapshots for the date |
| `rollback`                | `date`, `change_id`                             | yes    | Restore from a backup snapshot |
| `apply_external_schedule` | `date`, `external_mod_day_schedule`             | yes    | Apply an external `DaySchedule` with optional audit note |

---

## Data Models

### DaySchedule

```json
{
  "day": "Friday",
  "shifts": [ ]
}
```

### Shift

```json
{
  "name": "Night Shift",
  "start_time": "18:00",
  "end_time": "06:00",
  "segments": [ ],
  "tango": 42
}
```

| Field        | Type    | Description |
|--------------|---------|-------------|
| `name`       | string  | Human-readable shift name |
| `start_time` | string  | 24-hour `HH:MM` |
| `end_time`   | string  | 24-hour `HH:MM` |
| `segments`   | array   | Time segments within the shift |
| `tango`      | integer | Squad ID designated as tango lead |

### ShiftSegment

```json
{
  "start_time": "18:00",
  "end_time": "21:00",
  "squads": [ ]
}
```

### Squad

```json
{
  "id": 42,
  "territories": [34, 35],
  "active": true
}
```

| Field         | Type    | Description |
|---------------|---------|-------------|
| `id`          | integer | Squad ID — valid values: 34, 35, 42, 43, 54 |
| `territories` | array   | Territory IDs assigned to this squad |
| `active`      | boolean | `false` = No Crew |

---

## Environment Variables

| Variable              | Required           | Description |
|-----------------------|--------------------|-------------|
| `ENVIRONMENT`         | no (default: test) | `test` or `production` |
| `TEST_SPREADSHEET_ID` | yes                | Google Spreadsheet ID for test |
| `PROD_SPREADSHEET_ID` | if production      | Google Spreadsheet ID for production |
| `TEST_SUPABASE_URL`   | yes                | Supabase URL for test backups |
| `TEST_SUPABASE_KEY`   | yes                | Supabase API key for test |
| `PROD_SUPABASE_URL`   | if production      | Supabase URL for production |
| `PROD_SUPABASE_KEY`   | if production      | Supabase API key for production |

Credentials are loaded from AWS Secrets Manager when running in Lambda, otherwise from environment variables or a local `.env` file.

---

## Notes

- All modification actions default to `preview=true` — pass `preview=false` to commit changes to Google Sheets.
- Every live write creates a Supabase backup snapshot before modifying the sheet.
- CORS is currently open (`*`); restrict `allow_origins` for production deployments.
