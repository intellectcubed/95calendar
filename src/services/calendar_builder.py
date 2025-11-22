#!/usr/bin/env python3
"""
Rescue Squad Shift Scheduler
Reads a CSV template and generates monthly schedules for rescue squad shifts.
"""

import csv
import json
import argparse
import os
from dataclasses import asdict
from datetime import time, date, timedelta
from typing import List, Dict
import calendar
from src.integrations.google_sheets_master import GoogleSheetsMaster
from src.models.calendar_models import Squad, ShiftSegment, Shift, DaySchedule, WeekSchedule


def parse_time(time_str: str) -> time:
    """Parse time string in format 'HHMM' or 'HH:MM' to time object."""
    time_str = time_str.strip()
    
    if ':' in time_str:
        # Format: HH:MM
        parts = time_str.split(':')
        if len(parts) == 2:
            hour = int(parts[0])
            minute = int(parts[1])
            return time(hour, minute)
    elif len(time_str) == 4:
        # Format: HHMM
        hour = int(time_str[:2])
        minute = int(time_str[2:])
        return time(hour, minute)
    
    raise ValueError(f"Invalid time format: {time_str}")


def parse_shift_range(shift_range: str) -> tuple[time, time]:
    """Parse shift range like '1800 - 0600' or '06:00 -1800' into start and end times."""
    if not shift_range or shift_range.strip() == '':
        return None, None
    
    # Handle different separators and formats
    if ' - ' in shift_range:
        parts = shift_range.split(' - ')
    elif ' -' in shift_range:
        parts = shift_range.split(' -')
    elif '- ' in shift_range:
        parts = shift_range.split('- ')
    else:
        return None, None
    
    if len(parts) != 2:
        return None, None
    
    try:
        start_time = parse_time(parts[0])
        end_time = parse_time(parts[1])
        return start_time, end_time
    except ValueError:
        return None, None


def parse_squads(squad_str: str) -> List[Squad]:
    """Parse squad string like '34|54' into list of Squad objects."""
    if not squad_str or squad_str.strip() == '':
        return []
    
    squad_ids = squad_str.split('|')
    squads = []
    for squad_id in squad_ids:
        squad_id = squad_id.strip()
        if squad_id:
            squads.append(Squad(id=int(squad_id)))
    return squads


def create_shift_segments(start_time: time, end_time: time, squads: List[Squad], day_name: str) -> List[ShiftSegment]:
    """Create shift segments, handling special cases like Monday splits."""
    segments = []
    
    # Special handling for Monday splits (1800-0000 and 0000-0600)
    if day_name == "Monday" and start_time == time(18, 0) and end_time == time(6, 0):
        # Split into two segments
        segments.append(ShiftSegment(
            start_time=time(18, 0),
            end_time=time(0, 0),
            squads=squads
        ))
        segments.append(ShiftSegment(
            start_time=time(0, 0),
            end_time=time(6, 0),
            squads=squads
        ))
    else:
        # Single segment
        segments.append(ShiftSegment(
            start_time=start_time,
            end_time=end_time,
            squads=squads
        ))
    
    return segments


def load_template(csv_path: str) -> Dict[int, WeekSchedule]:
    """Parse the CSV into data objects representing the template weeks."""
    template_weeks = {}
    
    with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        rows = list(reader)
        
        if not rows:
            return template_weeks
            
        # Skip header row
        data_rows = rows[1:]
        
        for row in data_rows:
            if not row or not row[0].strip():
                continue
                
            week_str = row[0].strip()
            if not week_str.startswith('week'):
                continue
                
            # Extract week number
            week_num = int(week_str.replace('week', ''))
            
            if week_num not in template_weeks:
                template_weeks[week_num] = WeekSchedule(week_number=week_num)
            
            # Parse the row: week, shift_time, squads, shift_time, squads, ... for each day
            # Days: sunday, monday, tuesday, wed, thurs, fri, sat
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            
            # Process pairs of columns (shift_time, squads) for each day
            col_index = 1  # Start after week column
            
            for day_index, day_name in enumerate(day_names):
                if col_index >= len(row):
                    break
                    
                shift_time = row[col_index].strip() if col_index < len(row) else ''
                squads_str = row[col_index + 1].strip() if col_index + 1 < len(row) else ''
                
                if shift_time and squads_str:
                    start_time, end_time = parse_shift_range(shift_time)
                    if start_time and end_time:
                        squads = parse_squads(squads_str)
                        
                        # Determine shift name
                        if start_time == time(6, 0) and end_time == time(18, 0):
                            shift_name = "Day Shift"
                        elif start_time == time(18, 0) and end_time == time(6, 0):
                            shift_name = "Night Shift"
                        else:
                            shift_name = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} Shift"
                        
                        segments = create_shift_segments(start_time, end_time, squads, day_name)
                        
                        shift = Shift(
                            name=shift_name,
                            start_time=start_time,
                            end_time=end_time,
                            segments=segments
                        )
                        
                        # Find or create day schedule
                        day_schedule = None
                        for day in template_weeks[week_num].days:
                            if day.day == day_name:
                                day_schedule = day
                                break
                        
                        if not day_schedule:
                            day_schedule = DaySchedule(day=day_name)
                            template_weeks[week_num].days.append(day_schedule)
                        
                        day_schedule.shifts.append(shift)
                
                col_index += 2  # Move to next day's columns
    
    return template_weeks


