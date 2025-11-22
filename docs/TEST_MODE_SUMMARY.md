# Test Mode: Backup System Disabled

## Summary

The backup system is now automatically disabled when `CalendarCommands` is initialized with `live_test=True`. This prevents unit tests from requiring Supabase credentials and keeps test data out of the production backup database.

## Implementation

### Changes in `calendar_commands.py`

#### 1. Conditional Backup Manager Initialization

```python
def __init__(self, ..., live_test: bool = False, ...):
    # ...
    if not live_test:
        self.backup_manager = ChangeBackupManager(default_ttl_days=backup_ttl_days)
    else:
        self.backup_manager = None  # Disabled in test mode
```

#### 2. Skip Backup Creation in `execute_command`

```python
def execute_command(self, command_url: str) -> Dict:
    # ...
    backup_id = None
    if not self.live_test:
        # Save backup only in production mode
        backup_id = self.backup_manager.save_grid(...)
    # ...
```

#### 3. Guard `list_backups` Method

```python
def list_backups(self, date_str: str) -> List[Dict]:
    if self.live_test or not self.backup_manager:
        return []
    return self.backup_manager.list_snapshots(date_str)
```

#### 4. Guard `rollback` Method

```python
def rollback(self, change_id: str, date_str: str) -> Dict:
    if self.live_test or not self.backup_manager:
        return {
            'success': False,
            'error': 'Rollback not available in test mode'
        }
    # ... rest of rollback logic
```

## Behavior Comparison

### Production Mode (`live_test=False`)

```python
commands = CalendarCommands(spreadsheet_id='...', live_test=False)

# Backup created ✓
result = commands.execute_command('/?action=noCrew&...')
print(result['changeId'])  # UUID from Supabase

# Lists backups ✓
backups = commands.list_backups('20260110')
print(len(backups))  # > 0

# Rollback works ✓
result = commands.rollback(change_id, '20260110')
print(result['success'])  # True
```

### Test Mode (`live_test=True`)

```python
commands = CalendarCommands(spreadsheet_id='...', live_test=True)

# NO backup created ✗
result = commands.execute_command('/?action=noCrew&...')
print(result['changeId'])  # None

# Returns empty list ✗
backups = commands.list_backups('20260110')
print(len(backups))  # 0

# Rollback disabled ✗
result = commands.rollback(change_id, '20260110')
print(result['error'])  # "Rollback not available in test mode"
```

## Benefits

1. **No Supabase Required for Tests**: Unit tests can run without Supabase credentials
2. **Clean Test Database**: Test data doesn't pollute production backups
3. **Faster Tests**: No backup overhead during test execution
4. **Explicit Behavior**: Clear separation between test and production modes

## Testing

### Unit Test Example

```python
def test_nocrew_command():
    # Initialize in test mode
    commands = CalendarCommands(
        spreadsheet_id='test-id',
        live_test=True  # Backups disabled
    )
    
    # Execute command
    result = commands.execute_command(
        '/?action=noCrew&date=20260110&shift_start=1900&shift_end=2100&squad=42'
    )
    
    # Verify command succeeded
    assert result['success'] == True
    
    # Verify no backup was created
    assert result['changeId'] is None
    
    # Verify list_backups returns empty
    backups = commands.list_backups('20260110')
    assert len(backups) == 0
```

## Environment Variables

### Production

```bash
# .env file
SPREADSHEET_ID=your-spreadsheet-id
SUPABASE_URL=your-supabase-url      # Required
SUPABASE_KEY=your-supabase-key      # Required
```

### Testing

```bash
# .env file (or no .env needed)
SPREADSHEET_ID=your-spreadsheet-id
# SUPABASE_URL not required for tests
# SUPABASE_KEY not required for tests
```

## Migration Guide

### Existing Tests

If you have existing tests that initialize `CalendarCommands`:

**Before:**
```python
commands = CalendarCommands(spreadsheet_id='test-id')
# Would fail without Supabase credentials
```

**After:**
```python
commands = CalendarCommands(spreadsheet_id='test-id', live_test=True)
# Works without Supabase credentials ✓
```

### Production Code

No changes needed - production code should already be using `live_test=False` (the default):

```python
commands = CalendarCommands(spreadsheet_id='prod-id')
# Backups enabled by default ✓
```

## Troubleshooting

### Error: "Missing Supabase credentials" in Tests

**Solution:** Make sure you're initializing with `live_test=True`:
```python
commands = CalendarCommands(spreadsheet_id='...', live_test=True)
```

### Backups Not Being Created

**Check:** Are you in test mode?
```python
print(commands.live_test)  # Should be False for backups to work
print(commands.backup_manager)  # Should not be None
```

### Rollback Returns "Not available in test mode"

**Expected:** This is correct behavior when `live_test=True`. Use production mode for rollback functionality.
