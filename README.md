# Rescue Squad Shift Scheduler

A Python-based tool for generating and displaying rescue squad shift schedules from a CSV template.

## Overview

This project consists of two main scripts:
- `calendar_builder.py` - Reads a CSV template and generates monthly schedules in JSON format
- `calendar_printer.py` - Reads JSON schedules and displays them as formatted calendars

## Setup

### 1. Activate the Virtual Environment

Before running any scripts, activate the Python virtual environment:

```bash
source venv/bin/activate
```

You'll see `(venv)` appear at the start of your terminal prompt when activated.

To deactivate when you're done:

```bash
deactivate
```

### 2. Install Dependencies

Install required Python packages (with virtual environment activated):

```bash
pip install -r requirements.txt
```

This installs the Google Sheets API client libraries needed for the GoogleSheetsMaster class.

### 3. Google Sheets API Setup

The `GoogleSheetsMaster` class uses service account authentication:

1. Place your `credentials.json` (service account) file in the project root (already present)
2. Share your Google Spreadsheet with the service account email found in credentials.json
   - Email: `mrscoveragewebsite@appspot.gserviceaccount.com`
   - Give "Viewer" or "Editor" access depending on your needs
3. No user authorization required - service accounts authenticate automatically

### 4. CSV Template Format

The CSV template should be located at `/Users/george.nowakowski/Downloads/station95template.csv` (or specify a custom path).

Expected format:
- Header row with day names: `sunday, monday, tuesday, wed, thurs, fri, sat`
- Each week has multiple rows (week1, week2, week3, week4)
- Each day has two columns: shift time and squads
- Example: `week1,06:00 -1800,54,1800 - 0000,43|42,...`

## Usage

### Building a Schedule

Generate a monthly schedule from the CSV template:

```bash
# Generate schedule for October 2025 (default)
python calendar_builder.py

# Generate schedule for a specific month and year
python calendar_builder.py --month 11 --year 2025

# Save to a specific output file
python calendar_builder.py --month 12 --year 2025 --output december_schedule.json

# Use a custom CSV template path
python calendar_builder.py --csv /path/to/template.csv --month 11 --year 2025
```

**Options:**
- `--csv` - Path to CSV template file (default: `/Users/george.nowakowski/Downloads/station95template.csv`)
- `--month` - Target month (1-12, default: 10)
- `--year` - Target year (default: 2025)
- `--output` - Output JSON file path (optional, prints to console if not specified)
- `--populate-google-calendar` - Populate Google Sheets calendar template with the schedule
- `--google-calendar-tab` - Name of the Google Sheets tab to populate (default: "Month Year")
- `--spreadsheet-id` - Google Spreadsheet ID (default: 1bhmLdyBU9-rYmzBj-C6GwMXZCe9fvdb_hKd62S19Pvs)

### Displaying a Calendar

Print a formatted calendar from a JSON schedule:

```bash
# Display full calendar with detailed breakdown
python calendar_printer.py november_schedule.json

# Display compact calendar view (grid only)
python calendar_printer.py november_schedule.json --compact

# Save calendar to a text file
python calendar_printer.py november_schedule.json --output november_calendar.txt

# Compact view saved to file
python calendar_printer.py november_schedule.json --compact --output compact_calendar.txt
```

**Options:**
- `json_file` - Path to JSON schedule file (required)
- `--output` or `-o` - Output text file path (optional, prints to console if not specified)
- `--compact` or `-c` - Show compact view (calendar grid only, no detailed breakdown)

## Complete Workflow Example

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Generate November 2025 schedule
python calendar_builder.py --month 11 --year 2025 --output november_schedule.json

# 3. Generate schedule AND populate Google Calendar
python calendar_builder.py --month 11 --year 2025 --populate-google-calendar

# 4. Generate with custom tab name
python calendar_builder.py --month 12 --year 2025 --populate-google-calendar --google-calendar-tab "December 2025 Final"

# 5. Display the calendar
python calendar_printer.py november_schedule.json

# 6. Save a compact calendar to file
python calendar_printer.py november_schedule.json --compact --output november_calendar.txt

# 7. Deactivate virtual environment when done
deactivate
```

## Schedule Features

- **Rolling Week Pattern**: January starts with Week1, and weeks cycle through the template continuously
- **Shift Types**:
  - Day shifts: 06:00-18:00 (weekends)
  - Night shifts: 18:00-06:00 (most days)
  - Monday split shifts: 18:00-00:00 and 00:00-06:00
- **Squad Assignments**: Shows 1-2 squads per shift (squads: 34, 35, 42, 43, 54)

## Calendar Output Format

The calendar displays:
- Monthly grid layout with day-by-day shift information
- Shift times and squad assignments for each day
- Detailed daily breakdown showing all shift segments
- Clear indication of which squads are on duty

Example output:
```
        Day 3          |         Day 4          |         Day 5
  18:00-00:00: 43|42   |    18:00-06:00: 43     |   18:00-06:00: 34|35
   00:00-06:00: 42     |                        |
