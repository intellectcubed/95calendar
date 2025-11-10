#!/usr/bin/env python3
"""
Test calendar positioning logic
"""

from datetime import datetime

def calculate_position(date_str):
    """Calculate week and day position for a given date."""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    
    # Get day of week (0=Monday, 6=Sunday)
    weekday = date_obj.weekday()
    # Convert to calendar format (0=Sunday, 6=Saturday)
    day_of_week = (weekday + 1) % 7
    
    # Calculate which week of the month this is
    first_day_of_month = datetime(date_obj.year, date_obj.month, 1)
    first_weekday = first_day_of_month.weekday()
    first_day_of_week = (first_weekday + 1) % 7  # Convert to Sunday=0
    
    # Calculate week number (0-based)
    day_of_month = date_obj.day
    days_from_first = day_of_month - 1
    # Adjust for the starting day of the week
    week_number = (days_from_first + first_day_of_week) // 7
    
    # Calculate cell position
    row = 6 + (week_number * 10)
    col_offset = day_of_week * 4
    
    # Convert column offset to letter (B=1, so B+0=B, B+4=F, B+8=J, etc.)
    col_letters = ['B', 'F', 'J', 'N', 'R', 'V', 'Z']
    col_letter = col_letters[day_of_week] if day_of_week < len(col_letters) else f"B+{col_offset}"
    
    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    print(f"Date: {date_str} ({day_names[day_of_week]})")
    print(f"  Day of month: {day_of_month}")
    print(f"  First day of month is: {day_names[first_day_of_week]}")
    print(f"  Week number: {week_number}")
    print(f"  Day of week: {day_of_week} ({day_names[day_of_week]})")
    print(f"  Cell position: {col_letter}{row}")
    print()

# Test January 2026
print("="*60)
print("JANUARY 2026 - First day is Thursday")
print("="*60)
print()

calculate_position('2026-01-01')  # Thursday - should be R6
calculate_position('2026-01-04')  # Sunday - should be B16
calculate_position('2026-01-20')  # Tuesday - should be J36

print("="*60)
print("Expected positions:")
print("  Jan 1 (Thu): R6")
print("  Jan 4 (Sun): B16")
print("  Jan 20 (Tue): J36")
print("="*60)
