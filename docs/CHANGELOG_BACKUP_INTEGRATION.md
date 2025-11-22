# Changelog: Backup System Integration

## Summary

Integrated the `ChangeBackupManager` class into the calendar modification system to provide automatic backup and restore functionality for all calendar changes.

## Changes Made

### 1. Updated `calendar_commands.py`

#### Added Imports
- `ChangeBackupManager` from `change_backup_manager.py`
- `ScheduleFormatter` from `schedule_formatter.py`

#### Modified `__init__` Method
- Added `backup_ttl_days` parameter (default: 30)
- Initialized `ChangeBackupManager` instance
- Initialized `ScheduleFormatter` instance
- Removed `audit_log` list (replaced with Supabase backups)

#### Modified `execute_command` Method
- **Before modification**: Saves current grid state using `backup_manager.save_grid()`
- **Backup metadata**: Includes description, command URL, and date
- **Returns**: Snapshot ID as `changeId` instead of UUID

#### Replaced `rollback` Method
- **New signature**: `rollback(change_id: str, date_str: str)`
- **Functionality**: Restores from Supabase backup snapshot
- **Process**:
  1. Retrieves backup grid from Supabase
  2. Converts grid back to `DaySchedule`
  3. Writes restored schedule to Google Sheets

#### Added New Methods
- `list_backups(date_str: str)`: Lists all backup snapshots for a date
- `_grid_to_csv(grid)`: Helper to convert grid to CSV string

### 2. Updated `man_update_calendar.py`

#### Replaced `rollback` Method with `revert`
- **New signature**: `revert(date: str, change_id: str = None)`
- **Interactive mode**: If no `change_id` provided, lists available backups
- **Direct mode**: Reverts to specific snapshot if `change_id` provided

#### Added `list_backups` Method
- Lists all backup snapshots for a given date
- Shows snapshot ID, creation time, description, command, and expiration

#### Updated CLI Commands
- **Removed**: `rollback` command
- **Added**: `revert` command with `--date` and optional `--change-id`
- **Added**: `list-backups` command with `--date`

#### Updated Help Text
- Added examples for listing backups
- Added examples for reverting changes
- Updated environment variables documentation

### 3. Updated Configuration Files

#### `.env.example`
- Added `SUPABASE_URL` configuration
- Added `SUPABASE_KEY` configuration

#### `README.md`
- Added Supabase credentials to environment setup
- Added reference to `BACKUP_SYSTEM.md`

### 4. New Documentation

#### `BACKUP_SYSTEM.md`
- Complete guide to the backup system
- Setup instructions
- Usage examples (CLI and programmatic)
- Best practices
- Troubleshooting guide

#### `CHANGELOG_BACKUP_INTEGRATION.md` (this file)
- Summary of all changes made

## Test Mode Behavior

### Backup System Disabled in Test Mode

When `CalendarCommands` is initialized with `live_test=True`:
- **No backups are created** during command execution
- `backup_manager` is set to `None`
- `list_backups()` returns an empty list
- `rollback()` returns an error: "Rollback not available in test mode"
- **No Supabase credentials required** for unit tests

This ensures:
1. Unit tests don't require Supabase setup
2. Test data doesn't pollute the backup database
3. Tests run faster without backup overhead

## Migration Notes

### Breaking Changes

1. **`rollback` method signature changed**:
   - Old: `rollback(change_id: str)`
   - New: `rollback(change_id: str, date_str: str)`
   - **Impact**: Any code calling `rollback` must now provide the date

2. **CLI command changed**:
   - Old: `python man_update_calendar.py rollback --change-id <id>`
   - New: `python man_update_calendar.py revert --date <date> --change-id <id>`
   - **Impact**: Update any scripts or documentation using the old command

3. **Requires Supabase**:
   - The system now requires Supabase credentials
   - **Impact**: Must set `SUPABASE_URL` and `SUPABASE_KEY` in `.env`

### Non-Breaking Changes

1. **`execute_command` return value**:
   - Still returns `changeId` field
   - Now contains Supabase snapshot UUID instead of random UUID
   - **Impact**: None - existing code continues to work

2. **Backup TTL**:
   - Default: 30 days (configurable)
   - **Impact**: Old backups will expire automatically

## Benefits

1. **Persistent Backups**: Backups stored in Supabase database (not in-memory)
2. **Audit Trail**: Complete history of all changes with metadata
3. **Easy Recovery**: Simple CLI commands to list and restore backups
4. **Automatic Cleanup**: Expired backups are automatically eligible for deletion
5. **Flexible TTL**: Configurable retention period per backup or globally

## Testing Checklist

- [ ] Test `noCrew` command creates backup
- [ ] Test `addShift` command creates backup
- [ ] Test `obliterateShift` command creates backup
- [ ] Test `list-backups` shows all backups for a date
- [ ] Test `revert` without `--change-id` lists backups
- [ ] Test `revert` with `--change-id` restores backup
- [ ] Test backup expiration (TTL)
- [ ] Test production mode confirmation prompts
- [ ] Test error handling for missing Supabase credentials
- [ ] Test error handling for invalid snapshot IDs

## Future Enhancements

1. **Automatic cleanup job**: Scheduled task to delete expired backups
2. **Backup comparison**: Show diff between current state and backup
3. **Bulk operations**: Revert multiple days at once
4. **Backup export**: Download backups as JSON/CSV files
5. **Backup search**: Search backups by description or command