def generate_month_schedule(template_weeks: Dict[int, WeekSchedule], target_month: int, target_year: int) -> List[DaySchedule]:
    """Using the template, generate the schedule for the given month and year."""
    # Calculate which week template to start with for the target month
    # January starts with Week1, then rolls forward continuously
    
    # Calculate total weeks from January of target year to target month
    weeks_from_jan = 0
    for month in range(1, target_month):
        # Get number of weeks in each month
        first_day = date(target_year, month, 1)
        last_day = date(target_year, month, calendar.monthrange(target_year, month)[1])
        
        # Calculate weeks in this month
        first_week = first_day.isocalendar()[1]
        last_week = last_day.isocalendar()[1]
        
        # Handle year boundary
        if last_week < first_week:  # December to January transition
            weeks_in_month = (52 - first_week + 1) + last_week
        else:
            weeks_in_month = last_week - first_week + 1
            
        weeks_from_jan += weeks_in_month
    
    # Determine starting week template (1-based, cycling through available weeks)
    max_week = max(template_weeks.keys())
    starting_week = ((weeks_from_jan) % max_week) + 1
    
    # Generate the month schedule
    month_schedule = []
    first_day = date(target_year, target_month, 1)
    last_day = date(target_year, target_month, calendar.monthrange(target_year, target_month)[1])
    
    current_date = first_day
    current_week_template = starting_week
    
    while current_date <= last_day:
        # Get the day of week (0=Monday, 6=Sunday)
        weekday = current_date.weekday()
        # Convert to our format (0=Sunday, 6=Saturday)
        day_index = (weekday + 1) % 7
        
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        day_name = day_names[day_index]
        
        # Get the template for this week
        week_template = template_weeks.get(current_week_template)
        if week_template:
            # Find the day schedule in the template
            template_day = None
            for day in week_template.days:
                if day.day == day_name:
                    template_day = day
                    break
            
            if template_day:
                # Create a copy of the day schedule for this specific date
                day_schedule = DaySchedule(
                    day=f"{day_name} {current_date.strftime('%Y-%m-%d')}",
                    shifts=template_day.shifts.copy()
                )
                month_schedule.append(day_schedule)
        
        # Move to next day
        current_date += timedelta(days=1)
        
        # If it's Sunday (start of new week), advance to next week template
        if current_date.weekday() == 6:  # Sunday
            current_week_template = (current_week_template % max_week) + 1
    
    return month_schedule


def assign_territories(schedule: List[DaySchedule]) -> None:
    """
    Assign territories to squads based on Google Sheets territory assignments.
    
    Args:
        schedule: List of DaySchedule objects to update with territory assignments
    """
    # Initialize GoogleSheetsMaster and read territory assignments
    from dotenv import load_dotenv
    load_dotenv()
    
    sheets_master = GoogleSheetsMaster('credentials.json')
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    if not spreadsheet_id:
        raise ValueError("SPREADSHEET_ID not found in environment variables")
    territory_map = sheets_master.read_territories(spreadsheet_id)
    
    # Define all territories (based on squad IDs: 34, 35, 42, 43, 54)
    ALL_TERRITORIES = [34, 35, 42, 43, 54]
    
    # Iterate over the schedule
    for day_schedule in schedule:
        for shift in day_schedule.shifts:
            for segment in shift.segments:
                # Create key by sorting squad IDs and joining with comma
                squad_ids = sorted([squad.id for squad in segment.squads])
                
                # Special case: single squad on duty covers all territories
                if len(squad_ids) == 1:
                    for squad in segment.squads:
                        squad.territories = ALL_TERRITORIES.copy()
                else:
                    # Multiple squads: look up territory assignments
                    key = ','.join(str(sid) for sid in squad_ids)
                    
                    # Look up territory assignments for this squad combination
                    if key in territory_map:
                        territory_assignments = territory_map[key]
                        
                        # Assign territories to each squad
                        for squad in segment.squads:
                            # Find the matching territory assignment for this squad
                            for assignment in territory_assignments:
                                if assignment.squad == squad.id:
                                    squad.territories = assignment.territories
                                    break
                    else:
                        # No mapping found - leave territories empty
                        print(f"Warning: No territory mapping found for key '{key}'")


