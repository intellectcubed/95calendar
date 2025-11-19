#!/usr/bin/env python3
"""
Calendar Commands
Processes command requests to modify schedules in Google Sheets.
"""

import os
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional
from calendar_models import Squad, ShiftSegment, Shift, DaySchedule
from google_sheets_master import GoogleSheetsMaster
from change_backup_manager import ChangeBackupManager
from schedule_formatter import ScheduleFormatter
import calendar


class CalendarCommands:
    """Processes calendar modification commands."""
    
    def __init__(self, spreadsheet_id: str, credentials_path: str = 'credentials.json', testing: bool = False, live_test: bool = False, backup_ttl_days: int = 30):
        """
        Initialize CalendarCommands.
        
        Args:
            spreadsheet_id: Google Spreadsheet ID
            credentials_path: Path to credentials file
            testing: If True, append " Testing" to tab names
            live_test: If True, use "Testing" tab formatted as January 2026
            backup_ttl_days: Number of days to keep backups (default: 30)
        """
        self.spreadsheet_id = spreadsheet_id
        self.sheets_master = GoogleSheetsMaster(credentials_path, live_test=live_test)
        self.formatter = ScheduleFormatter()
        self.testing = testing
        self.live_test = live_test
        
        # Only initialize backup manager if not in test mode
        # This prevents unit tests from requiring Supabase credentials
        if not live_test:
            self.backup_manager = ChangeBackupManager(default_ttl_days=backup_ttl_days)
        else:
            self.backup_manager = None
    
    def execute_command(self, action: str, date: str, **kwargs) -> Dict:
        """
        Execute a calendar command.
        
        Args:
            action: Command action (e.g., 'noCrew', 'addShift', 'obliterateShift', 'get_schedule_day', 'list_backups', 'rollback')
            date: Date in YYYYMMDD format (e.g., "20260110")
            **kwargs: Additional parameters:
                - shift_start: Start time in HHMM format (e.g., "1800")
                - shift_end: End time in HHMM format (e.g., "0600")
                - squad: Squad ID (e.g., 34, 35, 42, 43, 54)
                - change_id: Snapshot ID for rollback action
                - preview: If True, return modified grid without writing to sheets (default: True)
            
        Returns:
            Dictionary with result status, changeId, and optionally modified_grid
        """
        if not action or not date:
            return {'success': False, 'error': 'Missing required parameters: action and date'}
        
        # Extract parameters from kwargs with defaults
        date_str = date
        shift_start_str = kwargs.get('shift_start')
        shift_end_str = kwargs.get('shift_end')
        squad_id = kwargs.get('squad')
        change_id = kwargs.get('change_id')
        preview = kwargs.get('preview', True)
        
        # Parse date
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        day = date_obj.day
        month = date_obj.month
        year = date_obj.year
        
        # Determine tab name
        tab_name = f"{calendar.month_name[month]} {year}"
        if self.testing:
            tab_name += " Testing"
        
        # Parse shift times
        shift_start = self._parse_time(shift_start_str) if shift_start_str else None
        shift_end = self._parse_time(shift_end_str) if shift_end_str else None
        
        # Get current day schedule
        day_schedule = self.sheets_master.get_day(self.spreadsheet_id, tab_name, day)
        if not day_schedule:
            return {'success': False, 'error': 'Could not retrieve day schedule'}
        
        # Execute the command based on action
        if action == 'get_schedule_day':
            # Read-only command - return current schedule
            grid = self.formatter.format_day(day_schedule)
            return {
                'success': True,
                'action': 'get_schedule_day',
                'date': date_str,
                'grid': grid
            }
        elif action == 'list_backups':
            # Read-only command - list backup snapshots
            backups = self.list_backups(date_str)
            return {
                'success': True,
                'action': 'list_backups',
                'date': date_str,
                'backups': backups
            }
        elif action == 'rollback':
            # Restore from backup snapshot
            if not change_id:
                return {'success': False, 'error': 'change_id is required for rollback action'}
            return self.rollback(change_id, date_str)
        elif action == 'noCrew':
            modified_schedule = self._no_crew(day_schedule, shift_start, shift_end, squad_id)
        elif action == 'addShift':
            modified_schedule = self._add_shift(day_schedule, shift_start, shift_end, squad_id)
        elif action == 'obliterateShift':
            modified_schedule = self._obliterate_shift(day_schedule, shift_start, shift_end, squad_id)
        else:
            return {'success': False, 'error': f'Unknown action: {action}'}
        
        print('Modified schedule: ')
        print(modified_schedule)
        
        # If preview mode, return the modified grid without writing to sheets or creating backup
        if preview:
            modified_grid = self.formatter.format_day(modified_schedule)
            return {
                'success': True,
                'preview': True,
                'modified_grid': modified_grid,
                'action': action,
                'date': date_str
            }
        
        # Save backup of original state before modification (only when actually writing, skip in test mode)
        backup_id = None
        if not self.live_test:
            original_grid = self.formatter.format_day(day_schedule)
            description = f"{action} - Squad {squad_id}" if squad_id else action
            if shift_start and shift_end:
                description += f" ({shift_start.strftime('%H%M')}-{shift_end.strftime('%H%M')})"
            
            # Build command string for audit trail
            command_str = f"action={action}&date={date_str}"
            if shift_start_str:
                command_str += f"&shift_start={shift_start_str}"
            if shift_end_str:
                command_str += f"&shift_end={shift_end_str}"
            if squad_id:
                command_str += f"&squad={squad_id}"
            
            backup_id = self.backup_manager.save_grid(
                day=date_str,
                grid=original_grid,
                description=description,
                command=command_str
            )
        
        # Write back to sheet (non-preview mode)
        success = self.sheets_master.put_day(self.spreadsheet_id, tab_name, day, modified_schedule)
        
        return {
            'success': success,
            'changeId': backup_id,
            'action': action,
            'date': date_str
        }
    

    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HHMM format."""
        if len(time_str) == 3:
            time_str = '0' + time_str
        hour = int(time_str[:2])
        minute = int(time_str[2:]) if len(time_str) > 2 else 0
        return time(hour, minute)
    
    def _no_crew(self, day_schedule: DaySchedule, start_time: time, end_time: time, squad_id: int) -> DaySchedule:
        """
        Remove a squad from duty for specified hours, marking territories as [No Crew].
        
        Args:
            day_schedule: Current day schedule
            start_time: Start time of no-crew period
            end_time: End time of no-crew period (if same as start_time, means full 24 hours)
            squad_id: Squad to remove
            
        Returns:
            Modified DaySchedule
        """
        # Convert to hourly grid for easier manipulation
        hourly_grid = self._to_hourly_grid(day_schedule)
        
        # Apply no-crew for the specified hours
        current_time = start_time
        hours_processed = 0
        max_hours = 24 if start_time == end_time else 24
        
        while hours_processed < max_hours:
            hour_key = current_time.hour
            
            if hour_key in hourly_grid:
                # Find and modify the squad
                for squad in hourly_grid[hour_key]['squads']:
                    if squad.id == squad_id:
                        squad.active = False  # Mark as inactive (No Crew)
                        squad.territories = []  # Clear territories
            
            # Increment hour
            current_time = (datetime.combine(datetime.today(), current_time) + timedelta(hours=1)).time()
            hours_processed += 1
            
            # Break if we've reached the end time (and it's not a 24-hour period)
            if start_time != end_time and current_time == end_time:
                break
        
        # Reassign tango and territories
        hourly_grid = self._reassign_tango(hourly_grid)
        
        # Convert back to DaySchedule
        return self._from_hourly_grid(hourly_grid, day_schedule.day)
    
    def _add_shift(self, day_schedule: DaySchedule, start_time: time, end_time: time, squad_id: int) -> DaySchedule:
        """
        Add a squad for the specified time window.
        
        Args:
            day_schedule: Current day schedule
            start_time: Start time of shift
            end_time: End time of shift (if same as start_time, means full 24 hours)
            squad_id: Squad to add
            
        Returns:
            Modified DaySchedule
        """
        hourly_grid = self._to_hourly_grid(day_schedule)
        
        # Add squad for the specified hours
        current_time = start_time
        hours_processed = 0
        max_hours = 24 if start_time == end_time else 24
        
        while hours_processed < max_hours:
            hour_key = current_time.hour
            
            if hour_key not in hourly_grid:
                hourly_grid[hour_key] = {'squads': [], 'tango': None}
            
            # Check if squad already exists
            if not any(s.id == squad_id for s in hourly_grid[hour_key]['squads']):
                hourly_grid[hour_key]['squads'].append(Squad(id=squad_id, territories=[]))
            
            current_time = (datetime.combine(datetime.today(), current_time) + timedelta(hours=1)).time()
            hours_processed += 1
            
            # Break if we've reached the end time (and it's not a 24-hour period)
            if start_time != end_time and current_time == end_time:
                break
        
        # Reassign territories and tango
        hourly_grid = self._reassign_tango(hourly_grid)
        
        return self._from_hourly_grid(hourly_grid, day_schedule.day)
    
    def _obliterate_shift(self, day_schedule: DaySchedule, start_time: time, end_time: time, squad_id: int) -> DaySchedule:
        """
        Completely remove a squad's shift.
        
        Args:
            day_schedule: Current day schedule
            start_time: Start time of shift to remove
            end_time: End time of shift to remove (if same as start_time, means full 24 hours)
            squad_id: Squad to remove
            
        Returns:
            Modified DaySchedule
        """
        hourly_grid = self._to_hourly_grid(day_schedule)
        
        # Remove squad for the specified hours
        current_time = start_time
        hours_processed = 0
        
        # If start_time == end_time, it means full 24 hours
        max_hours = 24 if start_time == end_time else 24
        
        while hours_processed < max_hours:
            hour_key = current_time.hour
            
            if hour_key in hourly_grid:
                hourly_grid[hour_key]['squads'] = [
                    s for s in hourly_grid[hour_key]['squads'] if s.id != squad_id
                ]
            
            current_time = (datetime.combine(datetime.today(), current_time) + timedelta(hours=1)).time()
            hours_processed += 1
            
            # Break if we've reached the end time (and it's not a 24-hour period)
            if start_time != end_time and current_time == end_time:
                break
        
        # Reassign tango
        hourly_grid = self._reassign_tango(hourly_grid)
        
        return self._from_hourly_grid(hourly_grid, day_schedule.day)
    
    def _to_hourly_grid(self, day_schedule: DaySchedule) -> Dict:
        """Convert DaySchedule to hourly grid representation."""
        hourly_grid = {}
        
        for shift in day_schedule.shifts:
            for segment in shift.segments:
                # Convert segment to hourly slots
                current_time = segment.start_time
                end_time = segment.end_time
                
                while current_time != end_time:
                    hour_key = current_time.hour
                    
                    if hour_key not in hourly_grid:
                        hourly_grid[hour_key] = {
                            'squads': [],
                            'tango': shift.tango
                        }
                    
                    # Add squads (avoid duplicates)
                    for squad in segment.squads:
                        if not any(s.id == squad.id for s in hourly_grid[hour_key]['squads']):
                            hourly_grid[hour_key]['squads'].append(Squad(
                                id=squad.id, 
                                territories=squad.territories.copy(),
                                active=getattr(squad, 'active', True)
                            ))
                    
                    # Increment hour
                    next_hour = (datetime.combine(datetime.today(), current_time) + timedelta(hours=1)).time()
                    current_time = next_hour
        
        return hourly_grid
    
    def _from_hourly_grid(self, hourly_grid: Dict, day_name: str) -> DaySchedule:
        """Convert hourly grid back to DaySchedule."""
        # Group consecutive hours with same squad configuration into shifts
        shifts = []
        
        # Sort hours - handle shifts that span midnight (18-23, 0-5)
        all_hours = sorted(hourly_grid.keys())
        
        if not all_hours:
            return DaySchedule(day=day_name, shifts=[])
        
        # Reorder hours to handle midnight crossing (18,19,20...23,0,1,2...5)
        # Assume shifts start at 6 or 18
        sorted_hours = []
        if 18 in all_hours:
            # Night shift pattern: 18-23, then 0-5
            sorted_hours = [h for h in all_hours if h >= 18] + [h for h in all_hours if h < 18]
        else:
            # Day shift or other pattern
            sorted_hours = all_hours
        
        # Build continuous shifts by detecting changes in squad configuration OR shift boundaries
        current_shift_start = None
        current_config = None
        
        for i, hour in enumerate(sorted_hours):
            hour_data = hourly_grid[hour]
            
            # Create a configuration signature: (squad_ids, territories_per_squad, active_status)
            config = tuple(sorted([
                (s.id, tuple(sorted(s.territories)), getattr(s, 'active', True)) for s in hour_data['squads']
            ]))
            
            # Check if we're at a standard shift boundary (6am or 6pm)
            is_shift_boundary = (hour == 6 or hour == 18)
            
            if current_config is None or config != current_config or is_shift_boundary:
                # Configuration changed or shift boundary - save previous shift and start new one
                if current_shift_start is not None:
                    # End time is the current hour
                    end_time = time(hour, 0)
                    shifts.append(self._create_shift_from_hour(current_shift_start, end_time, hourly_grid))
                
                current_shift_start = time(hour, 0)
                current_config = config
        
        # Add final shift
        if current_shift_start is not None:
            # Calculate end time based on last hour
            last_hour = sorted_hours[-1]
            # End time is one hour after the last hour
            if last_hour == 23:
                end_time = time(0, 0)
            elif last_hour < 6:
                end_time = time(6, 0)  # End at 6am
            else:
                end_time = time((last_hour + 1) % 24, 0)
            
            shifts.append(self._create_shift_from_hour(current_shift_start, end_time, hourly_grid))
        
        return DaySchedule(day=day_name, shifts=shifts)
    
    def _create_shift_from_hour(self, start_time: time, end_time: time, hourly_grid: Dict) -> Shift:
        """Create a Shift object from time range and hourly grid."""
        # Get squads from the first hour of this shift
        hour_key = start_time.hour
        hour_data = hourly_grid.get(hour_key, {})
        squads = hour_data.get('squads', [])
        tango = hour_data.get('tango')
        
        # Make copies of squads to avoid reference issues, preserving active flag
        squad_copies = [Squad(id=s.id, territories=s.territories.copy(), active=getattr(s, 'active', True)) for s in squads]
        
        # Determine shift name
        if start_time == time(6, 0) and end_time == time(18, 0):
            shift_name = "Day Shift"
        elif start_time == time(18, 0) and end_time == time(6, 0):
            shift_name = "Night Shift"
        else:
            shift_name = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} Shift"
        
        segment = ShiftSegment(
            start_time=start_time,
            end_time=end_time,
            squads=squad_copies
        )
        
        return Shift(
            name=shift_name,
            start_time=start_time,
            end_time=end_time,
            segments=[segment],
            tango=tango
        )
    
    def _reassign_tango(self, hourly_grid: Dict) -> Dict:
        """Reassign tango and territories based on current squad assignments."""
        ALL_TERRITORIES = [34, 35, 42, 43, 54]
        
        # Load territory assignments from Google Sheets
        from google_sheets_master import GoogleSheetsMaster
        sheets_master = GoogleSheetsMaster('credentials.json')
        territory_map = sheets_master.read_territories(self.spreadsheet_id)
        
        for hour_key, hour_data in hourly_grid.items():
            squads = hour_data['squads']
            
            # Get only ACTIVE squad IDs (inactive squads are "No Crew")
            active_squads = [s for s in squads if getattr(s, 'active', True)]
            active_squad_ids = [s.id for s in active_squads]
            
            # If only one active squad, it covers all territories
            if len(active_squad_ids) == 1:
                active_squads[0].territories = ALL_TERRITORIES.copy()
                hour_data['tango'] = active_squads[0].id
            elif len(active_squad_ids) > 1:
                # Multiple active squads - look up territory assignments
                # Create key by sorting squad IDs
                squad_key = ','.join(str(sid) for sid in sorted(active_squad_ids))
                
                if squad_key in territory_map:
                    # Assign territories based on territory map
                    territory_assignments = territory_map[squad_key]
                    for squad in active_squads:
                        for assignment in territory_assignments:
                            if assignment.squad == squad.id:
                                squad.territories = assignment.territories
                                break
                else:
                    # No mapping found - distribute evenly or assign all to first
                    print(f"Warning: No territory mapping found for squads {squad_key}")
                    # Fallback: first active squad gets all territories
                    if active_squads:
                        active_squads[0].territories = ALL_TERRITORIES.copy()
                        for i in range(1, len(active_squads)):
                            active_squads[i].territories = []
                
                # Assign tango to first active squad with territories
                squads_with_territories = [s for s in active_squads if s.territories]
                if squads_with_territories:
                    hour_data['tango'] = squads_with_territories[0].id
                else:
                    hour_data['tango'] = active_squad_ids[0] if active_squad_ids else None
            else:
                # No active squads
                hour_data['tango'] = None
            
            # Ensure inactive squads keep empty territories
            for squad in squads:
                if not getattr(squad, 'active', True):
                    squad.territories = []
        
        return hourly_grid
    
    def rollback(self, change_id: str, date_str: str) -> Dict:
        """
        Rollback a change by restoring from a backup snapshot.
        
        Args:
            change_id: The snapshot ID to restore
            date_str: Date string in YYYYMMDD format
            
        Returns:
            Dictionary with result status
        """
        if self.live_test or not self.backup_manager:
            return {
                'success': False,
                'error': 'Rollback not available in test mode'
            }
        
        try:
            # Retrieve the backup grid
            backup_grid = self.backup_manager.revert_to_snapshot(change_id)
            
            # Parse date
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            day = date_obj.day
            month = date_obj.month
            year = date_obj.year
            
            # Determine tab name
            tab_name = f"{calendar.month_name[month]} {year}"
            if self.testing:
                tab_name += " Testing"
            
            # Write the backup grid directly to the sheet
            # We don't need to convert to DaySchedule and back - just write the grid
            success = self._write_grid_to_sheet(self.spreadsheet_id, tab_name, day, backup_grid)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to write restored grid to sheet',
                    'changeId': change_id,
                    'date': date_str
                }
            
            # Remove the snapshot after successful rollback
            remove_result = self.backup_manager.remove_snapshot(change_id)
            
            return {
                'success': True,
                'message': f'Rolled back to snapshot {change_id}',
                'changeId': change_id,
                'date': date_str,
                'snapshot_removed': remove_result.get('success', False)
            }
        except ValueError as e:
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Rollback failed: {str(e)}'
            }
    
    def list_backups(self, date_str: str) -> List[Dict]:
        """
        List all backup snapshots for a given date.
        
        Args:
            date_str: Date string in YYYYMMDD format
            
        Returns:
            List of snapshot dictionaries
        """
        if self.live_test or not self.backup_manager:
            return []
        return self.backup_manager.list_snapshots(date_str)
    
    def _write_grid_to_sheet(self, spreadsheet_id: str, tab_name: str, day: int, grid: List[List[str]]) -> bool:
        """
        Write a grid directly to a specific day in Google Sheets.
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            tab_name: Name of the tab to write to
            day: Day of month (1-31)
            grid: 10x4 grid to write
            
        Returns:
            True if successful, False otherwise
        """
        from datetime import datetime
        import calendar as cal
        
        try:
            # Apply live_test override if enabled
            actual_tab_name = self.sheets_master._get_tab_name(tab_name)
            
            # Calculate the grid position for this day
            if self.live_test:
                month = 1
                year = 2026
            else:
                tab_parts = tab_name.split()
                if len(tab_parts) >= 2:
                    month_name = tab_parts[0]
                    year = int(tab_parts[1])
                    month = list(cal.month_name).index(month_name)
                else:
                    raise ValueError(f"Invalid tab name format: {tab_name}")
            
            date_obj = datetime(year, month, day)
            weekday = date_obj.weekday()
            day_of_week = (weekday + 1) % 7
            
            first_day_of_month = datetime(year, month, 1)
            first_weekday = first_day_of_month.weekday()
            first_day_of_week = (first_weekday + 1) % 7
            
            days_from_first = day - 1
            week_number = (days_from_first + first_day_of_week) // 7
            
            start_row = 6 + (week_number * 10)
            col_offset = day_of_week * 4
            start_col_num = 2 + col_offset
            
            def col_num_to_letter(n):
                result = ""
                while n > 0:
                    n -= 1
                    result = chr(65 + (n % 26)) + result
                    n //= 26
                return result
            
            start_col = col_num_to_letter(start_col_num)
            
            # Update the spreadsheet with the grid
            range_str = f"'{actual_tab_name}'!{start_col}{start_row}"
            
            body = {
                'values': grid
            }
            
            sheet = self.sheets_master.service.spreadsheets()
            result = self.sheets_master._retry_with_backoff(
                lambda: sheet.values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_str,
                    valueInputOption='RAW',
                    body=body
                ).execute()
            )
            
            print(f"Successfully restored day {day} in '{actual_tab_name}' ({result.get('updatedCells')} cells)")
            
            # Apply red text formatting to cells with [No Crew]
            self.sheets_master._format_no_crew_cells(spreadsheet_id, actual_tab_name, start_row, start_col_num, grid)
            
            return True
            
        except Exception as err:
            print(f"An error occurred: {err}")
            return False
    
    def _grid_to_csv(self, grid: List[List[str]]) -> str:
        """Helper to convert grid to CSV string."""
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        for row in grid:
            writer.writerow(row)
        return output.getvalue()


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    if not spreadsheet_id:
        raise ValueError("SPREADSHEET_ID not found in environment variables")
    
    # Example command
    commands = CalendarCommands(spreadsheet_id)
    
    # Get a day's schedule
    schedule_result = commands.execute_command(
        action='get_schedule_day',
        date='20260109'
    )
    print("Current schedule:")
    print(schedule_result)
    
    # Execute a noCrew command (preview mode)
    result = commands.execute_command(
        action='noCrew',
        date='20260109',
        shift_start='1900',
        shift_end='2100',
        squad=43,
        preview=True
    )
    print("\nPreview result:")
    print(result)
    
    # Execute with actual write to sheets
    result = commands.execute_command(
        action='noCrew',
        date='20260109',
        shift_start='1900',
        shift_end='2100',
        squad=43,
        preview=False
    )
    print("\nExecute result:")
    print(result)
    
    # List backups for a date
    backups_result = commands.execute_command(
        action='list_backups',
        date='20260109'
    )
    print("\nList backups result:")
    print(backups_result)
    
    # Rollback to a snapshot
    if backups_result.get('backups'):
        snapshot_id = backups_result['backups'][0]['id']
        rollback_result = commands.execute_command(
            action='rollback',
            date='20260109',
            change_id=snapshot_id
        )
        print("\nRollback result:")
        print(rollback_result)
