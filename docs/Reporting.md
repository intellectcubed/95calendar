# Solo Squad Report

## Overview

The Solo Squad Report identifies time slots where only one squad was actively on duty — a critical safety/staffing metric. It scans historical schedule data from Google Sheets and produces a formatted report grouped by month.

A shift segment is considered "solo coverage" when exactly one squad has `active=True`. A segment with two squads where one is marked No Crew (active=False) counts as solo.

## Usage

```bash
PYTHONPATH=. python scripts/solo_squad_report.py --months N [--prod] [--include-current] [--delay SECONDS] [--env-file PATH]
```

### Parameters

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--months N` | Yes | — | Number of past months to scan (backward from current month, not including current month) |
| `--prod` | No | Testing mode | Use production data; without this flag, queries hit the Testing tab |
| `--include-current` | No | Off | Include the current (partial) month up to today |
| `--delay SECONDS` | No | `1.0` | Seconds between API calls to avoid Google Sheets rate limits |
| `--env-file PATH` | No | `.env` | Path to env file |

## Examples

### Scan Last 6 Months (Production)

```bash
PYTHONPATH=. python scripts/solo_squad_report.py --months 6 --prod
```

### Scan Last Month Only

```bash
PYTHONPATH=. python scripts/solo_squad_report.py --months 1 --prod
```

### Include Current Partial Month

```bash
PYTHONPATH=. python scripts/solo_squad_report.py --months 3 --prod --include-current
```

### Save Report to File

```bash
PYTHONPATH=. python scripts/solo_squad_report.py --months 6 --prod > solo_report.txt
```

Progress output goes to stderr, so the file will contain only the clean report.

### Faster Scanning

```bash
PYTHONPATH=. python scripts/solo_squad_report.py --months 1 --prod --delay 0.5
```

## Output Format

```
Solo Squad Report
=================
Period: August 2025 - January 2026
Generated: 2026-02-12

--- January 2026 (4 solo segments) ---
  Date            Shift                 Time Slot          Solo Squad
  ----------      --------------------  -----------------  ----------
  Jan 04 (Sat)    Night Shift           18:00 - 06:00      Squad 42
  Jan 10 (Fri)    Night Shift           18:00 - 06:00      Squad 42
  ...

--- December 2025 (2 solo segments) ---
  ...

Summary
-------
Total solo segments: 22
Months scanned: 6

Solo frequency by squad:
  Squad 42: 8 times
  Squad 35: 6 times
  ...
```

## How It Works

For each day in the requested month range:

1. Calls `CalendarCommands.execute_command(action='get_schedule_day', date=YYYYMMDD)`
2. Parses the returned `DaySchedule` JSON
3. For each shift segment, counts squads where `squad.active == True`
4. If exactly 1 active squad, records it as a "solo" segment
5. Groups results by month and prints the formatted report with summary

## Performance

- Each day requires one Google Sheets API call
- Default delay between calls is 1 second to stay within rate limits
- 6 months (~180 days) takes approximately 3 minutes
- Use `--delay 0.5` for faster scans if rate limits allow

## Error Handling

- Days where schedule retrieval fails are skipped with a warning to stderr
- Missing `.env` or `SPREADSHEET_ID` exits with a clear error message
- `Ctrl+C` interrupts the scan cleanly

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SPREADSHEET_ID` | Yes | The Google Spreadsheet ID to read schedule data from |

Set in `.env` file or export directly:

```bash
export SPREADSHEET_ID='your-spreadsheet-id'
```
