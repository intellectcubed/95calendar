#!/usr/bin/env python3
"""
Schedule Formatter for Google Sheets
Formats DaySchedule objects into CSV format for posting to Google Sheets.
"""

import csv
from typing import List, Optional
from datetime import time
from io import StringIO
from src.models.calendar_models import DaySchedule, Shift, ShiftSegment, Squad


class ScheduleFormatter:
    """Formats schedule data for Google Sheets display."""
    
    ROWS_PER_DAY = 10
    COLS_PER_DAY = 4
    
    def format_day(self, day_schedule: DaySchedule) -> List[List[str]]:
        """
        Format a DaySchedule object into a 10x4 grid for Google Sheets.
        
        Args:
            day_schedule: DaySchedule object to format
            
        Returns:
            List of rows, where each row is a list of 4 column values
        """
        # Initialize 10x4 grid with empty strings
        grid = [['', '', '', ''] for _ in range(self.ROWS_PER_DAY)]
        
        # Extract day number from day string (e.g., "Monday 2025-11-03" -> "3")
        day_parts = day_schedule.day.split()
        if len(day_parts) >= 2 and '-' in day_parts[1]:
            date_parts = day_parts[1].split('-')
            day_number = date_parts[2].lstrip('0')  # Remove leading zeros
            grid[0][0] = day_number
        
        # Sort shifts chronologically (day shifts first, then night shifts)
        # Day shifts start at 06:00, night shifts start at 18:00
        # For night shifts that span midnight, treat hours 0-5 as coming after 18-23
        def shift_sort_key(shift):
            hour = shift.start_time.hour
            minute = shift.start_time.minute
            
            # Normalize hours for sorting: 6-23 stay as is, 0-5 become 24-29
            if hour < 6:
                normalized_hour = hour + 24
            else:
                normalized_hour = hour
            
            return (normalized_hour * 60 + minute)
        
        sorted_shifts = sorted(day_schedule.shifts, key=shift_sort_key)
        
        # Process each shift (starting from row 1)
        row_idx = 1
        for shift in sorted_shifts:
            if row_idx >= self.ROWS_PER_DAY:
                break  # No more rows available
            
            # Get all squads from all segments in this shift
            all_squads = []
            for segment in shift.segments:
                for squad in segment.squads:
                    # Avoid duplicates
                    if not any(s.id == squad.id for s in all_squads):
                        all_squads.append(squad)
            
            # Sort squads by ID
            all_squads.sort(key=lambda s: s.id)
            
            # Format Column 0: Time and Tango
            start_time_str = shift.start_time.strftime('%H%M')
            end_time_str = shift.end_time.strftime('%H%M')
            time_str = f"{start_time_str} - {end_time_str}"
            
            if shift.tango is not None:
                time_str += f"\n(Tango: {shift.tango})"
            
            grid[row_idx][0] = time_str
            
            # Format Columns 1-3: Squads
            for col_idx, squad in enumerate(all_squads[:3]):  # Max 3 squads
                squad_str = self._format_squad(squad)
                grid[row_idx][col_idx + 1] = squad_str
            
            row_idx += 1
        
        return grid
    
    def _format_squad(self, squad: Squad) -> str:
        """
        Format a squad for display.
        
        Args:
            squad: Squad object
            
        Returns:
            Formatted string like "43\n[34,43]", "43\n[All]", or "43\n[No Crew]"
        """
        squad_id = str(squad.id)
        
        # Check if squad is inactive (No Crew)
        if not getattr(squad, 'active', True):
            territories_str = '[No Crew]'
        elif squad.territories and len(squad.territories) > 0:
            # Check if this is all territories (34, 35, 42, 43, 54)
            all_territories = sorted([34, 35, 42, 43, 54])
            if sorted(squad.territories) == all_territories:
                territories_str = '[All]'
            else:
                territories_str = '[' + ','.join(str(t) for t in squad.territories) + ']'
        else:
            territories_str = '[No Crew]'
        
        return f"{squad_id}\n{territories_str}"
    
    def serialize_to_csv(self, day_schedule: DaySchedule) -> str:
        """
        Serialize a DaySchedule to CSV format.
        
        Args:
            day_schedule: DaySchedule object
            
        Returns:
            CSV string representation
        """
        grid = self.format_day(day_schedule)
        
        output = StringIO()
        writer = csv.writer(output)
        for row in grid:
            writer.writerow(row)
        
        return output.getvalue()
    
    def serialize_month_to_csv(self, schedule: List[DaySchedule]) -> str:
        """
        Serialize a full month schedule to CSV format.
        Each day occupies 10 rows, days are placed side by side.
        
        Args:
            schedule: List of DaySchedule objects
            
        Returns:
            CSV string representation of the entire month
        """
        if not schedule:
            return ""
        
        # Format each day
        formatted_days = [self.format_day(day) for day in schedule]
        
        # Combine days horizontally (side by side)
        # We'll put multiple days per row, separated by empty columns
        output = StringIO()
        writer = csv.writer(output)
        
        days_per_row = 7  # One week per row
        
        for week_start in range(0, len(formatted_days), days_per_row):
            week_days = formatted_days[week_start:week_start + days_per_row]
            
            # Write 10 rows for this week
            for row_idx in range(self.ROWS_PER_DAY):
                combined_row = []
                for day_grid in week_days:
                    combined_row.extend(day_grid[row_idx])
                writer.writerow(combined_row)
            
            # Add empty row between weeks
            writer.writerow([])
        
        return output.getvalue()
    
    def deserialize_from_csv(self, csv_data: str, day_name: str) -> DaySchedule:
        """
        Deserialize a DaySchedule from CSV format.
        
        Args:
            csv_data: CSV string (10 rows x 4 columns)
            day_name: Name of the day (e.g., "Monday 2025-11-03")
            
        Returns:
            DaySchedule object
        """
        reader = csv.reader(StringIO(csv_data))
        rows = list(reader)
        
        # Ensure we have at least 10 rows
        while len(rows) < self.ROWS_PER_DAY:
            rows.append(['', '', '', ''])
        
        # Parse day number from first cell (optional, we use day_name parameter)
        day_number = rows[0][0] if rows[0][0] else None
        
        # Parse shifts starting from row 1
        shifts = []
        for row_idx in range(1, self.ROWS_PER_DAY):
            row = rows[row_idx]
            
            # Check if this row has shift data
            if not row[0]:  # No time data means no shift
                continue
            
            # Parse time and tango from column 0
            time_parts = row[0].split('\n')
            time_str = time_parts[0].strip()
            
            tango = None
            if len(time_parts) > 1 and 'Tango:' in time_parts[1]:
                tango_str = time_parts[1].replace('(Tango:', '').replace(')', '').strip()
                tango = int(tango_str)
            
            # Parse start and end times
            if ' - ' in time_str:
                start_str, end_str = time_str.split(' - ')
                start_time = self._parse_time_str(start_str.strip())
                end_time = self._parse_time_str(end_str.strip())
            else:
                continue  # Invalid time format
            
            # Parse squads from columns 1-3
            squads = []
            for col_idx in range(1, 4):
                if col_idx < len(row) and row[col_idx]:
                    squad = self._parse_squad(row[col_idx])
                    if squad:
                        squads.append(squad)
            
            # Create shift
            if start_time and end_time:
                # Determine shift name
                if start_time == time(6, 0) and end_time == time(18, 0):
                    shift_name = "Day Shift"
                elif start_time == time(18, 0) and end_time == time(6, 0):
                    shift_name = "Night Shift"
                else:
                    shift_name = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} Shift"
                
                # Create shift segment
                segment = ShiftSegment(
                    start_time=start_time,
                    end_time=end_time,
                    squads=squads
                )
                
                shift = Shift(
                    name=shift_name,
                    start_time=start_time,
                    end_time=end_time,
                    segments=[segment],
                    tango=tango
                )
                
                shifts.append(shift)
        
        return DaySchedule(day=day_name, shifts=shifts)
    
    def _parse_time_str(self, time_str: str) -> Optional[time]:
        """
        Parse time string in format 'HHMM' to time object.
        
        Args:
            time_str: Time string like '0600' or '1800'
            
        Returns:
            time object or None if invalid
        """
        try:
            if len(time_str) == 4:
                hour = int(time_str[:2])
                minute = int(time_str[2:])
                return time(hour, minute)
        except (ValueError, IndexError):
            pass
        return None
    
    def _parse_squad(self, squad_str: str) -> Optional[Squad]:
        """
        Parse squad string like "43\n[34,43]", "43\n[All]", or "43\n[No Crew]".
        
        Args:
            squad_str: Formatted squad string
            
        Returns:
            Squad object or None if invalid
        """
        parts = squad_str.split('\n')
        if len(parts) < 2:
            return None
        
        try:
            squad_id = int(parts[0].strip())
            territories_str = parts[1].strip()
            
            territories = []
            active = True
            
            if territories_str == '[No Crew]':
                # Inactive squad
                territories = []
                active = False
            elif territories_str == '[All]':
                # All territories
                territories = [34, 35, 42, 43, 54]
                active = True
            else:
                # Parse territories like "[34,43]"
                territories_str = territories_str.strip('[]')
                if territories_str:
                    territories = [int(t.strip()) for t in territories_str.split(',')]
                active = True
            
            return Squad(id=squad_id, territories=territories, active=active)
        except (ValueError, IndexError):
            return None


# Example usage
if __name__ == "__main__":
    from calendar_builder import load_template, generate_month_schedule, assign_territories, assign_tango
    
    # Load and generate a schedule
    template = load_template('/Users/george.nowakowski/Downloads/station95template.csv')
    schedule = generate_month_schedule(template, 11, 2025)
    assign_territories(schedule)
    assign_tango(schedule)
    
    # Format the first day
    formatter = ScheduleFormatter()
    if schedule:
        first_day = schedule[0]
        print("Formatted first day:")
        print(formatter.serialize_to_csv(first_day))
        
        print("\n" + "="*60)
        print("Full month CSV (first 20 lines):")
        month_csv = formatter.serialize_month_to_csv(schedule)
        lines = month_csv.split('\n')[:20]
        print('\n'.join(lines))
