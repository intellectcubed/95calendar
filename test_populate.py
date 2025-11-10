#!/usr/bin/env python3
"""
Test populate calendar with January 2026
"""

from calendar_builder import load_template, generate_month_schedule, assign_territories, assign_tango
from google_sheets_master import GoogleSheetsMaster

# Generate January 2026 schedule
print("Generating January 2026 schedule...")
template = load_template('/Users/george.nowakowski/Downloads/station95template.csv')
schedule = generate_month_schedule(template, 1, 2026)

print(f"Generated {len(schedule)} days")
print(f"First day: {schedule[0].day}")
print(f"Last day: {schedule[-1].day}")

# Just test the positioning logic without actually updating
print("\nTesting calendar positioning...")
sheets_master = GoogleSheetsMaster('credentials.json')

# This will show debug output
# sheets_master.populate_calendar(
#     spreadsheet_id='1bhmLdyBU9-rYmzBj-C6GwMXZCe9fvdb_hKd62S19Pvs',
#     schedule=schedule[:3],  # Just first 3 days for testing
#     tab_name='Test',
#     month=1,
#     year=2026
# )
