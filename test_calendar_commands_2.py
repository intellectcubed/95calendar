#!/usr/bin/env python3
"""
Comprehensive Test Suite for CalendarCommands
Based on TestCommandsSpec.txt - Tests all permutations of add/remove/obliterate operations
"""

import pytest
from datetime import time
from calendar_commands import CalendarCommands
from calendar_models import Squad, ShiftSegment, Shift, DaySchedule
from google_sheets_master import GoogleSheetsMaster

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
if not SPREADSHEET_ID:
    raise ValueError("SPREADSHEET_ID not found in environment variables")
TAB_NAME = 'Testing'


class TestCalendarCommands:
    """Test suite for CalendarCommands with comprehensive coverage."""
    
    @pytest.fixture(scope="class")
    def commands(self):
        """Initialize CalendarCommands with live_test mode."""
        return CalendarCommands(SPREADSHEET_ID, live_test=True)
    
    @pytest.fixture(scope="class")
    def sheets_master(self):
        """Initialize GoogleSheetsMaster with live_test mode."""
        return GoogleSheetsMaster('credentials.json', live_test=True)
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_calendar(self, sheets_master):
        """
        Setup: Populate the Testing tab with initial squad configurations.
        This runs once before all tests in the class.
        """
        from calendar_builder import load_template, generate_month_schedule, assign_territories, assign_tango
        
        print("\n" + "="*80)
        print("SETUP: Populating Testing Calendar")
        print("="*80)
        
        # Load and generate January 2026 schedule
        template = load_template('/Users/george.nowakowski/Downloads/station95template.csv')
        schedule = generate_month_schedule(template, 1, 2026)
        assign_territories(schedule)
        assign_tango(schedule)
        
        # Populate the Testing tab
        success = sheets_master.populate_calendar(
            spreadsheet_id=SPREADSHEET_ID,
            schedule=schedule,
            tab_name='January 2026',  # Will be overridden to "Testing"
            month=1,
            year=2026
        )
        
        assert success, "Failed to populate base calendar"
        print("✓ Base calendar populated successfully")
        
        yield  # Tests run here
        
        # Teardown (if needed)
        print("\n" + "="*80)
        print("TEARDOWN: Tests complete")
        print("="*80)
    
    def get_day_schedule(self, sheets_master, day):
        """Helper to retrieve a day's schedule."""
        return sheets_master.get_day(SPREADSHEET_ID, TAB_NAME, day)
    
    def get_squads_from_shift(self, shift):
        """Helper to extract squad IDs from a shift."""
        squads = []
        for segment in shift.segments:
            squads.extend([squad.id for squad in segment.squads])
        return list(set(squads))
    
    def verify_squad_territories(self, shift, squad_id, expected_territories):
        """Verify a squad has the expected territories."""
        for segment in shift.segments:
            for squad in segment.squads:
                if squad.id == squad_id:
                    assert set(squad.territories) == set(expected_territories), \
                        f"Squad {squad_id} territories mismatch: expected {expected_territories}, got {squad.territories}"
                    return True
        return False
    
    # ========================================================================
    # TC01: noCrew - Partial shift removal (middle hours)
    # ========================================================================
    def test_tc01_nocrew_partial_middle(self, commands, sheets_master):
        """TC01: Remove squad 34 for 1900-2100 on Jan 1."""
        print("\n" + "="*80)
        print("TC01: noCrew - Partial shift (1900-2100)")
        print("="*80)
        
        # Get initial state
        initial = self.get_day_schedule(sheets_master, 1)
        initial_squads = self.get_squads_from_shift(initial.shifts[0])
        print(f"Initial squads on day 1: {initial_squads}")
        
        # Execute command
        result = commands.execute_command(
            '/?action=noCrew&date=20260101&shift_start=1900&shift_end=2100&squad=42'
        )
        assert result['success'], f"Command failed: {result}"
        
        # Verify result
        modified = self.get_day_schedule(sheets_master, 1)
        
        # Should have 3 shifts: before (1800-1900), during (1900-2100), after (2100-0600)
        assert len(modified.shifts) == 3, f"Expected 3 shifts, got {len(modified.shifts)}"
        
        # Middle shift should have squad 34 with no territories
        middle_shift = modified.shifts[1]
        assert middle_shift.start_time == time(19, 0)
        assert middle_shift.end_time == time(21, 0)
        
        # Verify squad 34 has no territories in middle shift
        squad_34_found = False
        for segment in middle_shift.segments:
            for squad in segment.squads:
                if squad.id == 42:
                    squad_34_found = True
                    assert squad.territories == [], f"Squad 42 should have no territories, got {squad.territories}"
        
        assert squad_34_found, "Squad 42 not found in middle shift"
        print("✓ TC01 PASSED")
    
    # ========================================================================
    # TC02: noCrew - Full shift removal
    # ========================================================================
    def test_tc02_nocrew_full_shift(self, commands, sheets_master):
        """TC02: Remove squad 35 for entire shift on Jan 2."""
        print("\n" + "="*80)
        print("TC02: noCrew - Full shift")
        print("="*80)
        
        result = commands.execute_command(
            '/?action=noCrew&date=20260102&shift_start=1800&shift_end=0600&squad=35'
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 2)
        
        # Should have 1 shift with squad 35 marked as No Crew
        assert len(modified.shifts) >= 1
        
        # Verify squad 35 has no territories
        for shift in modified.shifts:
            for segment in shift.segments:
                for squad in segment.squads:
                    if squad.id == 35:
                        assert squad.territories == [], f"Squad 35 should have no territories"
        
        print("✓ TC02 PASSED")
    
    # ========================================================================
    # TC03: obliterateShift - Remove one of three squads
    # ========================================================================
    def test_tc03_obliterate_from_three(self, commands, sheets_master):
        """TC03: Remove squad 35 entirely from 3-squad shift on Jan 3."""
        print("\n" + "="*80)
        print("TC03: obliterateShift - Remove from 3-squad shift")
        print("="*80)
        
        result = commands.execute_command(
            '/?action=obliterateShift&date=20260103&shift_start=0600&shift_end=0600&squad=35'
        )

        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 3)
        
        # Squad 35 should not appear in any shift
        for shift in modified.shifts:
            squads = self.get_squads_from_shift(shift)
            assert 35 not in squads, f"Squad 35 should be removed, but found in shift"
        
        print("✓ TC03 PASSED")
    
    # ========================================================================
    # TC04: noCrew - Temporarily remove Tango
    # ========================================================================
    def test_tc04_nocrew_tango_removal(self, commands, sheets_master):
        """TC04: Remove Tango squad 43 for 0000-0300 on Jan 3."""
        print("\n" + "="*80)
        print("TC04: noCrew - Temporarily remove Tango")
        print("="*80)
        
        # First check who is Tango initially
        initial = self.get_day_schedule(sheets_master, 3)
        initial_tango = initial.shifts[0].tango if initial.shifts else None
        print(f"Initial Tango: {initial_tango}")
        
        result = commands.execute_command(
            '/?action=noCrew&date=20260103&shift_start=0000&shift_end=0300&squad=43'
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 3)
        
        # Find the shift covering 0000-0300
        midnight_shift = None
        for shift in modified.shifts:
            if shift.start_time <= time(0, 0) < shift.end_time or \
               (shift.start_time > shift.end_time and time(0, 0) < shift.end_time):
                midnight_shift = shift
                break
        
        if midnight_shift:
            # Tango should have changed if 43 was Tango
            if initial_tango == 43:
                assert midnight_shift.tango != 43, "Tango should have changed from 43"
        
        print("✓ TC04 PASSED")
    
    # ========================================================================
    # TC05: addShift - Add second squad to single-squad day
    # ========================================================================
    def test_tc05_addshift_to_single(self, commands, sheets_master):
        """TC05: Add squad 43 to single-squad day on Jan 4."""
        print("\n" + "="*80)
        print("TC05: addShift - Add to single-squad shift")
        print("="*80)
        
        initial = self.get_day_schedule(sheets_master, 4)
        initial_squads = self.get_squads_from_shift(initial.shifts[0]) if initial.shifts else []
        print(f"Initial squads: {initial_squads}")
        
        result = commands.execute_command(
            '/?action=addShift&date=20260104&shift_start=1800&shift_end=0600&squad=43'
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 4)
        
        # Should now have 2 squads
        modified_squads = self.get_squads_from_shift(modified.shifts[1])
        assert 43 in modified_squads, "Squad 43 should be added"
        assert len(modified_squads) >= 2, f"Should have at least 2 squads, got {len(modified_squads)}"
        
        print("✓ TC05 PASSED")
    
    # ========================================================================
    # TC06: noCrew - Remove Tango for part of shift
    # ========================================================================
    def test_tc06_nocrew_tango_partial(self, commands, sheets_master):
        """TC06: Remove Tango squad for 2200-0600 on Jan 5."""
        print("\n" + "="*80)
        print("TC06: noCrew - Remove Tango for partial shift")
        print("="*80)
        
        initial = self.get_day_schedule(sheets_master, 5)
        initial_tango = initial.shifts[0].tango if initial.shifts else None
        
        result = commands.execute_command(
            f'/?action=noCrew&date=20260105&shift_start=2200&shift_end=0600&squad={initial_tango}'
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 5)
        
        # Should have multiple shifts
        assert len(modified.shifts) >= 2, f"Expected multiple shifts, got {len(modified.shifts)}"
        
        print("✓ TC06 PASSED")
    
    # ========================================================================
    # TC07: addShift - Add to weekend daytime shift
    # ========================================================================
    def test_tc07_addshift_weekend_day(self, commands, sheets_master):
        """TC07: Add squad 34 to weekend day shift on Jan 6."""
        print("\n" + "="*80)
        print("TC07: addShift - Weekend daytime")
        print("="*80)
        
        result = commands.execute_command(
            '/?action=addShift&date=20260106&shift_start=0600&shift_end=1800&squad=34'
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 6)
        
        # Find day shift
        day_shift = next((s for s in modified.shifts if s.start_time == time(6, 0)), None)
        if day_shift:
            squads = self.get_squads_from_shift(day_shift)
            assert 34 in squads, "Squad 34 should be in day shift"
        
        print("✓ TC07 PASSED")
    
    # ========================================================================
    # TC08: obliterateShift - Remove squad completely
    # ========================================================================
    def test_tc08_obliterate_complete(self, commands, sheets_master):
        """TC08: Remove squad 43 completely from Jan 7."""
        print("\n" + "="*80)
        print("TC08: obliterateShift - Complete removal")
        print("="*80)
        
        result = commands.execute_command(
            '/?action=obliterateShift&date=20260107&shift_start=1800&shift_end=0600&squad=43'
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 7)
        
        # Squad 43 should not appear
        for shift in modified.shifts:
            squads = self.get_squads_from_shift(shift)
            assert 43 not in squads, "Squad 43 should be completely removed"
        
        print("✓ TC08 PASSED")
    
    # ========================================================================
    # TC09: addShift - Partial shift addition
    # ========================================================================
    def test_tc09_addshift_partial(self, commands, sheets_master):
        """TC09: Add squad 35 for 2000-0000 on Jan 8."""
        print("\n" + "="*80)
        print("TC09: addShift - Partial shift")
        print("="*80)
        
        result = commands.execute_command(
            '/?action=addShift&date=20260108&shift_start=2000&shift_end=0000&squad=35'
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 8)
        
        # Should have multiple shifts due to split
        assert len(modified.shifts) >= 2, f"Expected multiple shifts, got {len(modified.shifts)}"
        
        # Find shift covering 2000-0000
        target_shift = None
        for shift in modified.shifts:
            if shift.start_time == time(20, 0):
                target_shift = shift
                break
        
        if target_shift:
            squads = self.get_squads_from_shift(target_shift)
            assert 35 in squads, "Squad 35 should be in 2000-0000 shift"
        
        print("✓ TC09 PASSED")
    
    # ========================================================================
    # TC10: Combined operations - noCrew after addShift
    # ========================================================================
    def test_tc10_combined_operations(self, commands, sheets_master):
        """TC10: noCrew on squad 34 for 2000-0000 on Jan 8 (after TC09)."""
        print("\n" + "="*80)
        print("TC10: Combined - noCrew after addShift")
        print("="*80)
        
        result = commands.execute_command(
            '/?action=noCrew&date=20260108&shift_start=2000&shift_end=0000&squad=34'
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 8)
        
        # Verify squad 34 has no territories in 2000-0000 window
        for shift in modified.shifts:
            if shift.start_time >= time(20, 0) and shift.end_time <= time(0, 0):
                for segment in shift.segments:
                    for squad in segment.squads:
                        if squad.id == 34:
                            assert squad.territories == [], f"Squad 34 should have no territories"
        
        print("✓ TC10 PASSED")
    
    # ========================================================================
    # TC11: obliterateShift - Remove first squad
    # ========================================================================
    def test_tc11_obliterate_first_squad(self, commands, sheets_master):
        """TC11: Remove squad 35 from Jan 9."""
        print("\n" + "="*80)
        print("TC11: obliterateShift - Remove first squad")
        print("="*80)
        
        result = commands.execute_command(
            '/?action=obliterateShift&date=20260109&shift_start=1800&shift_end=0600&squad=35'
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 9)
        
        # Squad 35 should not appear
        for shift in modified.shifts:
            squads = self.get_squads_from_shift(shift)
            assert 35 not in squads, "Squad 35 should be removed"
        
        print("✓ TC11 PASSED")
    
    # ========================================================================
    # TC12: addShift - Add fourth squad to 3-squad shift
    # ========================================================================
    def test_tc12_addshift_fourth_squad(self, commands, sheets_master):
        """TC12: Add squad 54 to 3-squad shift on Jan 10."""
        print("\n" + "="*80)
        print("TC12: addShift - Add fourth squad")
        print("="*80)
        
        initial = self.get_day_schedule(sheets_master, 10)
        initial_squads = self.get_squads_from_shift(initial.shifts[0]) if initial.shifts else []
        print(f"Initial squads: {initial_squads}")
        
        result = commands.execute_command(
            '/?action=addShift&date=20260110&shift_start=1800&shift_end=0600&squad=54'
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 10)
        
        # Squad 54 should now be present
        modified_squads = self.get_squads_from_shift(modified.shifts[0])
        assert 54 in modified_squads, "Squad 54 should be added"
        
        print("✓ TC12 PASSED")

"""
# Run all tests
pytest test_calendar_commands_2.py -v -s

# Run specific test
pytest test_calendar_commands_2.py::TestCalendarCommands::test_tc01_nocrew_partial_middle -v -s

# Run with detailed output
pytest test_calendar_commands_2.py -v -s --tb=short
"""

if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
