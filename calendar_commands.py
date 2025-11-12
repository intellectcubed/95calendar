#!/usr/bin/env python3
"""
Calendar Commands
Processes command requests to modify schedules in Google Sheets.
"""

import os
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse
import uuid
from calendar_models import Squad, ShiftSegment, Shift, DaySchedule
from google_sheets_master import GoogleSheetsMaster
import calendar


class CalendarCommands:
    """Processes calendar modification commands."""
    
    def __init__(self, spreadsheet_id: str, credentials_path: str = 'credentials.json', testing: bool = False, live_test: bool = False):
        """
        Initialize CalendarCommands.
        
        Args:
            spreadsheet_id: Google Spreadsheet ID
            credentials_path: Path to credentials file
            testing: If True, append " Testing" to tab names
            live_test: If True, use "Testing" tab formatted as January 2026
        """
        self.spreadsheet_id = spreadsheet_id
        self.sheets_master = GoogleSheetsMaster(credentials_path, live_test=live_test)
        self.audit_log = []  # Stub for audit tracking
        self.testing = testing
        self.live_test = live_test
    
    def execute_command(self, command_url: str) -> Dict:
        """
        Execute a calendar command from a URL-style query string.
        
        Args:
            command_url: URL with query parameters (e.g., "/?action=noCrew&date=20251110&shift_start=1800&shift_end=0600&squad=42")
            
        Returns:
            Dictionary with result status and changeId
        """
        # Parse the URL
        parsed = urlparse(command_url)
        params = parse_qs(parsed.query)
        
        # Extract parameters
        action = params.get('action', [None])[0]
        date_str = params.get('date', [None])[0]
        shift_start_str = params.get('shift_start', [None])[0]
        shift_end_str = params.get('shift_end', [None])[0]
        squad_id = int(params.get('squad', [0])[0]) if params.get('squad') else None
        
        if not action or not date_str:
            return {'success': False, 'error': 'Missing required parameters'}
        
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
        
        # Generate change ID
        change_id = str(uuid.uuid4())
        
        # Get current day schedule
        day_schedule = self.sheets_master.get_day(self.spreadsheet_id, tab_name, day)
        if not day_schedule:
            return {'success': False, 'error': 'Could not retrieve day schedule'}
        
        # Store original state for audit
        self.audit_log.append({
            'changeId': change_id,
            'action': action,
            'date': date_str,
            'original_state': day_schedule
        })
        
        # Execute the command
        if action == 'noCrew':
            modified_schedule = self._no_crew(day_schedule, shift_start, shift_end, squad_id)
        elif action == 'addShift':
            modified_schedule = self._add_shift(day_schedule, shift_start, shift_end, squad_id)
        elif action == 'obliterateShift':
            modified_schedule = self._obliterate_shift(day_schedule, shift_start, shift_end, squad_id)
        else:
            return {'success': False, 'error': f'Unknown action: {action}'}
        
        print('Modified schedule: ')
        print(modified_schedule)
        # Write back to sheet
        success = self.sheets_master.put_day(self.spreadsheet_id, tab_name, day, modified_schedule)
        
        return {
            'success': success,
            'changeId': change_id,
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
    
    def rollback(self, change_id: str) -> Dict:
        """
        Rollback a change by changeId (stub for now).
        
        Args:
            change_id: The change ID to rollback
            
        Returns:
            Dictionary with result status
        """
        # Find the change in audit log
        for entry in self.audit_log:
            if entry['changeId'] == change_id:
                # Restore original state
                original_state = entry['original_state']
                date_str = entry['date']
                
                date_obj = datetime.strptime(date_str, '%Y%m%d')
                day = date_obj.day
                month = date_obj.month
                year = date_obj.year
                tab_name = f"{calendar.month_name[month]} {year}"
                if self.testing:
                    tab_name += " Testing"
                
                success = self.sheets_master.put_day(self.spreadsheet_id, tab_name, day, original_state)
                
                return {
                    'success': success,
                    'message': f'Rolled back change {change_id}'
                }
        
        return {
            'success': False,
            'error': f'Change ID {change_id} not found'
        }


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
    
    # Execute a noCrew command
    result = commands.execute_command('/?action=noCrew&date=20260109&shift_start=1900&shift_end=2100&squad=43')
    print(result)