def calculate_shift_hours(start_time: time, end_time: time) -> float:
    """
    Calculate the number of hours in a shift.
    Handles shifts that span midnight (e.g., 18:00 to 06:00).
    
    Args:
        start_time: Shift start time
        end_time: Shift end time
        
    Returns:
        Number of hours as a float
    """
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    
    if end_minutes <= start_minutes:
        # Shift spans midnight
        minutes = (24 * 60 - start_minutes) + end_minutes
    else:
        minutes = end_minutes - start_minutes
    
    return minutes / 60.0


def assign_tango(schedule: List[DaySchedule]) -> None:
    """
    Assign tango designation to shifts to balance tango hours across all squads.
    Tango is one of the squads on duty (or None if no squads).
    
    Args:
        schedule: List of DaySchedule objects to update with tango assignments
    """
    # Track tango hours for each squad
    tango_hours = {}
    
    # Get all unique squad IDs from the schedule
    all_squad_ids = set()
    for day_schedule in schedule:
        for shift in day_schedule.shifts:
            for segment in shift.segments:
                for squad in segment.squads:
                    all_squad_ids.add(squad.id)
    
    # Initialize tango hours tracking
    for squad_id in all_squad_ids:
        tango_hours[squad_id] = 0.0
    
    # Iterate through schedule and assign tango
    for day_schedule in schedule:
        for shift in day_schedule.shifts:
            # Get all squads in this shift (from all segments)
            shift_squads = set()
            for segment in shift.segments:
                for squad in segment.squads:
                    shift_squads.add(squad.id)
            
            if not shift_squads:
                # No squads on duty
                shift.tango = None
            elif len(shift_squads) == 1:
                # Only one squad, they are tango by default
                shift.tango = list(shift_squads)[0]
                shift_hours = calculate_shift_hours(shift.start_time, shift.end_time)
                tango_hours[shift.tango] += shift_hours
            else:
                # Multiple squads - assign tango to the squad with fewest tango hours
                shift_hours = calculate_shift_hours(shift.start_time, shift.end_time)
                
                # Find squad with minimum tango hours from those on this shift
                min_hours = float('inf')
                tango_squad = None
                for squad_id in shift_squads:
                    if tango_hours[squad_id] < min_hours:
                        min_hours = tango_hours[squad_id]
                        tango_squad = squad_id
                
                shift.tango = tango_squad
                tango_hours[tango_squad] += shift_hours


def collect_statistics(schedule: List[DaySchedule]) -> Dict:
    """
    Collect statistics from the schedule.
    
    Args:
        schedule: List of DaySchedule objects
        
    Returns:
        Dictionary containing:
        - hours_by_squad: Dict mapping squad ID to total hours scheduled
        - tango_hours_by_squad: Dict mapping squad ID to total tango hours
        - single_squad_shifts: Number of shifts with only one squad on duty
    """
    hours_by_squad = {}
    tango_hours_by_squad = {}
    single_squad_shifts = 0
    
    # Get all unique squad IDs
    all_squad_ids = set()
    for day_schedule in schedule:
        for shift in day_schedule.shifts:
            for segment in shift.segments:
                for squad in segment.squads:
                    all_squad_ids.add(squad.id)
    
    # Initialize tracking
    for squad_id in all_squad_ids:
        hours_by_squad[squad_id] = 0.0
        tango_hours_by_squad[squad_id] = 0.0
    
    # Collect statistics
    for day_schedule in schedule:
        for shift in day_schedule.shifts:
            shift_hours = calculate_shift_hours(shift.start_time, shift.end_time)
            
            # Get all squads in this shift
            shift_squads = set()
            for segment in shift.segments:
                for squad in segment.squads:
                    shift_squads.add(squad.id)
                    hours_by_squad[squad.id] += shift_hours
            
            # Count single squad shifts
            if len(shift_squads) == 1:
                single_squad_shifts += 1
            
            # Track tango hours
            if shift.tango is not None:
                tango_hours_by_squad[shift.tango] += shift_hours
    
    return {
        'hours_by_squad': hours_by_squad,
        'tango_hours_by_squad': tango_hours_by_squad,
        'single_squad_shifts': single_squad_shifts
    }


