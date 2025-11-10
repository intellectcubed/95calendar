#!/usr/bin/env python3
"""
GoogleSheetsMaster - Class for managing Google Sheets operations
Handles reading territory assignments from Google Sheets templates.
"""

import os.path
import json
from typing import Dict, List
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Scopes for Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class TerritoryAssignment:
    """Represents a squad's territory assignment."""
    
    def __init__(self, squad: int, territories: List[int]):
        self.squad = squad
        self.territories = territories
    
    def __repr__(self):
        return f"TerritoryAssignment(squad={self.squad}, territories={self.territories})"


class GoogleSheetsMaster:
    """Manages Google Sheets operations for rescue squad scheduling."""
    
    def __init__(self, credentials_path: str = 'credentials.json'):
        """
        Initialize GoogleSheetsMaster with credentials.
        
        Args:
            credentials_path: Path to the Google API credentials JSON file
        """
        self.credentials_path = credentials_path
        self.creds = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API using service account credentials."""
        # Check if credentials file exists
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")
        
        # Load credentials to check type
        with open(self.credentials_path, 'r') as f:
            creds_data = json.load(f)
        
        # Use service account authentication
        if creds_data.get('type') == 'service_account':
            self.creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES)
        else:
            raise ValueError("credentials.json must be a service account credentials file")
        
        # Build the service
        self.service = build('sheets', 'v4', credentials=self.creds)
    
    def read_territories(self, spreadsheet_id: str) -> Dict[str, List[TerritoryAssignment]]:
        """
        Read territory assignments from a Google Sheets template.
        
        The spreadsheet contains two tables:
        - Two squad table: Starts at B1, format: Key, Squad, Covering, Squad, Covering
        - Three squad table: Starts at H1, format: Key, Squad, Covering, Squad, Covering, Squad, Covering
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            
        Returns:
            Dictionary mapping squad combination keys (e.g., "34,35") to lists of TerritoryAssignment objects
        """
        try:
            sheet = self.service.spreadsheets()
            
            # Read the two squad table from "Territories" tab (B1:F100, assuming max 100 rows)
            two_squad_range = 'Territories!B1:F100'
            two_squad_result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=two_squad_range
            ).execute()
            two_squad_values = two_squad_result.get('values', [])
            
            # Read the three squad table from "Territories" tab (H1:N100)
            three_squad_range = 'Territories!H1:N100'
            three_squad_result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=three_squad_range
            ).execute()
            three_squad_values = three_squad_result.get('values', [])
            
            # Parse both tables and combine into one map
            territory_map = {}

            print(two_squad_values)
            
            # Parse two squad table
            if two_squad_values:
                # Skip header row (index 0)
                for row in two_squad_values[1:]:
                    if len(row) >= 5 and row[0].strip():  # Ensure we have all columns and a key
                        key = row[0].strip()
                        
                        # Parse first squad
                        squad1 = int(row[1].strip())
                        territories1 = self._parse_territories(row[2])
                        
                        # Parse second squad
                        squad2 = int(row[3].strip())
                        territories2 = self._parse_territories(row[4])
                        
                        territory_map[key] = [
                            TerritoryAssignment(squad1, territories1),
                            TerritoryAssignment(squad2, territories2)
                        ]
            
            # Parse three squad table
            if three_squad_values:
                # Skip header row (index 0)
                for row in three_squad_values[1:]:
                    if len(row) >= 7 and row[0].strip():  # Ensure we have all columns and a key
                        key = row[0].strip()
                        
                        # Parse first squad
                        squad1 = int(row[1].strip())
                        territories1 = self._parse_territories(row[2])
                        
                        # Parse second squad
                        squad2 = int(row[3].strip())
                        territories2 = self._parse_territories(row[4])
                        
                        # Parse third squad
                        squad3 = int(row[5].strip())
                        territories3 = self._parse_territories(row[6])
                        
                        territory_map[key] = [
                            TerritoryAssignment(squad1, territories1),
                            TerritoryAssignment(squad2, territories2),
                            TerritoryAssignment(squad3, territories3)
                        ]
            
            return territory_map
            
        except HttpError as err:
            print(f"An error occurred: {err}")
            return {}
    
    def _parse_territories(self, territory_str: str) -> List[int]:
        """
        Parse a comma-separated string of territories into a list of integers.
        
        Args:
            territory_str: String like "34,42,54"
            
        Returns:
            List of territory numbers as integers
        """
        if not territory_str or not territory_str.strip():
            return []
        
        territories = []
        for t in territory_str.split(','):
            t = t.strip()
            if t:
                territories.append(int(t))
        
        return territories
    
    def populate_calendar(self, spreadsheet_id: str, schedule, tab_name: str = None, month: int = None, year: int = None):
        """
        Populate a Google Sheets calendar template with schedule data.
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            schedule: List of DaySchedule objects
            tab_name: Name of the tab to write to (default: "Month Year" format)
            month: Month number (1-12) for default tab name
            year: Year for default tab name
        """
        from schedule_formatter import ScheduleFormatter
        import calendar as cal
        
        # Generate default tab name if not provided
        if tab_name is None:
            if month and year:
                tab_name = f"{cal.month_name[month]} {year}"
            else:
                raise ValueError("Either tab_name or both month and year must be provided")
        
        try:
            sheet = self.service.spreadsheets()
            
            # Check if cell A100 contains "editable"
            check_range = f"'{tab_name}'!A100"
            check_result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=check_range
            ).execute()
            
            check_values = check_result.get('values', [])
            if not check_values or not check_values[0] or check_values[0][0].lower() != 'editable':
                print(f"Warning: Cell A100 does not contain 'editable'. Aborting calendar population.")
                return False
            
            # Format the schedule using ScheduleFormatter
            formatter = ScheduleFormatter()
            from datetime import datetime
            
            # Parse dates from schedule and organize by calendar position
            # Create a map of (week_number, day_of_week) -> day_schedule
            day_map = {}
            
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            
            for day_schedule in schedule:
                # Extract date from day string (e.g., "Thursday 2026-01-01")
                day_parts = day_schedule.day.split()
                if len(day_parts) >= 2 and '-' in day_parts[1]:
                    date_str = day_parts[1]
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # Get day of week (0=Monday, 6=Sunday)
                    weekday = date_obj.weekday()
                    # Convert to calendar format (0=Sunday, 6=Saturday)
                    day_of_week = (weekday + 1) % 7
                    
                    # Calculate which week of the month this is
                    # Week 0 is the first week containing days of this month
                    first_day_of_month = datetime(date_obj.year, date_obj.month, 1)
                    first_weekday = first_day_of_month.weekday()
                    first_day_of_week = (first_weekday + 1) % 7  # Convert to Sunday=0
                    
                    # Calculate week number (0-based)
                    day_of_month = date_obj.day
                    days_from_first = day_of_month - 1
                    # Adjust for the starting day of the week
                    week_number = (days_from_first + first_day_of_week) // 7
                    
                    day_map[(week_number, day_of_week)] = day_schedule
            
            # Determine how many weeks we need (max week_number + 1)
            max_week = max(week_num for week_num, _ in day_map.keys()) if day_map else 0
            num_weeks = max_week + 1
            
            # Build the data grid for the entire month
            # Each week occupies 10 rows, days are 4 columns each (Sunday-Saturday = 28 columns)
            all_data = []
            
            for week_num in range(num_weeks):
                # Create 10 rows for this week
                week_rows = [[] for _ in range(10)]
                
                # Process each day of the week (Sunday=0 to Saturday=6)
                for day_of_week in range(7):
                    day_schedule = day_map.get((week_num, day_of_week))
                    
                    if day_schedule:
                        # Format this day
                        day_grid = formatter.format_day(day_schedule)
                        
                        # Add each row of this day to the corresponding week row
                        for row_idx in range(10):
                            week_rows[row_idx].extend(day_grid[row_idx])
                    else:
                        # Empty day (pad with empty cells)
                        for row_idx in range(10):
                            week_rows[row_idx].extend(['', '', '', ''])
                
                # Add this week's rows to all_data
                all_data.extend(week_rows)
            
            # Update the spreadsheet starting at B6
            update_range = f"'{tab_name}'!B6"
            
            body = {
                'values': all_data
            }
            
            result = sheet.values().update(
                spreadsheetId=spreadsheet_id,
                range=update_range,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"Successfully updated {result.get('updatedCells')} cells in '{tab_name}'")
            return True
            
        except HttpError as err:
            print(f"An error occurred: {err}")
            return False


# Example usage
if __name__ == "__main__":
    # Example: Read territories from a spreadsheet
    # Replace with your actual spreadsheet ID
    SPREADSHEET_ID = 'your-spreadsheet-id-here'
    
    master = GoogleSheetsMaster()
    territories = master.read_territories(SPREADSHEET_ID)
    
    print("Territory Assignments:")
    for key, assignments in territories.items():
        print(f"\nKey: {key}")
        for assignment in assignments:
            print(f"  Squad {assignment.squad} covers territories: {assignment.territories}")