```

## Google Calendar Population

The system can automatically populate a Google Sheets calendar template with the generated schedule.

### Requirements

1. **Editable Check**: Cell A100 in the target tab must contain the word "editable" (case-insensitive)
2. **Template Format**: Calendar starts at cell B6 and spans to AC65
3. **Layout**: Each week occupies 10 rows, with days arranged Sunday through Saturday (4 columns per day)

### Usage

```bash
# Populate Google Calendar with default tab name (e.g., "November 2025")
python calendar_builder.py --month 11 --year 2025 --populate-google-calendar

# Use custom tab name
python calendar_builder.py --month 11 --year 2025 --populate-google-calendar --google-calendar-tab "Nov 2025 Draft"

# Use different spreadsheet
python calendar_builder.py --month 11 --year 2025 --populate-google-calendar --spreadsheet-id "your-spreadsheet-id"
```

### How It Works

1. Generates the monthly schedule with territories and tango assignments
2. Checks if cell A100 contains "editable" (safety check)
3. Formats all days using `ScheduleFormatter`
4. Organizes days into weeks (Sunday-Saturday)
5. Updates the entire calendar in a single API call starting at B6

## GoogleSheetsMaster Class

The `GoogleSheetsMaster` class provides integration with Google Sheets for managing territory assignments and calendar population.

### Usage Example

```python
from google_sheets_master import GoogleSheetsMaster

# Initialize with credentials
master = GoogleSheetsMaster('credentials.json')

# Read territory assignments from a spreadsheet
SPREADSHEET_ID = 'your-spreadsheet-id-here'
territories = master.read_territories(SPREADSHEET_ID)

# Access the territory assignments
for key, assignments in territories.items():
    print(f"Key: {key}")
    for assignment in assignments:
        print(f"  Squad {assignment.squad} covers: {assignment.territories}")
```

### Spreadsheet Format

The spreadsheet should contain two tables:

**Two Squad Table (B1:F):**
- Header: Key, Squad, Covering, Squad, Covering
- Example row: `34,35 | 34 | 34,42,54 | 35 | 35,43`

**Three Squad Table (H1:N):**
- Header: Key, Squad, Covering, Squad, Covering, Squad, Covering
- Example row: `34,35,42 | 34 | 34,54 | 35 | 35,43 | 42 | 42`

The `read_territories()` method returns a dictionary where:
- **Key**: String representing squad combination (e.g., "34,35")
- **Value**: List of `TerritoryAssignment` objects, each containing:
  - `squad`: Squad number (int)
  - `territories`: List of territory numbers (List[int])

## ScheduleFormatter Class

The `ScheduleFormatter` class formats schedule data for Google Sheets display.

### Format Specification

Each day occupies a **10 rows × 4 columns** grid:

**Row 0, Column 0**: Day number (e.g., "3" for the 3rd of the month)

**Rows 1-9**: Shifts (one shift per row)
- **Column 0**: Time and Tango
  - Format: `HHMM - HHMM\n(Tango: XX)`
  - Example: `0600 - 1800\n(Tango: 54)`
- **Column 1-3**: Squads (sorted by ID)
  - Format: `ID\n[territories]` or `ID\n[No Crew]`
  - Example: `43\n[34,43]` or `43\n[No Crew]`

### Usage Example

```python
from schedule_formatter import ScheduleFormatter
from calendar_builder import load_template, generate_month_schedule, assign_territories, assign_tango

# Generate schedule
template = load_template('template.csv')
schedule = generate_month_schedule(template, 11, 2025)
assign_territories(schedule)
assign_tango(schedule)

# Format for Google Sheets
formatter = ScheduleFormatter()

# Format a single day
day_csv = formatter.serialize_to_csv(schedule[0])

# Format entire month
month_csv = formatter.serialize_month_to_csv(schedule)

# Deserialize from CSV back to DaySchedule
day_schedule = formatter.deserialize_from_csv(day_csv, "Monday 2025-11-03")
```

### Methods

- `format_day(day_schedule)` - Format a DaySchedule into a 10×4 grid
- `serialize_to_csv(day_schedule)` - Convert DaySchedule to CSV string
- `serialize_month_to_csv(schedule)` - Convert full month to CSV (days side-by-side)
- `deserialize_from_csv(csv_data, day_name)` - Parse CSV back to DaySchedule

## Files

- `calendar_builder.py` - Schedule generator with territory and tango assignment
- `calendar_printer.py` - Calendar formatter for text display
- `schedule_formatter.py` - Google Sheets CSV formatter
- `google_sheets_master.py` - Google Sheets integration class
- `README.md` - This file
- `requirements.txt` - Python package dependencies
- `credentials.json` - Google API service account credentials
- `venv/` - Python virtual environment
- `*.json` - Generated schedule files
- `*.txt` - Generated calendar text files
- `*.csv` - Generated CSV files for Google Sheets
