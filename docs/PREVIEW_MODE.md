# Preview Mode for Calendar Commands

## Overview

The `execute_command` method now supports a **preview mode** that allows you to see what changes will be made without actually writing to Google Sheets.

## Usage

### Preview Mode (Default)

```python
from calendar_commands import CalendarCommands

commands = CalendarCommands(spreadsheet_id='your-id')

# Preview mode - returns modified grid without writing
result = commands.execute_command(
    action='noCrew',
    date='20260110',
    shift_start='1900',
    shift_end='2100',
    squad=42,
    preview=True  # Default
)

print(result['preview'])  # True
print(result['modified_grid'])  # 10x4 grid showing the changes
```

### Execute Mode (Write to Sheets)

```python
# Execute mode - writes changes to Google Sheets
result = commands.execute_command(
    action='noCrew',
    date='20260110',
    shift_start='1900',
    shift_end='2100',
    squad=42,
    preview=False
)

print(result['success'])  # True/False
print(result['changeId'])  # Backup snapshot ID
```

## Return Values

### Preview Mode Response

```python
{
    'success': True,
    'preview': True,
    'modified_grid': [
        ['8', '', '', ''],
        ['1800 - 0600\n(Tango: 35)', '35\n[34,35,42]', '42\n[43,54]', ''],
        # ... 8 more rows (10 total)
    ],
    'action': 'noCrew',
    'date': '20260110'
}
```

### Execute Mode Response

```python
{
    'success': True,
    'changeId': 'abc-123-def-456',  # Supabase snapshot ID
    'action': 'noCrew',
    'date': '20260110'
}
```

## Benefits

1. **Test Changes**: See what will happen before committing
2. **Validation**: Verify the command produces expected results
3. **UI Integration**: Display preview to users before applying
4. **Debugging**: Inspect the modified grid structure

## Getting Current Schedule

Use the `get_schedule_day` action to retrieve the current schedule for a day:

```python
# Get current schedule
result = commands.execute_command(
    action='get_schedule_day',
    date='20260110'
)

if result['success']:
    print("Current schedule grid:")
    for row in result['grid']:
        print(row)
else:
    print(f"Error: {result['error']}")
```

**Response:**
```python
{
    'success': True,
    'date': '20260110',
    'grid': [
        ['10', '', '', ''],
        ['0600 - 1800\n(Tango: 35)', '35\n[All]', '', ''],
        ['1800 - 0600\n(Tango: 42)', '35\n[34,35,42]', '42\n[43,54]', ''],
        # ... 7 more rows
    ]
}
```

## Example Workflow

```python
# Step 1: Get current schedule
current = commands.execute_command(
    action='get_schedule_day',
    date='20260110'
)
print("Current schedule:", current['grid'])

# Step 2: Preview the change
preview_result = commands.execute_command(
    action='noCrew',
    date='20260110',
    shift_start='1900',
    shift_end='2100',
    squad=42,
    preview=True
)

# Step 3: Display to user
print("Preview of changes:")
for row in preview_result['modified_grid']:
    print(row)

# Step 4: Confirm with user
confirm = input("Apply these changes? (yes/no): ")

# Step 5: Execute if confirmed
if confirm.lower() == 'yes':
    execute_result = commands.execute_command(
        action='noCrew',
        date='20260110',
        shift_start='1900',
        shift_end='2100',
        squad=42,
        preview=False
    )
    print(f"Changes applied! Backup ID: {execute_result['changeId']}")
```

## CLI Integration

The `man_update_calendar.py` CLI tool always uses `preview=False` to write changes directly:

```bash
# This writes to Google Sheets immediately
python man_update_calendar.py noCrew --date 20260110 --start 1900 --end 2100 --squad 42
```

## Test Integration

Tests use `preview=False` to actually write to the Testing tab:

```python
def test_nocrew_command(commands):
    result = commands.execute_command(
        '/?action=noCrew&date=20260101&shift_start=1900&shift_end=2100&squad=42',
        preview=False  # Actually write to test the full flow
    )
    assert result['success'] == True
```

## Grid Format

The `modified_grid` is a 10x4 list of lists representing the day's schedule:

```python
[
    ['8', '', '', ''],                                    # Row 0: Day number
    ['1800 - 0600\n(Tango: 35)', '35\n[34,35]', ...],   # Row 1: Shift info
    ['', '', '', ''],                                     # Row 2: Empty
    # ... 7 more rows
]
```

Each cell contains formatted text as it would appear in Google Sheets.

## Notes

- **Default is preview=True**: This prevents accidental writes
- **Backups only in execute mode**: Preview mode doesn't create backups
- **No formatting in preview**: Red text formatting is only applied when writing to sheets
- **Grid is ready to display**: The modified_grid can be directly shown to users
