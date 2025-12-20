#!/usr/bin/env python3
"""
Comprehensive Test Suite for CalendarCommands
Based on TestCommandsSpec.txt - Tests all permutations of add/remove/obliterate operations
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports
# Use explicit path to ensure .env is found regardless of where pytest is run from
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

import pytest
from datetime import time
from src.services.calendar_commands import CalendarCommands
from src.models.calendar_models import Squad, ShiftSegment, Shift, DaySchedule
from src.integrations.google_sheets_master import GoogleSheetsMaster

# Test configuration
SPREADSHEET_ID = os.getenv('TEST_SPREADSHEET_ID')
if not SPREADSHEET_ID:
    raise ValueError("TEST_SPREADSHEET_ID not found in environment variables")
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
        return GoogleSheetsMaster('config/credentials.json', live_test=True)
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_calendar(self, sheets_master):
        """
        Setup: Populate the Testing tab with initial squad configurations.
        This runs once before all tests in the class.
        """
        from src.services.calendar_builder import load_template, generate_month_schedule, assign_territories, assign_tango
        
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

    def build_expected_schedule(self, day: str, shifts_spec: list) -> DaySchedule:
        """
        Build an expected DaySchedule from a simplified specification.

        Args:
            day: Day string (e.g., "Saturday 2026-01-11")
            shifts_spec: List of shift specifications, where each shift is a dict:
                {
                    'start': '1800',  # HHMM format
                    'end': '0600',    # HHMM format
                    'tango': 42,
                    'squads': [
                        {'id': 35, 'territories': [], 'active': False},
                        {'id': 42, 'territories': [42, 54], 'active': True}
                    ]
                }

        Returns:
            DaySchedule object
        """
        shifts = []

        for shift_spec in shifts_spec:
            # Parse times
            start_str = shift_spec['start']
            end_str = shift_spec['end']
            start_time = time(int(start_str[:2]), int(start_str[2:]))
            end_time = time(int(end_str[:2]), int(end_str[2:]))

            # Build squads
            squads = []
            for squad_spec in shift_spec['squads']:
                squad = Squad(
                    id=squad_spec['id'],
                    territories=squad_spec.get('territories', []),
                    active=squad_spec.get('active', True)
                )
                squads.append(squad)

            # Create segment (one segment per shift in this simplified model)
            segment = ShiftSegment(
                start_time=start_time,
                end_time=end_time,
                squads=squads
            )

            # Create shift with name based on times
            shift_name = shift_spec.get('name', f'{start_time.strftime("%H:%M")} - {end_time.strftime("%H:%M")} Shift')

            shift = Shift(
                name=shift_name,
                start_time=start_time,
                end_time=end_time,
                segments=[segment],
                tango=shift_spec.get('tango', squads[0].id if squads else 0)
            )

            shifts.append(shift)

        return DaySchedule(day=day, shifts=shifts)

    def assert_schedules_equal(self, expected: DaySchedule, actual: DaySchedule, message: str = "") -> tuple:
        """
        Compare two DaySchedule objects and return whether they're equal.

        Args:
            expected: The expected DaySchedule
            actual: The actual DaySchedule to compare
            message: Optional message prefix for differences

        Returns:
            Tuple of (is_equal: bool, differences: str)
            If equal, differences will be empty string
            If not equal, differences contains detailed explanation
        """
        differences = []
        prefix = f"{message}: " if message else ""

        # Compare day names
        if expected.day != actual.day:
            differences.append(f"{prefix}Day name mismatch: expected '{expected.day}', got '{actual.day}'")

        # Compare number of shifts
        if len(expected.shifts) != len(actual.shifts):
            differences.append(
                f"{prefix}Number of shifts mismatch: expected {len(expected.shifts)}, got {len(actual.shifts)}"
            )
            # If shift counts differ, we can't compare individual shifts meaningfully
            return (False, "\n".join(differences))

        # Compare each shift
        for i, (exp_shift, act_shift) in enumerate(zip(expected.shifts, actual.shifts)):
            shift_prefix = f"{prefix}Shift {i}"

            # Compare shift properties
            if exp_shift.name != act_shift.name:
                differences.append(f"{shift_prefix}: name mismatch: expected '{exp_shift.name}', got '{act_shift.name}'")

            if exp_shift.start_time != act_shift.start_time:
                differences.append(
                    f"{shift_prefix}: start_time mismatch: expected {exp_shift.start_time}, got {act_shift.start_time}"
                )

            if exp_shift.end_time != act_shift.end_time:
                differences.append(
                    f"{shift_prefix}: end_time mismatch: expected {exp_shift.end_time}, got {act_shift.end_time}"
                )

            if exp_shift.tango != act_shift.tango:
                differences.append(f"{shift_prefix}: tango mismatch: expected {exp_shift.tango}, got {act_shift.tango}")

            # Compare segments
            if len(exp_shift.segments) != len(act_shift.segments):
                differences.append(
                    f"{shift_prefix}: number of segments mismatch: expected {len(exp_shift.segments)}, got {len(act_shift.segments)}"
                )
                continue  # Skip segment comparison if counts differ

            for j, (exp_seg, act_seg) in enumerate(zip(exp_shift.segments, act_shift.segments)):
                seg_prefix = f"{shift_prefix}, Segment {j}"

                # Compare segment times
                if exp_seg.start_time != act_seg.start_time:
                    differences.append(
                        f"{seg_prefix}: start_time mismatch: expected {exp_seg.start_time}, got {act_seg.start_time}"
                    )

                if exp_seg.end_time != act_seg.end_time:
                    differences.append(
                        f"{seg_prefix}: end_time mismatch: expected {exp_seg.end_time}, got {act_seg.end_time}"
                    )

                # Compare squads
                if len(exp_seg.squads) != len(act_seg.squads):
                    differences.append(
                        f"{seg_prefix}: number of squads mismatch: expected {len(exp_seg.squads)}, got {len(act_seg.squads)}"
                    )
                    # Show which squads are present
                    exp_squad_ids = sorted([s.id for s in exp_seg.squads])
                    act_squad_ids = sorted([s.id for s in act_seg.squads])
                    differences.append(f"{seg_prefix}: expected squad IDs {exp_squad_ids}, got {act_squad_ids}")
                    continue  # Skip individual squad comparison if counts differ

                # Sort squads by ID for consistent comparison
                exp_squads_sorted = sorted(exp_seg.squads, key=lambda s: s.id)
                act_squads_sorted = sorted(act_seg.squads, key=lambda s: s.id)

                for k, (exp_squad, act_squad) in enumerate(zip(exp_squads_sorted, act_squads_sorted)):
                    squad_prefix = f"{seg_prefix}, Squad {k}"

                    # Compare squad properties
                    if exp_squad.id != act_squad.id:
                        differences.append(
                            f"{squad_prefix}: id mismatch: expected {exp_squad.id}, got {act_squad.id}"
                        )

                    if sorted(exp_squad.territories) != sorted(act_squad.territories):
                        differences.append(
                            f"{squad_prefix} (id={exp_squad.id}): territories mismatch: "
                            f"expected {sorted(exp_squad.territories)}, got {sorted(act_squad.territories)}"
                        )

                    if exp_squad.active != act_squad.active:
                        differences.append(
                            f"{squad_prefix} (id={exp_squad.id}): active mismatch: "
                            f"expected {exp_squad.active}, got {act_squad.active}"
                        )

        is_equal = len(differences) == 0
        differences_str = "\n".join(differences) if differences else ""

        return (is_equal, differences_str)

    def clear_day(self, commands, sheets_master, day):
        """
        Clear all squads from a given day by obliterating all shifts.

        Args:
            commands: CalendarCommands instance
            sheets_master: GoogleSheetsMaster instance
            day: Day number (1-31)
        """
        print(f"\nClearing all squads from day {day}...")

        # Get the current schedule for the day
        schedule = self.get_day_schedule(sheets_master, day)

        if not schedule or not schedule.shifts:
            print(f"  Day {day} is already empty")
            return

        # Collect all unique squad/shift combinations to obliterate
        obliterations = []
        for shift in schedule.shifts:
            shift_start = shift.start_time
            shift_end = shift.end_time

            # Get all unique squads in this shift
            squad_ids = set()
            for segment in shift.segments:
                for squad in segment.squads:
                    squad_ids.add(squad.id)

            # Add obliteration for each squad
            for squad_id in squad_ids:
                obliterations.append({
                    'squad_id': squad_id,
                    'shift_start': shift_start.strftime('%H%M'),
                    'shift_end': shift_end.strftime('%H%M')
                })

        # Execute obliterations
        print(f"  Found {len(obliterations)} squad/shift combination(s) to remove:")
        for obl in obliterations:
            print(f"    Squad {obl['squad_id']}: {obl['shift_start']}-{obl['shift_end']}")

            result = commands.execute_command(
                action='obliterateShift',
                date=f'202601{day:02d}',  # Format as YYYYMMDD (January 2026)
                shift_start=obl['shift_start'],
                shift_end=obl['shift_end'],
                squad=obl['squad_id'],
                preview=False
            )

            if not result['success']:
                print(f"  ✗ Failed to obliterate squad {obl['squad_id']}: {result}")
            else:
                print(f"  ✓ Obliterated squad {obl['squad_id']}")

        print(f"✓ Day {day} cleared")

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
            action='noCrew',
            date='20260101',
            shift_start='1900',
            shift_end='2100',
            squad=42,
            preview=False
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
            action='noCrew',
            date='20260102',
            shift_start='1800',
            shift_end='0600',
            squad=35,
            preview=False
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
            action='obliterateShift',
            date='20260103',
            shift_start='0600',
            shift_end='0600',
            squad=35,
            preview=False
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
            action='noCrew',
            date='20260103',
            shift_start='0000',
            shift_end='0300',
            squad=43,
            preview=False
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
            action='addShift',
            date='20260104',
            shift_start='1800',
            shift_end='0600',
            squad=43,
            preview=False
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
            action='noCrew',
            date='20260105',
            shift_start='2200',
            shift_end='0600',
            squad=initial_tango,
            preview=False
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
            action='addShift',
            date='20260106',
            shift_start='0600',
            shift_end='1800',
            squad=34,
            preview=False
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
            action='obliterateShift',
            date='20260107',
            shift_start='1800',
            shift_end='0600',
            squad=43,
            preview=False
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
            action='addShift',
            date='20260108',
            shift_start='2000',
            shift_end='0000',
            squad=35,
            preview=False
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
            action='noCrew',
            date='20260108',
            shift_start='2000',
            shift_end='0000',
            squad=34,
            preview=False
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
            action='obliterateShift',
            date='20260109',
            shift_start='1800',
            shift_end='0600',
            squad=35,
            preview=False
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
            action='addShift',
            date='20260110',
            shift_start='1800',
            shift_end='0600',
            squad=54,
            preview=False
        )
        assert result['success'], f"Command failed: {result}"
        
        modified = self.get_day_schedule(sheets_master, 10)
        
        # Squad 54 should now be present
        modified_squads = self.get_squads_from_shift(modified.shifts[0])
        assert 54 in modified_squads, "Squad 54 should be added"
        
        print("✓ TC12 PASSED")

    # ========================================================================
    # TC13: 
    # ========================================================================
    # def test_tc13_test_hourly_grid_respects_active_flag(self, commands, sheets_master):
    #     """TC13: test_hourly_grid_respects_active_flag on Jan 12."""
    #     print("\n" + "="*80)
    #     print("TC13: addShift - Add fourth squad")
    #     print("="*80)
        
    #     self.clear_day(commands, sheets_master, 12)

    #     result = commands.execute_command(
    #         action='addShift',
    #         date='20260112',
    #         shift_start='1800',
    #         shift_end='0600',
    #         squad=35,
    #         preview=False
    #     )

    #     result = commands.execute_command(
    #         action='addShift',
    #         date='20260112',
    #         shift_start='1800',
    #         shift_end='0600',
    #         squad=42,
    #         preview=False
    #     )

    #     result = commands.execute_command(
    #         action='noCrew',
    #         date='20260112',
    #         shift_start='1800',
    #         shift_end='0600',
    #         squad=35,
    #         preview=False
    #     )

    #     result = commands.execute_command(
    #         action='addShift',
    #         date='20260112',
    #         shift_start='2200',
    #         shift_end='0600',
    #         squad=43,
    #         preview=False
    #     )

    #     actual = self.get_day_schedule(sheets_master, 12)

    #     # Create expected DaySchedule object
    #     # Day: 1/11/2026
    #     # Shift 1: 1800-2200 with Squad 35 (inactive), Squad 42 (active)
    #     # Shift 2: 2200-0600 with Squad 35 (active), Squad 42 (active)
    #     # expected = self.build_expected_schedule(
    #     #     day="Saturday 2026-01-11",
    #     #     shifts_spec=[
    #     #         {
    #     #             'start': '1800',
    #     #             'end': '2200',
    #     #             'tango': 42,
    #     #             'squads': [
    #     #                 {'id': 35, 'territories': [], 'active': False},
    #     #                 {'id': 42, 'territories': [42, 54], 'active': True}
    #     #             ]
    #     #         },
    #     #         {
    #     #             'start': '2200',
    #     #             'end': '0600',
    #     #             'tango': 35,
    #     #             'squads': [
    #     #                 {'id': 35, 'territories': [35, 43], 'active': True},
    #     #                 {'id': 42, 'territories': [42, 54], 'active': True}
    #     #             ]
    #     #         }
    #     #     ]
    #     # )

    #     expected = self.build_expected_schedule(
    #         day="Monday 2026-01-12",
    #         shifts_spec=[
    #             {
    #                 'start': '1800',
    #                 'end': '2200',
    #                 'tango': 42,
    #                 'squads': [
    #                     {'id': 35, 'territories': [], 'active': False},
    #                     {'id': 42, 'territories': [34, 35, 42, 43, 54], 'active': True}
    #                 ]
    #             },
    #             {
    #                 'start': '2200',
    #                 'end': '0600',
    #                 'tango': 42,
    #                 'squads': [
    #                     {'id': 35, 'territories': [], 'active': False},
    #                     {'id': 42, 'territories': [35, 42, 54], 'active': True},
    #                     {'id': 43, 'territories': [34, 43], 'active': True}
    #                 ]
    #             }
    #         ]
    #     )


    #     # Compare expected vs actual
    #     is_equal, differences = self.assert_schedules_equal(expected, actual, "TC13")

    #     if not is_equal:
    #         print("\n" + "="*80)
    #         print("SCHEDULE COMPARISON FAILED:")
    #         print("="*80)
    #         print(differences)
    #         print("\nActual schedule:")
    #         print(actual)

    #     assert is_equal, f"Schedules should match:\n{differences}"

    #     print("✓ TC13 PASSED")


    # ========================================================================
    # TC13: 
    # ========================================================================
    def test_tc14_test_hourly_grid_respects_active_flag(self, commands, sheets_master):
        """TC13: test_hourly_grid_respects_active_flag on Jan 13."""
        print("\n" + "="*80)
        print("TC14: addShift - Add fourth squad")
        print("="*80)
        
        # self.clear_day(commands, sheets_master, 13)

        # result = commands.execute_command(
        #     action='addShift',
        #     date='20260113',
        #     shift_start='1800',
        #     shift_end='0600',
        #     squad=35,
        #     preview=False
        # )

        # result = commands.execute_command(
        #     action='addShift',
        #     date='20260113',
        #     shift_start='1800',
        #     shift_end='0600',
        #     squad=42,
        #     preview=False
        # )

        result = commands.execute_command(
            action='noCrew',
            date='20260113',
            shift_start='1800',
            shift_end='0600',
            squad=54,
            preview=False
        )

        result = commands.execute_command(
            action='addShift',
            date='20260113',
            shift_start='2200',
            shift_end='0600',
            squad=54,
            preview=False
        )

        actual = self.get_day_schedule(sheets_master, 13)

        # Create expected DaySchedule object
        # Day: 1/11/2026
        # Shift 1: 1800-2200 with Squad 35 (inactive), Squad 42 (active)
        # Shift 2: 2200-0600 with Squad 35 (active), Squad 42 (active)
        expected = self.build_expected_schedule(
            day="Tuesday 2026-01-13",
            shifts_spec=[
                {
                    'start': '1800',
                    'end': '2200',
                    'tango': 43,
                    'squads': [
                        {'id': 54, 'territories': [], 'active': False},
                        {'id': 43, 'territories': [34, 35, 42, 43, 54], 'active': True}
                    ]
                },
                {
                    'start': '2200',
                    'end': '0600',
                    'tango': 43,
                    'squads': [
                        {'id': 43, 'territories': [34, 43], 'active': True},
                        {'id': 54, 'territories': [35, 42, 54], 'active': True}
                    ]
                }
            ]
        )

        # expected = self.build_expected_schedule(
        #     day="Monday 2026-01-12",
        #     shifts_spec=[
        #         {
        #             'start': '1800',
        #             'end': '2200',
        #             'tango': 42,
        #             'squads': [
        #                 {'id': 35, 'territories': [], 'active': False},
        #                 {'id': 42, 'territories': [34, 35, 42, 43, 54], 'active': True}
        #             ]
        #         },
        #         {
        #             'start': '2200',
        #             'end': '0600',
        #             'tango': 42,
        #             'squads': [
        #                 {'id': 35, 'territories': [], 'active': False},
        #                 {'id': 42, 'territories': [35, 42, 54], 'active': True},
        #                 {'id': 43, 'territories': [34, 43], 'active': True}
        #             ]
        #         }
        #     ]
        # )


        # Compare expected vs actual
        is_equal, differences = self.assert_schedules_equal(expected, actual, "TC14")

        if not is_equal:
            print("\n" + "="*80)
            print("SCHEDULE COMPARISON FAILED:")
            print("="*80)
            print(differences)
            print("\nActual schedule:")
            print(actual)

        assert is_equal, f"Schedules should match:\n{differences}"

        print("✓ TC14 PASSED")




"""
# Run all tests
pytest test_calendar_commands.py -v -s

# Run specific test
pytest test_calendar_commands.py::TestCalendarCommands::test_tc01_nocrew_partial_middle -v -s

# Run with detailed output
pytest test_calendar_commands.py -v -s --tb=short
"""

if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