def serialize_schedule(schedule: List[DaySchedule]) -> str:
    """Serialize the schedule to JSON format."""
    # Convert dataclasses to dict, handling time objects
    def time_serializer(obj):
        if isinstance(obj, time):
            return obj.strftime('%H:%M:%S')
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    schedule_dict = [asdict(day) for day in schedule]
    return json.dumps(schedule_dict, indent=2, default=time_serializer)


def main():
    parser = argparse.ArgumentParser(description='Generate rescue squad shift schedules')
    parser.add_argument('--csv', default='/Users/george.nowakowski/Downloads/station95template.csv',
                       help='Path to CSV template file')
    parser.add_argument('--month', type=int, default=10, help='Target month (1-12)')
    parser.add_argument('--year', type=int, default=2025, help='Target year')
    parser.add_argument('--output', help='Output JSON file path (optional)')
    parser.add_argument('--populate-google-calendar', action='store_true',
                       help='Populate Google Calendar with the schedule')
    parser.add_argument('--google-calendar-tab', 
                       help='Name of the Google Sheets tab to populate (default: "Month Year")')
    parser.add_argument('--spreadsheet-id',
                       help='Google Spreadsheet ID (default: from SPREADSHEET_ID env var)')
    
    args = parser.parse_args()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        print(f"Loading template from {args.csv}...")
        template = load_template(args.csv)
        print(f"Loaded {len(template)} week templates")
        
        print(f"Generating schedule for {calendar.month_name[args.month]} {args.year}...")
        schedule = generate_month_schedule(template, args.month, args.year)
        
        print("Assigning territories to squads...")
        assign_territories(schedule)
        
        print("Assigning tango designations...")
        assign_tango(schedule)
        
        print("\nCollecting statistics...")
        stats = collect_statistics(schedule)
        
        print("\n" + "="*60)
        print("SCHEDULE STATISTICS")
        print("="*60)
        print("\nHours Scheduled by Squad:")
        for squad_id in sorted(stats['hours_by_squad'].keys()):
            hours = stats['hours_by_squad'][squad_id]
            print(f"  Squad {squad_id}: {hours:.1f} hours")
        
        print("\nTango Hours by Squad:")
        for squad_id in sorted(stats['tango_hours_by_squad'].keys()):
            hours = stats['tango_hours_by_squad'][squad_id]
            print(f"  Squad {squad_id}: {hours:.1f} hours")
        
        print(f"\nSingle Squad Shifts: {stats['single_squad_shifts']}")
        print("="*60 + "\n")
        
        # Populate Google Calendar if requested
        if args.populate_google_calendar:
            print("Populating Google Calendar...")
            sheets_master = GoogleSheetsMaster('credentials.json')
            
            # Get spreadsheet_id from args or environment
            spreadsheet_id = args.spreadsheet_id or os.getenv('SPREADSHEET_ID')
            if not spreadsheet_id:
                raise ValueError("SPREADSHEET_ID must be provided via --spreadsheet-id or SPREADSHEET_ID environment variable")
            
            # Use provided tab name or generate default
            tab_name = args.google_calendar_tab
            if not tab_name:
                tab_name = f"{calendar.month_name[args.month]} {args.year}"
            
            success = sheets_master.populate_calendar(
                spreadsheet_id=spreadsheet_id,
                schedule=schedule,
                tab_name=tab_name,
                month=args.month,
                year=args.year
            )
            
            if success:
                print(f"✓ Successfully populated Google Calendar tab: {tab_name}")
            else:
                print(f"✗ Failed to populate Google Calendar")
        
        json_output = serialize_schedule(schedule)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(json_output)
            print(f"Schedule saved to {args.output}")
        else:
            pass
            # print("\nGenerated Schedule:")
            # print(json_output)
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())