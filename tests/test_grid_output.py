#!/usr/bin/env python3
"""
Test grid output to verify empty cells
"""

from datetime import datetime

# Simulate January 2026 - first day is Thursday
schedule_data = [
    ("Thursday 2026-01-01", 1),
    ("Friday 2026-01-02", 2),
    ("Saturday 2026-01-03", 3),
]

day_map = {}
day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

for day_str, day_num in schedule_data:
    day_parts = day_str.split()
    date_str = day_parts[1]
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    
    weekday = date_obj.weekday()
    day_of_week = (weekday + 1) % 7
    
    first_day_of_month = datetime(date_obj.year, date_obj.month, 1)
    first_weekday = first_day_of_month.weekday()
    first_day_of_week = (first_weekday + 1) % 7
    
    day_of_month = date_obj.day
    days_from_first = day_of_month - 1
    week_number = (days_from_first + first_day_of_week) // 7
    
    day_map[(week_number, day_of_week)] = f"Day{day_num}"
    print(f"{day_str}: week={week_number}, day_of_week={day_of_week} ({day_names[day_of_week]})")

print("\nWeek 0 grid (first row only):")
week_rows = [[]]

for day_of_week in range(7):
    data = day_map.get((0, day_of_week))
    if data:
        week_rows[0].extend([data, '', '', ''])  # 4 columns per day
    else:
        week_rows[0].extend(['', '', '', ''])  # Empty day

print("Row 0:", week_rows[0])
print(f"Length: {len(week_rows[0])} cells")
print("\nExpected: ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 'Day1', '', '', '', 'Day2', '', '', '', 'Day3', '', '', '']")
print("          [Sun empty (4)    ][Mon empty (4)    ][Tue empty (4)    ][Wed empty (4)    ][Thu Day1 (4)     ][Fri Day2 (4)     ][Sat Day3 (4)     ]")
