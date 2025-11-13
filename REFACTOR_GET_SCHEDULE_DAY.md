# Refactor: get_schedule_day Command

## Summary

Refactored the schedule retrieval functionality to follow proper naming conventions and integrate with the command system.

## Changes Made

### 1. Removed Standalone Method

**Before:**
```python
def getScheduleDay(self, date_str: str) -> Dict:
    # Standalone method with camelCase name
```

**After:**
```python
# Integrated into execute_command as an action
```

### 2. Added as Command Action

The `get_schedule_day` action is now handled by `execute_command`:

```python
if action == 'get_schedule_day':
    grid = self.formatter.format_day(day_schedule)
    return {
        'success': True,
        'action': 'get_schedule_day',
        'date': date_str,
        'grid': grid
    }
```

### 3. Updated Usage

**Before (camelCase method):**
```python
result = commands.getScheduleDay('20260110')
```

**After (command action):**
```python
result = commands.execute_command('/?action=get_schedule_day&date=20260110')
```

## Benefits

1. **Consistent Naming**: Uses snake_case like other Python methods
2. **Unified Interface**: All operations go through `execute_command`
3. **URL-based**: Follows the same pattern as other commands
4. **Extensible**: Easy to add more read-only commands in the future

## Command Format

```
/?action=get_schedule_day&date=YYYYMMDD
```

**Parameters:**
- `action`: Must be `get_schedule_day`
- `date`: Date in YYYYMMDD format (required)

**Note:** This command does not use `shift_start`, `shift_end`, or `squad` parameters.

## Response Format

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

## Behavior

- **Read-only**: Does not modify the schedule
- **No backup**: Does not create a backup snapshot
- **Returns immediately**: Exits before modification logic
- **Ignores preview flag**: Always returns the grid (read-only operation)

## Examples

### Get Current Schedule

```python
result = commands.execute_command('/?action=get_schedule_day&date=20260110')
if result['success']:
    print(result['grid'])
```

### Compare Before/After

```python
# Get current
before = commands.execute_command('/?action=get_schedule_day&date=20260110')

# Preview change
preview = commands.execute_command(
    '/?action=noCrew&date=20260110&shift_start=1900&shift_end=2100&squad=42',
    preview=True
)

# Compare
print("Before:", before['grid'])
print("After:", preview['modified_grid'])
```

### Execute and Verify

```python
# Get before
before = commands.execute_command('/?action=get_schedule_day&date=20260110')

# Execute change
commands.execute_command(
    '/?action=noCrew&date=20260110&shift_start=1900&shift_end=2100&squad=42',
    preview=False
)

# Get after
after = commands.execute_command('/?action=get_schedule_day&date=20260110')

# Verify
assert before['grid'] != after['grid']
```

## Migration Guide

If you were using the old `getScheduleDay` method:

**Old Code:**
```python
result = commands.getScheduleDay('20260110')
```

**New Code:**
```python
result = commands.execute_command('/?action=get_schedule_day&date=20260110')
```

The response format is the same, so no other changes are needed.

## Documentation Updated

- `PREVIEW_MODE.md`: Updated examples to use new command format
- `GET_SCHEDULE_DAY.md`: Completely updated to reflect command-based approach
- `calendar_commands.py`: Updated example usage at bottom of file
