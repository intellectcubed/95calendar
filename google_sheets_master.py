#!/usr/bin/env python3
"""
GoogleSheetsMaster - Class for managing Google Sheets operations
Handles reading territory assignments from Google Sheets templates.
"""

import os.path
import json
import time
from typing import Dict, List, Callable, Any
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
    
    def __init__(self, credentials_path: str = 'credentials.json', live_test: bool = False, 
                 max_retries: int = 5, retry_backoff_seconds: float = 5.0):
        """
        Initialize GoogleSheetsMaster with credentials.
        
        Args:
            credentials_path: Path to the Google API credentials JSON file
            live_test: If True, use "Testing" tab formatted as January 2026
            max_retries: Maximum number of retry attempts for rate-limited requests (default: 5)
            retry_backoff_seconds: Base backoff time in seconds for exponential backoff (default: 5.0)
        """
        self.credentials_path = credentials_path
        self.creds = None
        self.service = None
        self.live_test = live_test
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
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
    
    def _get_tab_name(self, tab_name: str) -> str:
        """
        Get the actual tab name to use, considering live_test mode.
        
        Args:
            tab_name: The requested tab name (e.g., "January 2026")
            
        Returns:
            "Testing" if live_test is True, otherwise the original tab_name
        """
        if self.live_test:
            return "Testing"
        return tab_name
    
    def _retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with exponential backoff retry on rate limit errors.
        
        Args:
            func: The function to execute
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            HttpError: If all retries are exhausted or a non-retryable error occurs
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except HttpError as err:
                last_error = err
                
                # Check if this is a rate limit error (429)
                if err.resp.status == 429:
                    if attempt < self.max_retries - 1:
                        # Calculate backoff time with exponential increase
                        backoff_time = self.retry_backoff_seconds * (2 ** attempt)
                        print(f"Rate limit hit (429). Retrying in {backoff_time:.1f} seconds... (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(backoff_time)
                        continue
                    else:
                        print(f"Rate limit hit (429). Max retries ({self.max_retries}) exhausted.")
                        raise
                else:
                    # Non-retryable error, raise immediately
                    raise
        
        # If we get here, all retries were exhausted
        if last_error:
            raise last_error
    
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
            two_squad_result = self._retry_with_backoff(
                lambda: sheet.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=two_squad_range
                ).execute()
            )
            two_squad_values = two_squad_result.get('values', [])
            
            # Read the three squad table from "Territories" tab (H1:N100)
            three_squad_range = 'Territories!H1:N100'
            three_squad_result = self._retry_with_backoff(
                lambda: sheet.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=three_squad_range
                ).execute()
            )
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
        
        # Apply live_test override if enabled
        actual_tab_name = self._get_tab_name(tab_name)
        
        try:
            sheet = self.service.spreadsheets()
            
            # Check if cell A100 contains "editable"
            check_range = f"'{actual_tab_name}'!A100"
            check_result = self._retry_with_backoff(
                lambda: sheet.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=check_range
                ).execute()
            )
            
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
            update_range = f"'{actual_tab_name}'!B6"
            
            body = {
                'values': all_data
            }
            
            result = self._retry_with_backoff(
                lambda: sheet.values().update(
                    spreadsheetId=spreadsheet_id,
                    range=update_range,
                    valueInputOption='RAW',
                    body=body
                ).execute()
            )
            
            print(f"Successfully updated {result.get('updatedCells')} cells in '{actual_tab_name}'")
            
            # Apply red text formatting to all cells with [No Crew]
            self._format_no_crew_in_range(spreadsheet_id, actual_tab_name, all_data, 6, 2)  # Start at row 6, column B (2)
            
            return True
            
        except HttpError as err:
            print(f"An error occurred: {err}")
            return False
    
    def _format_no_crew_in_range(self, spreadsheet_id: str, tab_name: str, data_grid: list, start_row: int, start_col_num: int):
        """
        Apply red text formatting to all cells containing [No Crew] in a data range.
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            tab_name: Name of the tab
            data_grid: The full data grid
            start_row: Starting row number (1-indexed)
            start_col_num: Starting column number (1-indexed, A=1, B=2, etc.)
        """
        try:
            # Find all cells with [No Crew]
            requests = []
            
            for row_idx, row in enumerate(data_grid):
                for col_idx, cell_value in enumerate(row):
                    if '[No Crew]' in str(cell_value):
                        # Calculate actual row and column in sheet
                        sheet_row = start_row + row_idx - 1  # Convert to 0-indexed
                        sheet_col = start_col_num + col_idx - 1  # Convert to 0-indexed
                        
                        # Create format request for red text
                        requests.append({
                            'repeatCell': {
                                'range': {
                                    'sheetId': self._get_sheet_id(spreadsheet_id, tab_name),
                                    'startRowIndex': sheet_row,
                                    'endRowIndex': sheet_row + 1,
                                    'startColumnIndex': sheet_col,
                                    'endColumnIndex': sheet_col + 1
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'textFormat': {
                                            'foregroundColor': {
                                                'red': 1.0,
                                                'green': 0.0,
                                                'blue': 0.0
                                            }
                                        }
                                    }
                                },
                                'fields': 'userEnteredFormat.textFormat.foregroundColor'
                            }
                        })
            
            # Apply formatting if there are any requests
            if requests:
                body = {
                    'requests': requests
                }
                
                self._retry_with_backoff(
                    lambda: self.service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body=body
                    ).execute()
                )
                
                print(f"Applied red formatting to {len(requests)} cells with [No Crew]")
        
        except HttpError as err:
            print(f"Warning: Could not apply formatting: {err}")
    
    def get_day(self, spreadsheet_id: str, tab_name: str, day: int):
        """
        Retrieve a specific day's schedule from a Google Sheets tab.
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            tab_name: Name of the tab to read from
            day: Day of month (1-31)
            
        Returns:
            DaySchedule object for the specified day
        """
        from schedule_formatter import ScheduleFormatter
        from datetime import datetime
        import calendar as cal
        
        try:
            # Apply live_test override if enabled
            actual_tab_name = self._get_tab_name(tab_name)
            
            # Calculate the grid position for this day
            # Need to determine which week and day of week this day falls on
            # If live_test mode, use January 2026 for calculations
            if self.live_test:
                month = 1
                year = 2026
            else:
                # Parse tab name to get month and year (format: "Month Year")
                tab_parts = tab_name.split()
                if len(tab_parts) >= 2:
                    month_name = tab_parts[0]
                    year = int(tab_parts[1])
                    month = list(cal.month_name).index(month_name)
                else:
                    raise ValueError(f"Invalid tab name format: {tab_name}")
            
            # Create date object for this day
            date_obj = datetime(year, month, day)
            
            # Calculate week and day of week
            weekday = date_obj.weekday()
            day_of_week = (weekday + 1) % 7  # Convert to Sunday=0
            
            first_day_of_month = datetime(year, month, 1)
            first_weekday = first_day_of_month.weekday()
            first_day_of_week = (first_weekday + 1) % 7
            
            days_from_first = day - 1
            week_number = (days_from_first + first_day_of_week) // 7
            
            # Calculate cell range
            # Starting row: 6 + (week_number * 10)
            # Starting column: B + (day_of_week * 4)
            start_row = 6 + (week_number * 10)
            end_row = start_row + 9  # 10 rows total
            
            # Column calculation (B=1, F=5, J=9, N=13, R=17, V=21, Z=25)
            col_offset = day_of_week * 4
            start_col_num = 2 + col_offset  # B=2
            end_col_num = start_col_num + 3  # 4 columns total
            
            # Convert column numbers to letters
            def col_num_to_letter(n):
                result = ""
                while n > 0:
                    n -= 1
                    result = chr(65 + (n % 26)) + result
                    n //= 26
                return result
            
            start_col = col_num_to_letter(start_col_num)
            end_col = col_num_to_letter(end_col_num)
            
            # Read the grid
            range_str = f"'{actual_tab_name}'!{start_col}{start_row}:{end_col}{end_row}"
            
            sheet = self.service.spreadsheets()
            result = self._retry_with_backoff(
                lambda: sheet.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_str
                ).execute()
            )
            
            values = result.get('values', [])
            
            # Pad rows to ensure we have 10 rows
            while len(values) < 10:
                values.append(['', '', '', ''])
            
            # Pad each row to ensure 4 columns
            for i in range(len(values)):
                while len(values[i]) < 4:
                    values[i].append('')
            
            # Convert to CSV format
            from io import StringIO
            import csv as csv_module
            output = StringIO()
            writer = csv_module.writer(output)
            for row in values:
                writer.writerow(row)
            csv_data = output.getvalue()
            
            # Deserialize using ScheduleFormatter
            formatter = ScheduleFormatter()
            day_name = f"{date_obj.strftime('%A')} {date_obj.strftime('%Y-%m-%d')}"
            day_schedule = formatter.deserialize_from_csv(csv_data, day_name)
            
            return day_schedule
            
        except HttpError as err:
            print(f"An error occurred: {err}")
            return None
    
    def put_day(self, spreadsheet_id: str, tab_name: str, day: int, day_schedule):
        """
        Write a DaySchedule back to a specific day in a Google Sheets tab.
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            tab_name: Name of the tab to write to
            day: Day of month (1-31)
            day_schedule: DaySchedule object to write
            
        Returns:
            True if successful, False otherwise
        """
        from schedule_formatter import ScheduleFormatter
        from datetime import datetime
        import calendar as cal
        
        try:
            # Apply live_test override if enabled
            actual_tab_name = self._get_tab_name(tab_name)
            
            # Calculate the grid position for this day (same logic as get_day)
            # If live_test mode, use January 2026 for calculations
            if self.live_test:
                month = 1
                year = 2026
            else:
                tab_parts = tab_name.split()
                if len(tab_parts) >= 2:
                    month_name = tab_parts[0]
                    year = int(tab_parts[1])
                    month = list(cal.month_name).index(month_name)
                else:
                    raise ValueError(f"Invalid tab name format: {tab_name}")
            
            date_obj = datetime(year, month, day)
            weekday = date_obj.weekday()
            day_of_week = (weekday + 1) % 7
            
            first_day_of_month = datetime(year, month, 1)
            first_weekday = first_day_of_month.weekday()
            first_day_of_week = (first_weekday + 1) % 7
            
            days_from_first = day - 1
            week_number = (days_from_first + first_day_of_week) // 7
            
            start_row = 6 + (week_number * 10)
            col_offset = day_of_week * 4
            start_col_num = 2 + col_offset
            
            def col_num_to_letter(n):
                result = ""
                while n > 0:
                    n -= 1
                    result = chr(65 + (n % 26)) + result
                    n //= 26
                return result
            
            start_col = col_num_to_letter(start_col_num)
            
            # Format the day schedule
            formatter = ScheduleFormatter()
            day_grid = formatter.format_day(day_schedule)
            
            # Update the spreadsheet
            range_str = f"'{actual_tab_name}'!{start_col}{start_row}"
            
            body = {
                'values': day_grid
            }
            
            sheet = self.service.spreadsheets()
            result = self._retry_with_backoff(
                lambda: sheet.values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_str,
                    valueInputOption='RAW',
                    body=body
                ).execute()
            )
            
            print(f"Successfully updated day {day} in '{actual_tab_name}' ({result.get('updatedCells')} cells)")
            
            # Apply red text formatting to cells with [No Crew]
            self._format_no_crew_cells(spreadsheet_id, actual_tab_name, start_row, start_col_num, day_grid)
            
            return True
            
        except HttpError as err:
            print(f"An error occurred: {err}")
            return False
    
    def _format_no_crew_cells(self, spreadsheet_id: str, tab_name: str, start_row: int, start_col_num: int, day_grid: list):
        """
        Apply red text formatting to cells containing [No Crew], and reset all other cells to black.
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            tab_name: Name of the tab
            start_row: Starting row number (1-indexed)
            start_col_num: Starting column number (1-indexed, A=1, B=2, etc.)
            day_grid: The 10x4 grid of cell values
        """
        try:
            requests = []
            
            # First, reset ALL cells in the day grid to black
            sheet_id = self._get_sheet_id(spreadsheet_id, tab_name)
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': start_row - 1,  # Convert to 0-indexed
                        'endRowIndex': start_row - 1 + len(day_grid),
                        'startColumnIndex': start_col_num - 1,
                        'endColumnIndex': start_col_num - 1 + 4  # 4 columns wide
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'foregroundColor': {
                                    'red': 0.0,
                                    'green': 0.0,
                                    'blue': 0.0
                                }
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.foregroundColor'
                }
            })
            
            # Then, apply red formatting to cells with [No Crew]
            for row_idx, row in enumerate(day_grid):
                for col_idx, cell_value in enumerate(row):
                    if '[No Crew]' in str(cell_value):
                        # Calculate actual row and column in sheet
                        sheet_row = start_row + row_idx - 1  # Convert to 0-indexed
                        sheet_col = start_col_num + col_idx - 1  # Convert to 0-indexed
                        
                        # Create format request for red text
                        requests.append({
                            'repeatCell': {
                                'range': {
                                    'sheetId': sheet_id,
                                    'startRowIndex': sheet_row,
                                    'endRowIndex': sheet_row + 1,
                                    'startColumnIndex': sheet_col,
                                    'endColumnIndex': sheet_col + 1
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'textFormat': {
                                            'foregroundColor': {
                                                'red': 1.0,
                                                'green': 0.0,
                                                'blue': 0.0
                                            }
                                        }
                                    }
                                },
                                'fields': 'userEnteredFormat.textFormat.foregroundColor'
                            }
                        })
            
            # Apply all formatting requests in a single batch
            if requests:
                body = {
                    'requests': requests
                }
                
                self._retry_with_backoff(
                    lambda: self.service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body=body
                    ).execute()
                )
                
                no_crew_count = len(requests) - 1  # Subtract the reset request
                print(f"Reset all cells to black, then applied red formatting to {no_crew_count} cells with [No Crew]")
        
        except HttpError as err:
            print(f"Warning: Could not apply formatting: {err}")
    
    def _get_sheet_id(self, spreadsheet_id: str, tab_name: str) -> int:
        """
        Get the sheet ID for a given tab name.
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            tab_name: Name of the tab
            
        Returns:
            Sheet ID (integer)
        """
        try:
            spreadsheet = self._retry_with_backoff(
                lambda: self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == tab_name:
                    return sheet['properties']['sheetId']
            
            # If not found, return 0 (first sheet)
            return 0
        
        except HttpError as err:
            print(f"Warning: Could not get sheet ID: {err}")
            return 0


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
