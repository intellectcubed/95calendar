# CLI: get-schedule Command

## Overview

The `get-schedule` command retrieves and displays the current schedule for a specific date from Google Sheets.

## Usage

```bash
python man_update_calendar.py get-schedule --date YYYYMMDD
```

### Parameters

- `--date`: Date in YYYYMMDD format (required)
  - Example: `20260110` for January 10, 2026

### Flags

- `--prod`: Use production calendar (optional, default: testing mode)

## Examples

### Get Schedule (Testing Mode)

```bash
python man_update_calendar.py get-schedule --date 20260110
```

**Output:**
```
Retrieving schedule for January 10, 2026:

✓ Schedule retrieved successfully

Schedule Grid:
  Row 0: ['10', '', '', '']
  Row 1: ['0600 - 1800\n(Tango: 35)', '35\n[All]', '', '']
  Row 2: ['1800 - 0600\n(Tango: 42)', '35\n[34,35,42]', '42\n[43,54]', '']
  Row 3: ['', '', '', '']
  Row 4: ['', '', '', '']
  Row 5: ['', '', '', '']
  Row 6: ['', '', '', '']
  Row 7: ['', '', '', '']
  Row 8: ['', '', '', '']
  Row 9: ['', '', '', '']
```

### Get Schedule (Production Mode)

```bash
python man_update_calendar.py --prod get-schedule --date 20260110
```

## Return Value

The method returns a dictionary:

```python
{
    'success': True,
    'action': 'get_schedule_day',
    'date': '20260110',
    'grid': [
        ['10', '', '', ''],
        ['0600 - 1800\n(Tango: 35)', '35\n[All]', '', ''],
        # ... 8 more rows
    ]
}
```

## Use Cases

### 1. View Current Schedule

```bash
# Check what's currently scheduled for a date
python man_update_calendar.py get-schedule --date 20260110
```

### 2. Before Making Changes

```bash
# View schedule before modifying
python man_update_calendar.py get-schedule --date 20260110

# Make changes
python man_update_calendar.py noCrew --date 20260110 --start 1900 --end 2100 --squad 42

# View schedule after
python man_update_calendar.py get-schedule --date 20260110
```

### 3. Verify Production Schedule

```bash
# Check production calendar
python man_update_calendar.py --prod get-schedule --date 20260110
```

### 4. Compare Testing vs Production

```bash
# Get testing schedule
python man_update_calendar.py get-schedule --date 20260110 > testing_schedule.txt

# Get production schedule
python man_update_calendar.py --prod get-schedule --date 20260110 > prod_schedule.txt

# Compare
diff testing_schedule.txt prod_schedule.txt
```

## Grid Format

The schedule is displayed as a 10x4 grid:

- **Row 0**: Day number and empty cells
- **Row 1+**: Shift information
  - Column 0: Shift time and Tango designation
  - Columns 1-3: Squad information with territories

### Cell Format Examples

**Day Number:**
```
'10'
```

**Shift Time:**
```
'1800 - 0600\n(Tango: 42)'
```

**Squad with Territories:**
```
'35\n[34,35,42]'
```

**Squad with All Territories:**
```
'35\n[All]'
```

**Squad with No Crew:**
```
'35\n[No Crew]'
```

## Error Handling

### Invalid Date Format

```bash
$ python man_update_calendar.py get-schedule --date 2026-01-10

✗ Failed to retrieve schedule
  Error: Invalid date format: ...
```

**Solution:** Use YYYYMMDD format: `20260110`

### Date Not Found

```bash
$ python man_update_calendar.py get-schedule --date 20260199

✗ Failed to retrieve schedule
  Error: Could not retrieve day schedule
```

**Solution:** Verify the date exists in the calendar

### Missing Environment Variables

```bash
$ python man_update_calendar.py get-schedule --date 20260110

❌ Environment Error: SPREADSHEET_ID environment variable is not set.
```

**Solution:** Set `SPREADSHEET_ID` in `.env` file

## Programmatic Usage

You can also use the method directly in Python:

```python
from man_update_calendar import ManualCalendarUpdater

updater = ManualCalendarUpdater(is_prod=False)
result = updater.get_schedule('20260110')

if result['success']:
    for row in result['grid']:
        print(row)
```

## Integration with Other Commands

### Workflow Example

```bash
# 1. Check current schedule
python man_update_calendar.py get-schedule --date 20260110

# 2. Make a change
python man_update_calendar.py noCrew --date 20260110 --start 1900 --end 2100 --squad 42

# 3. Verify the change
python man_update_calendar.py get-schedule --date 20260110

# 4. If needed, revert
python man_update_calendar.py list-backups --date 20260110
python man_update_calendar.py revert --date 20260110 --change-id <snapshot-id>

# 5. Confirm revert
python man_update_calendar.py get-schedule --date 20260110
```

## Notes

- **Read-only**: This command does not modify the schedule
- **No confirmation**: Runs immediately without prompts
- **No backups**: Does not create backup snapshots
- **Fast**: Single API call to Google Sheets
- **Testing by default**: Use `--prod` flag for production calendar
