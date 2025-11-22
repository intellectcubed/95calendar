# Calendar Change Backup System

## Overview

The calendar modification system now includes automatic backup functionality using Supabase. Every time a change is made to the calendar (noCrew, addShift, obliterateShift), the original state is saved as a backup snapshot that can be restored later.

## Setup

### 1. Supabase Configuration

Add your Supabase credentials to the `.env` file:

```bash
SUPABASE_URL=your-supabase-url-here
SUPABASE_KEY=your-supabase-anon-key-here
```

### 2. Database Schema

The backup system uses a `day_snapshots` table in Supabase. See `supabase/setup.sql` for the schema.

## How It Works

### Automatic Backups

When you execute any calendar modification command, the system:

1. **Saves the current state** before making changes
2. **Stores metadata** including:
   - Date (YYYYMMDD format)
   - Description (e.g., "noCrew - Squad 42 (1900-2100)")
   - Command URL that was executed
   - Timestamp
   - Expiration date (default: 30 days)
3. **Returns a snapshot ID** that can be used to revert the change

**Note:** Backups are NOT created when `CalendarCommands` is initialized with `live_test=True`. This prevents unit tests from requiring Supabase credentials and polluting the backup database.

### Backup Retention

- Default TTL: 30 days
- Configurable per backup or globally
- Expired backups can be cleaned up automatically

## Usage

### Making Changes (Automatic Backup)

```bash
# Make a change - backup is created automatically
python man_update_calendar.py noCrew --date 20260110 --start 1900 --end 2100 --squad 34

# Output includes:
# ✅ Saved snapshot abc-123-def for day 20260110
# Change ID: abc-123-def
# (Use this ID to rollback if needed)
```

### Listing Available Backups

```bash
# List all backups for a specific date
python man_update_calendar.py list-backups --date 20260110

# Output:
# Backups for January 10, 2026:
#
#   1. Snapshot ID: abc-123-def
#      Created: 2026-01-10T14:30:00
#      Description: noCrew - Squad 42 (1900-2100)
#      Command: /?action=noCrew&date=20260110&shift_start=1900&shift_end=2100&squad=42
#      Expires: 2026-02-09T14:30:00
```

### Reverting Changes

#### Option 1: List and Choose

```bash
# Show available backups and instructions
python man_update_calendar.py revert --date 20260110

# Then revert to a specific snapshot
python man_update_calendar.py revert --date 20260110 --change-id abc-123-def
```

#### Option 2: Direct Revert

```bash
# Revert directly if you know the snapshot ID
python man_update_calendar.py revert --date 20260110 --change-id abc-123-def
```

## Programmatic Usage

### In Python Code

```python
from calendar_commands import CalendarCommands

# Initialize with custom TTL (production mode)
commands = CalendarCommands(
    spreadsheet_id='your-id',
    backup_ttl_days=60  # Keep backups for 60 days
)

# Execute a command (backup created automatically)
result = commands.execute_command(
    '/?action=noCrew&date=20260110&shift_start=1900&shift_end=2100&squad=42'
)
snapshot_id = result['changeId']

# List backups for a date
backups = commands.list_backups('20260110')

# Revert to a backup
result = commands.rollback(snapshot_id, '20260110')
```

### Test Mode (No Backups)

```python
# Initialize in test mode - backups are disabled
commands = CalendarCommands(
    spreadsheet_id='your-id',
    live_test=True  # Disables backup system
)

# Execute a command (NO backup created)
result = commands.execute_command(
    '/?action=noCrew&date=20260110&shift_start=1900&shift_end=2100&squad=42'
)
# result['changeId'] will be None

# list_backups returns empty list in test mode
backups = commands.list_backups('20260110')  # Returns []

# rollback returns error in test mode
result = commands.rollback(snapshot_id, '20260110')
# Returns: {'success': False, 'error': 'Rollback not available in test mode'}
```

### Using ChangeBackupManager Directly

```python
from change_backup_manager import ChangeBackupManager

manager = ChangeBackupManager(default_ttl_days=30)

# Save a grid snapshot
snapshot_id = manager.save_grid(
    day='20260110',
    grid=my_10x4_grid,
    description='Before modification',
    command='/?action=noCrew&...',
    ttl_days=45  # Override default TTL
)

# List snapshots for a day
snapshots = manager.list_snapshots('20260110')

# Revert to a snapshot
restored_grid = manager.revert_to_snapshot(snapshot_id)

# Cleanup expired snapshots
deleted_count = manager.cleanup_expired_snapshots()
```

## Backup Data Structure

Each backup snapshot contains:

- **id**: UUID (automatically generated)
- **day**: Date in YYYYMMDD format
- **description**: Human-readable description
- **command**: The command URL that was executed
- **csv_data**: The 10x4 grid in CSV format
- **created_at**: Timestamp when backup was created
- **expires_at**: When the backup will expire

## Best Practices

1. **Review before reverting**: Always list backups first to see what you're reverting to
2. **Use descriptive commands**: The command URL is saved for reference
3. **Production mode**: Always confirm before reverting in production
4. **Regular cleanup**: Periodically clean up expired backups to save storage

## Troubleshooting

### Error: "Missing Supabase credentials"

Make sure `SUPABASE_URL` and `SUPABASE_KEY` are set in your `.env` file.

### Error: "No snapshot found with id..."

The snapshot may have expired or been deleted. List available backups to see what's available.

### Backup not created

Check that:
1. Supabase credentials are correct
2. The `day_snapshots` table exists in your Supabase database
3. You have write permissions

## Security Notes

- Backups are stored in Supabase with your configured access controls
- The anon key should have appropriate row-level security policies
- Expired backups are automatically eligible for deletion
- Consider implementing additional access controls in Supabase for production use
