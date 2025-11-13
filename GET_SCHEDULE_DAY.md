# get_schedule_day Command

## Overview

The `get_schedule_day` action retrieves a day's schedule from Google Sheets and returns it formatted as a 10x4 grid, ready for display or comparison.

## Command Format

```
/?action=get_schedule_day&date=YYYYMMDD
```

**Parameters:**
- `action`: Must be `get_schedule_day`
- `date`: Date in YYYYMMDD format (e.g., "20260110")

## Usage

### Basic Usage

```python
from calendar_commands import CalendarCommands

commands = CalendarCommands(spreadsheet_id='your-id')

# Get schedule for January 10, 2026
result = commands.execute_command('/?action=get_schedule_day&date=20260110')

if result['success']:
    print(f"Schedule for {result['date']}:")
    for row in result['grid']:
        print(row)
else:
    print(f"Error: {result['error']}")
```

## Return Value

### Success Response

```python
{
    'success': True,
    'action': 'get_schedule_day',
    'date': '20260110',
    'grid': [
        ['10', '', '', ''],                                    # Row 0: Day number
        ['0600 - 1800\n(Tango: 35)', '35\n[All]', '', ''],   # Row 1: Day shift
        ['1800 - 0600\n(Tango: 42)', '35\n[34,35]', '42\n[43,54]', ''],  # Row 2: Night shift
        ['', '', '', ''],                                      # Row 3-9: Empty
        ['', '', '', ''],
        ['', '', '', ''],
        ['', '', '', ''],
        ['', '', '', ''],
        ['', '', '', ''],
        ['', '', '', '']
    ]
}
```

### Error Response

```python
{
    'success': False,
    'error': 'Could not retrieve day schedule'
}
```

## Grid Format

The grid is a 10x4 list of lists:
- **10 rows**: Matches the Google Sheets day cell height
- **4 columns**: Matches the Google Sheets day cell width
- **Row 0, Col 0**: Day number (e.g., "10")
- **Row 1+**: Shift information with squads and territories

### Cell Format Examples

**Day Number (0,0):**
```
"10"
```

**Shift with Tango (1,0):**
```
"1800 - 0600\n(Tango: 42)"
```

**Squad with Territories (1,1):**
```
"35\n[34,35,42]"
```

**Squad with All Territories (1,1):**
```
"35\n[All]"
```

**Squad with No Crew (1,1):**
```
"35\n[No Crew]"
```

## Use Cases

### 1. Display Current Schedule

```python
result = commands.execute_command('/?action=get_schedule_day&date='20260110')
if result['success']:
    print("Current Schedule:")
    for i, row in enumerate(result['grid']):
        print(f"Row {i}: {row}")
```

### 2. Compare Before/After

```python
# Get current schedule
before = commands.execute_command('/?action=get_schedule_day&date='20260110')

# Preview changes
preview = commands.execute_command(
    '/?action=noCrew&date=20260110&shift_start=1900&shift_end=2100&squad=42',
    preview=True
)

# Compare
print("Before:", before['grid'])
print("After:", preview['modified_grid'])
```

### 3. Validate Schedule

```python
result = commands.execute_command('/?action=get_schedule_day&date='20260110')
if result['success']:
    grid = result['grid']
    
    # Check if day has any shifts
    has_shifts = any(row[0] for row in grid[1:])
    
    # Check for No Crew
    has_no_crew = any('[No Crew]' in str(cell) for row in grid for cell in row)
    
    print(f"Has shifts: {has_shifts}")
    print(f"Has No Crew: {has_no_crew}")
```

### 4. Export Schedule

```python
import csv

result = commands.execute_command('/?action=get_schedule_day&date='20260110')
if result['success']:
    # Write to CSV file
    with open('schedule_20260110.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(result['grid'])
    print("Schedule exported to schedule_20260110.csv")
```

## Error Handling

```python
result = commands.execute_command('/?action=get_schedule_day&date='20260110')

if not result['success']:
    error = result['error']
    
    if 'Invalid date format' in error:
        print("Please use YYYYMMDD format")
    elif 'Could not retrieve' in error:
        print("Day not found in calendar")
    else:
        print(f"Unexpected error: {error}")
```

## Integration with Other Methods

### With Preview Mode

```python
# Get current schedule
current = commands.execute_command('/?action=get_schedule_day&date='20260110')

# Preview changes
preview = commands.execute_command(
    '/?action=noCrew&date=20260110&shift_start=1900&shift_end=2100&squad=42',
    preview=True
)

# Show comparison
print("Current:", current['grid'][1])  # First shift row
print("Preview:", preview['modified_grid'][1])  # First shift row after change
```

### With Execute Mode

```python
# Get schedule before
before = commands.execute_command('/?action=get_schedule_day&date='20260110')

# Execute change
result = commands.execute_command(
    '/?action=noCrew&date=20260110&shift_start=1900&shift_end=2100&squad=42',
    preview=False
)

# Get schedule after
after = commands.execute_command('/?action=get_schedule_day&date='20260110')

# Verify change was applied
print("Before:", before['grid'])
print("After:", after['grid'])
print("Backup ID:", result['changeId'])
```

## Notes

- **Date Format**: Must be YYYYMMDD (e.g., "20260110" for January 10, 2026)
- **Tab Selection**: Automatically determines the correct tab based on date
- **Testing Mode**: Respects `testing` and `live_test` flags from initialization
- **Grid Format**: Same format as `format_day()` output from ScheduleFormatter
- **No Side Effects**: Read-only operation, doesn't modify anything

## Performance

- **Single API Call**: Makes one call to Google Sheets API
- **Cached**: Not cached - always fetches fresh data
- **Rate Limits**: Subject to Google Sheets API rate limits (handled with retry logic)
