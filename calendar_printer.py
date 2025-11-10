#!/usr/bin/env python3
"""
Calendar Printer for Rescue Squad Schedules
Reads JSON schedule data and formats it as a visual calendar.
"""

import json
import argparse
import calendar
from datetime import datetime
from typing import List, Dict, Any


def load_schedule(json_path: str) -> List[Dict[str, Any]]:
    """Load schedule data from JSON file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def parse_date_from_day(day_str: str) -> datetime:
    """Extract date from day string like 'Monday 2025-10-06'."""
    parts = day_str.split(' ')
    if len(parts) >= 2:
        date_str = parts[1]  # Get the date part
        return datetime.strptime(date_str, '%Y-%m-%d')
    return None


def format_squads(squads: List[Dict[str, Any]]) -> str:
    """Format squad list for display."""
    squad_ids = [str(squad['id']) for squad in squads]
    return '|'.join(squad_ids)


def format_shift_summary(shifts: List[Dict[str, Any]]) -> List[str]:
    """Create a summary of shifts for a day."""
    shift_lines = []
    
    for shift in shifts:
        shift_name = shift['name']
        segments = shift['segments']
        
        if len(segments) == 1:
            # Single segment shift
            segment = segments[0]
            squads_str = format_squads(segment['squads'])
            start_time = segment['start_time'][:5]  # Remove seconds
            end_time = segment['end_time'][:5]
            shift_lines.append(f"{start_time}-{end_time}: {squads_str}")
        else:
            # Multi-segment shift (like Monday splits)
            for segment in segments:
                squads_str = format_squads(segment['squads'])
                start_time = segment['start_time'][:5]
                end_time = segment['end_time'][:5]
                shift_lines.append(f"{start_time}-{end_time}: {squads_str}")
    
    return shift_lines


def create_calendar_view(schedule: List[Dict[str, Any]], output_file: str = None, compact: bool = False) -> str:
    """Create a formatted calendar view of the schedule."""
    if not schedule:
        return "No schedule data found."
    
    # Parse the first date to get month/year info
    first_day = parse_date_from_day(schedule[0]['day'])
    if not first_day:
        return "Could not parse schedule dates."
    
    month = first_day.month
    year = first_day.year
    month_name = calendar.month_name[month]
    
    # Create a dictionary mapping dates to schedule data
    schedule_by_date = {}
    for day_schedule in schedule:
        date_obj = parse_date_from_day(day_schedule['day'])
        if date_obj:
            schedule_by_date[date_obj.day] = day_schedule
    
    # Start building the calendar
    output_lines = []
    output_lines.append(f"{'='*160}")
    output_lines.append(f"RESCUE SQUAD SCHEDULE - {month_name.upper()} {year}")
    output_lines.append(f"{'='*160}")
    output_lines.append("")
    
    # Get calendar layout
    cal = calendar.monthcalendar(year, month)
    
    # Create a wider calendar format that can show squad information
    cell_width = 22  # Increased width to show full squad information
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    header = " | ".join(f"{day:^{cell_width}}" for day in day_names)
    output_lines.append(header)
    output_lines.append("-" * len(header))
    
    # Process each week
    for week in cal:
        # We'll create multiple rows for each week to show all shift information
        week_data = []
        max_shifts = 0
        
        # Collect data for each day in the week
        for day in week:
            if day == 0:
                week_data.append([])
            else:
                day_data = schedule_by_date.get(day)
                if day_data:
                    day_info = [f"Day {day}"]
                    shifts = format_shift_summary(day_data['shifts'])
                    day_info.extend(shifts)
                    week_data.append(day_info)
                    max_shifts = max(max_shifts, len(shifts))
                else:
                    week_data.append([f"Day {day}", "No shifts"])
                    max_shifts = max(max_shifts, 1)
        
        # Output the week with proper alignment
        for row_idx in range(max_shifts + 1):  # +1 for day number row
            row_cells = []
            for day_idx in range(7):
                if day_idx < len(week_data) and week_data[day_idx]:
                    if row_idx < len(week_data[day_idx]):
                        cell_content = week_data[day_idx][row_idx]
                        # Don't truncate unless absolutely necessary
                        if len(cell_content) > cell_width + 2:
                            cell_content = cell_content[:cell_width-1] + "+"
                        row_cells.append(f"{cell_content:^{cell_width}}")
                    else:
                        row_cells.append(" " * cell_width)
                else:
                    row_cells.append(" " * cell_width)
            
            output_lines.append(" | ".join(row_cells))
        
        output_lines.append("")  # Space between weeks
    
    # Add detailed daily breakdown (unless compact mode)
    if not compact:
        output_lines.append("\n" + "="*160)
        output_lines.append("DETAILED DAILY SCHEDULE")
        output_lines.append("="*160)
        
        for day_schedule in schedule:
            date_obj = parse_date_from_day(day_schedule['day'])
            if date_obj:
                day_name = date_obj.strftime('%A')
                date_str = date_obj.strftime('%B %d, %Y')
                
                output_lines.append(f"\n{day_name}, {date_str}")
                output_lines.append("-" * (len(day_name) + len(date_str) + 2))
                
                shifts = day_schedule['shifts']
                if not shifts:
                    output_lines.append("  No shifts scheduled")
                else:
                    for shift in shifts:
                        shift_name = shift['name']
                        output_lines.append(f"  {shift_name}:")
                        
                        for segment in shift['segments']:
                            start_time = segment['start_time'][:5]
                            end_time = segment['end_time'][:5]
                            squads = format_squads(segment['squads'])
                            output_lines.append(f"    {start_time} - {end_time}: Squads {squads}")
    
    calendar_text = "\n".join(output_lines)
    
    # Write to file if specified
    if output_file:
        with open(output_file, 'w') as f:
            f.write(calendar_text)
        print(f"Calendar saved to {output_file}")
    
    return calendar_text


def main():
    parser = argparse.ArgumentParser(description='Print rescue squad schedule as a calendar')
    parser.add_argument('json_file', help='Path to JSON schedule file')
    parser.add_argument('--output', '-o', help='Output text file path (optional)')
    parser.add_argument('--compact', '-c', action='store_true', 
                       help='Show compact view (calendar only, no detailed breakdown)')
    
    args = parser.parse_args()
    
    try:
        schedule = load_schedule(args.json_file)
        calendar_text = create_calendar_view(schedule, args.output, args.compact)
        
        if not args.output:
            print(calendar_text)
            
    except FileNotFoundError:
        print(f"Error: Could not find file {args.json_file}")
        return 1
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file {args.json_file}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())