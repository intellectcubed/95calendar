#!/usr/bin/env python3
"""
Manual Calendar Update Tool
Command-line interface for executing calendar modification commands.
"""

import os
import sys
import argparse
from datetime import datetime
from calendar_commands import CalendarCommands


class ManualCalendarUpdater:
    """Command-line tool for manual calendar updates."""
    
    def __init__(self, is_prod: bool = False):
        """
        Initialize the calendar updater.
        
        Args:
            is_prod: If True, use production calendar. If False, use Testing tab.
        """
        # Get spreadsheet ID from environment variable
        from dotenv import load_dotenv
        load_dotenv()
        
        self.spreadsheet_id = os.environ.get('SPREADSHEET_ID')
        if not self.spreadsheet_id:
            raise EnvironmentError(
                "SPREADSHEET_ID environment variable is not set.\n"
                "Please set it in .env file or with: export SPREADSHEET_ID='your-spreadsheet-id'"
            )
        
        self.is_prod = is_prod
        
        # Initialize CalendarCommands with appropriate mode
        # live_test=True means use "Testing" tab (non-production)
        self.commands = CalendarCommands(
            self.spreadsheet_id,
            live_test=(not is_prod)
        )
        
        print(f"Initialized calendar updater:")
        print(f"  Spreadsheet ID: {self.spreadsheet_id}")
        print(f"  Mode: {'PRODUCTION' if is_prod else 'TESTING'}")
        print(f"  Tab: {'Month-specific' if is_prod else 'Testing'}")
    
    def no_crew(self, date: str, shift_start: str, shift_end: str, squad: int):
        """
        Mark a squad as No Crew for specified hours.
        
        Args:
            date: Date in YYYYMMDD format (e.g., "20260110")
            shift_start: Start time in HHMM format (e.g., "1900")
            shift_end: End time in HHMM format (e.g., "2100")
            squad: Squad ID (e.g., 34, 35, 42, 43, 54)
        
        Returns:
            Result dictionary from command execution
        """
        print(f"\nExecuting noCrew command:")
        print(f"  Date: {self._format_date(date)}")
        print(f"  Time: {self._format_time(shift_start)} - {self._format_time(shift_end)}")
        print(f"  Squad: {squad}")
        
        if self.is_prod:
            confirm = input("\n⚠️  PRODUCTION MODE - Are you sure? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Command cancelled.")
                return {'success': False, 'error': 'User cancelled'}
        
        result = self.commands.execute_command(
            action='noCrew',
            date=date,
            shift_start=shift_start,
            shift_end=shift_end,
            squad=squad,
            preview=False
        )
        self._print_result(result)
        return result
    
    def add_shift(self, date: str, shift_start: str, shift_end: str, squad: int):
        """
        Add a squad to a shift for specified hours.
        
        Args:
            date: Date in YYYYMMDD format (e.g., "20260110")
            shift_start: Start time in HHMM format (e.g., "0600")
            shift_end: End time in HHMM format (e.g., "1800")
            squad: Squad ID (e.g., 34, 35, 42, 43, 54)
        
        Returns:
            Result dictionary from command execution
        """
        print(f"\nExecuting addShift command:")
        print(f"  Date: {self._format_date(date)}")
        print(f"  Time: {self._format_time(shift_start)} - {self._format_time(shift_end)}")
        print(f"  Squad: {squad}")
        
        if self.is_prod:
            confirm = input("\n⚠️  PRODUCTION MODE - Are you sure? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Command cancelled.")
                return {'success': False, 'error': 'User cancelled'}
        
        result = self.commands.execute_command(
            action='addShift',
            date=date,
            shift_start=shift_start,
            shift_end=shift_end,
            squad=squad,
            preview=False
        )
        self._print_result(result)
        return result
    
    def obliterate_shift(self, date: str, shift_start: str, shift_end: str, squad: int):
        """
        Completely remove a squad from a shift.
        
        Args:
            date: Date in YYYYMMDD format (e.g., "20260110")
            shift_start: Start time in HHMM format (e.g., "1800")
            shift_end: End time in HHMM format (e.g., "0600")
            squad: Squad ID (e.g., 34, 35, 42, 43, 54)
        
        Returns:
            Result dictionary from command execution
        """
        print(f"\nExecuting obliterateShift command:")
        print(f"  Date: {self._format_date(date)}")
        print(f"  Time: {self._format_time(shift_start)} - {self._format_time(shift_end)}")
        print(f"  Squad: {squad}")
        
        if self.is_prod:
            confirm = input("\n⚠️  PRODUCTION MODE - Are you sure? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Command cancelled.")
                return {'success': False, 'error': 'User cancelled'}
        
        result = self.commands.execute_command(
            action='obliterateShift',
            date=date,
            shift_start=shift_start,
            shift_end=shift_end,
            squad=squad,
            preview=False
        )
        self._print_result(result)
        return result
    
    def get_schedule(self, date: str):
        """
        Get the current schedule for a specific date.
        
        Args:
            date: Date in YYYYMMDD format (e.g., "20260110")
        
        Returns:
            Result dictionary with schedule grid
        """
        print(f"\nRetrieving schedule for {self._format_date(date)}:")
        
        result = self.commands.execute_command(
            action='get_schedule_day',
            date=date
        )
        
        if result.get('success'):
            print("\n✓ Schedule retrieved successfully")
            print("\nSchedule Grid:")
            for i, row in enumerate(result['grid']):
                print(f"  Row {i}: {row}")
        else:
            print(f"\n✗ Failed to retrieve schedule")
            if 'error' in result:
                print(f"  Error: {result['error']}")
        
        return result
    
    def revert(self, date: str, change_id: str = None):
        """
        Revert a change by restoring from a backup snapshot.
        If no change_id is provided, shows available backups for the date.
        
        Args:
            date: Date in YYYYMMDD format (e.g., "20260110")
            change_id: Optional snapshot ID to restore. If None, lists available backups.
        
        Returns:
            Result dictionary from revert operation
        """
        if not change_id:
            # Delegate to list_backups for display
            self.list_backups(date)
            print("\nTo revert to a snapshot, run:")
            print(f"  python man_update_calendar.py revert --date {date} --change-id <snapshot-id>")
            return {'success': True, 'message': 'Listed available backups'}
        
        # Revert to specific backup
        print(f"\nReverting to snapshot:")
        print(f"  Date: {self._format_date(date)}")
        print(f"  Snapshot ID: {change_id}")
        
        if self.is_prod:
            confirm = input("\n⚠️  PRODUCTION MODE - Are you sure? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Revert cancelled.")
                return {'success': False, 'error': 'User cancelled'}
        
        # Delegate to calendar_commands via execute_command
        result = self.commands.execute_command(
            action='rollback',
            date=date,
            change_id=change_id
        )
        self._print_result(result)
        return result
    
    def list_backups(self, date: str):
        """
        List all backup snapshots for a given date (CLI wrapper).
        
        Args:
            date: Date in YYYYMMDD format (e.g., "20260110")
        
        Returns:
            List of backup snapshots
        """
        print(f"\nBackups for {self._format_date(date)}:")
        
        # Delegate to calendar_commands via execute_command
        result = self.commands.execute_command(
            action='list_backups',
            date=date
        )
        
        backups = result.get('backups', [])
        
        if not backups:
            print("  No backups found for this date.")
            return []
        
        # Format and display backups (CLI-specific presentation)
        for i, backup in enumerate(backups, 1):
            print(f"\n  {i}. Snapshot ID: {backup['id']}")
            print(f"     Created: {backup['created_at']}")
            print(f"     Description: {backup['description']}")
            print(f"     Command: {backup['command']}")
            print(f"     Expires: {backup['expires_at']}")
        
        return backups
    
    def _format_date(self, date_str: str) -> str:
        """Format date string for display."""
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            return date_obj.strftime('%B %d, %Y')
        except:
            return date_str
    
    def _format_time(self, time_str: str) -> str:
        """Format time string for display."""
        if len(time_str) == 4:
            return f"{time_str[:2]}:{time_str[2:]}"
        return time_str
    
    def _print_result(self, result: dict):
        """Print command result."""
        print("\nResult:")
        if result.get('success'):
            print("  ✓ SUCCESS")
            if 'changeId' in result:
                print(f"  Change ID: {result['changeId']}")
                print(f"  (Use this ID to rollback if needed)")
        else:
            print("  ✗ FAILED")
            if 'error' in result:
                print(f"  Error: {result['error']}")


