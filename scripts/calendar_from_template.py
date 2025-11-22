import csv
from datetime import datetime, timedelta
from collections import defaultdict

class ShiftTemplate:
    def __init__(self):
        self.weeks = {}  # week_num -> day_name -> [(time_range, squads)]
        
    def add_shift(self, week_num, day_name, time_range, squads):
        if week_num not in self.weeks:
            self.weeks[week_num] = defaultdict(list)
        self.weeks[week_num][day_name].append((time_range, squads))

def read_template(filename):
    """Read the CSV template and parse into ShiftTemplate object"""
    template = ShiftTemplate()
    
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    # Parse header to get day names
    header = rows[0]
    day_columns = {}
    for i in range(2, len(header), 2):
        if header[i]:
            day_columns[i] = header[i].lower()
    
    # Parse data rows
    current_week = None
    for row in rows[1:]:
        if not row[0]:
            continue
            
        week_label = row[0]
        if week_label.startswith('week'):
            current_week = int(week_label.replace('week', ''))
        
        # Parse shifts for each day
        for col_idx, day_name in day_columns.items():
            time_range = row[col_idx]
            squads = row[col_idx + 1] if col_idx + 1 < len(row) else ""
            
            if time_range and squads:
                template.add_shift(current_week, day_name, time_range, squads)
    
    return template

def generate_month_schedule(template, target_month, target_year):
    """Generate schedule for a given month and year"""
    # Start date: January 1, 2025 (Wednesday, week 1)
    start_date = datetime(2025, 1, 1)
    target_date = datetime(target_year, target_month, 1)
    
    # Calculate how many days from start to target month
    days_diff = (target_date - start_date).days
    
    # Calculate which week of the 4-week cycle we start on
    # January 1 is week 1, day 0 (Wednesday)
    start_week_offset = (days_diff // 7) % 4
    starting_cycle_week = (start_week_offset % 4) + 1
    
    # Get the last day of the target month
    if target_month == 12:
        last_day = datetime(target_year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(target_year, target_month + 1, 1) - timedelta(days=1)
    
    # Generate schedule
    schedule = []
    current_date = target_date
    calendar_week = 1
    
    day_names = ['monday', 'tuesday', 'wed', 'thurs', 'fri', 'sat', 'sunday']
    
    while current_date <= last_day:
        # Determine which week of 4-week cycle we're in
        days_from_start = (current_date - start_date).days
        cycle_week = ((days_from_start // 7) % 4) + 1
        
        # Get day name
        day_idx = current_date.weekday()  # 0=Monday, 6=Sunday
        if day_idx == 6:  # Sunday
            day_name = 'sunday'
        else:
            day_name = day_names[day_idx]
        
        # Get shifts for this day from template
        if cycle_week in template.weeks and day_name in template.weeks[cycle_week]:
            shifts = template.weeks[cycle_week][day_name]
            for time_range, squads in shifts:
                schedule.append({
                    'calendar_week': calendar_week,
                    'cycle_week': cycle_week,
                    'date': current_date,
                    'day': day_name,
                    'time': time_range,
                    'squads': squads
                })
        
        # Move to next day
        current_date += timedelta(days=1)
        
        # Increment calendar week on Sundays
        if current_date.weekday() == 0 and current_date <= last_day:
            calendar_week += 1
    
    return schedule

def print_schedule_csv(schedule, month, year):
    """Print schedule in CSV format similar to template"""
    if not schedule:
        print("No schedule data")
        return
    
    # Group by calendar week and day
    weeks_data = defaultdict(lambda: defaultdict(list))
    
    for entry in schedule:
        cal_week = entry['calendar_week']
        day = entry['day']
        weeks_data[cal_week][day].append((entry['time'], entry['squads']))
    
    # Print header
    print(",,sunday,,monday,,tuesday,,wed,,thurs,,fri,,sat")
    
    # Print each week
    for week_num in sorted(weeks_data.keys()):
        week_data = weeks_data[week_num]
        
        # Determine how many rows we need for this week
        max_shifts = max(len(week_data[day]) for day in week_data)
        
        for shift_idx in range(max_shifts):
            row = [f"week{week_num}" if shift_idx == 0 else ""]
            
            for day in ['sunday', 'monday', 'tuesday', 'wed', 'thurs', 'fri', 'sat']:
                if day in week_data and shift_idx < len(week_data[day]):
                    time_range, squads = week_data[day][shift_idx]
                    row.extend([time_range, squads])
                else:
                    row.extend(["", ""])
            
            print(",".join(row))

# Main execution
if __name__ == "__main__":
    # Read template
    template = read_template('/Users/george.nowakowski/Downloads/station95template.csv')
    
    # Generate schedules for October, November, December 2025
    for month in [10, 11, 12]:
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December']
        print(f"\n{'='*60}")
        print(f"{month_names[month]} 2025")
        print(f"{'='*60}")
        
        schedule = generate_month_schedule(template, month, 2025)
        print_schedule_csv(schedule, month, 2025)