def main():
    """Main entry point for command-line interface."""
    parser = argparse.ArgumentParser(
        description='Manual Calendar Update Tool - Execute calendar modification commands',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mark squad 34 as No Crew from 19:00-21:00 on Jan 10, 2026 (testing mode)
  python man_update_calendar.py noCrew --date 20260110 --start 1900 --end 2100 --squad 34
  
  # Add squad 42 to day shift on Jan 15, 2026 (testing mode)
  python man_update_calendar.py addShift --date 20260115 --start 0600 --end 1800 --squad 42
  
  # Remove squad 54 completely from night shift (testing mode)
  python man_update_calendar.py obliterateShift --date 20260120 --start 1800 --end 0600 --squad 54
  
  # Same as above but in PRODUCTION mode (--prod comes BEFORE the command)
  python man_update_calendar.py --prod noCrew --date 20260110 --start 1900 --end 2100 --squad 34
  
  # List available backups for a date
  python man_update_calendar.py list-backups --date 20260110
  
  # Revert to a specific backup snapshot
  python man_update_calendar.py revert --date 20260110 --change-id abc-123-def
  
  # List backups and choose one to revert (interactive)
  python man_update_calendar.py revert --date 20260110
  
  # Get current schedule for a date
  python man_update_calendar.py get-schedule --date 20260110
  
Environment Variables:
  SPREADSHEET_ID - Required. The Google Spreadsheet ID to update.
  
  Set in .env file or with: export SPREADSHEET_ID='your-spreadsheet-id'
        """
    )
    
    # Global options
    parser.add_argument('--prod', action='store_true',
                       help='Use PRODUCTION mode (default: testing mode)')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # noCrew command
    nocrew_parser = subparsers.add_parser('noCrew', 
                                          help='Mark a squad as No Crew for specified hours')
    nocrew_parser.add_argument('--date', required=True,
                              help='Date in YYYYMMDD format (e.g., 20260110)')
    nocrew_parser.add_argument('--start', required=True,
                              help='Start time in HHMM format (e.g., 1900)')
    nocrew_parser.add_argument('--end', required=True,
                              help='End time in HHMM format (e.g., 2100)')
    nocrew_parser.add_argument('--squad', type=int, required=True,
                              help='Squad ID (34, 35, 42, 43, or 54)')
    
    # addShift command
    addshift_parser = subparsers.add_parser('addShift',
                                            help='Add a squad to a shift')
    addshift_parser.add_argument('--date', required=True,
                                help='Date in YYYYMMDD format (e.g., 20260110)')
    addshift_parser.add_argument('--start', required=True,
                                help='Start time in HHMM format (e.g., 0600)')
    addshift_parser.add_argument('--end', required=True,
                                help='End time in HHMM format (e.g., 1800)')
    addshift_parser.add_argument('--squad', type=int, required=True,
                                help='Squad ID (34, 35, 42, 43, or 54)')
    
    # obliterateShift command
    obliterate_parser = subparsers.add_parser('obliterateShift',
                                              help='Completely remove a squad from a shift')
    obliterate_parser.add_argument('--date', required=True,
                                  help='Date in YYYYMMDD format (e.g., 20260110)')
    obliterate_parser.add_argument('--start', required=True,
                                  help='Start time in HHMM format (e.g., 1800)')
    obliterate_parser.add_argument('--end', required=True,
                                  help='End time in HHMM format (e.g., 0600)')
    obliterate_parser.add_argument('--squad', type=int, required=True,
                                  help='Squad ID (34, 35, 42, 43, or 54)')
    
    # revert command
    revert_parser = subparsers.add_parser('revert',
                                          help='Revert to a previous backup snapshot')
    revert_parser.add_argument('--date', required=True,
                              help='Date in YYYYMMDD format (e.g., 20260110)')
    revert_parser.add_argument('--change-id',
                              help='Snapshot ID to restore (omit to list available backups)')
    
    # list-backups command
    listbackups_parser = subparsers.add_parser('list-backups',
                                               help='List all backup snapshots for a date')
    listbackups_parser.add_argument('--date', required=True,
                                   help='Date in YYYYMMDD format (e.g., 20260110)')
    
    # get-schedule command
    getschedule_parser = subparsers.add_parser('get-schedule',
                                               help='Get the current schedule for a date')
    getschedule_parser.add_argument('--date', required=True,
                                   help='Date in YYYYMMDD format (e.g., 20260110)')
    
    args = parser.parse_args()
    
    # Check if command was provided
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        # Initialize updater
        updater = ManualCalendarUpdater(is_prod=args.prod)
        
        # Execute command
        if args.command == 'noCrew':
            result = updater.no_crew(args.date, args.start, args.end, args.squad)
        elif args.command == 'addShift':
            result = updater.add_shift(args.date, args.start, args.end, args.squad)
        elif args.command == 'obliterateShift':
            result = updater.obliterate_shift(args.date, args.start, args.end, args.squad)
        elif args.command == 'revert':
            result = updater.revert(args.date, args.change_id)
        elif args.command == 'list-backups':
            result = {'success': True, 'backups': updater.list_backups(args.date)}
        elif args.command == 'get-schedule':
            result = updater.get_schedule(args.date)
        
        # Exit with appropriate code
        sys.exit(0 if result.get('success') else 1)
        
    except EnvironmentError as e:
        print(f"\n❌ Environment Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
