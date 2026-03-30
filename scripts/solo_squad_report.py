#!/usr/bin/env python3
"""
Solo Squad Report
Identifies time slots where only one squad was actively on duty.
"""

import os
import sys
import json
import argparse
import calendar
import time
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from collections import Counter
from typing import List, Dict, Tuple

from src.services.calendar_commands import CalendarCommands
from src.models.calendar_models import DaySchedule


@dataclass
class SoloSegment:
    """A shift segment where only one squad was actively on duty."""
    date_obj: date
    date_display: str
    shift_name: str
    start_time: str
    end_time: str
    solo_squad_id: int
    hours: float


class SoloSquadReporter:
    """Scans historical schedules and reports solo-coverage segments."""

    def __init__(self, is_prod: bool = False, delay: float = 1.0, env_file: str = '.env'):
        from dotenv import load_dotenv
        load_dotenv(env_file)

        self.spreadsheet_id = os.environ.get('SPREADSHEET_ID')
        if not self.spreadsheet_id:
            raise EnvironmentError(
                "SPREADSHEET_ID environment variable is not set.\n"
                "Please set it in .env file or with: export SPREADSHEET_ID='your-spreadsheet-id'"
            )

        self.is_prod = is_prod
        self.delay = delay

        self.commands = CalendarCommands(
            self.spreadsheet_id,
            live_test=(not is_prod)
        )

        if not is_prod:
            print(
                "WARNING: Running in TESTING mode. Schedule data comes from the Testing tab only.\n"
                "         Use --prod for real historical data.\n",
                file=sys.stderr
            )

    def run(self, months_back: int = 0, include_current: bool = False, single_month: str = None):
        """Scan the requested months and print the formatted report.

        Args:
            months_back: Number of past months to scan backward from current month.
            include_current: Include the current (partial) month.
            single_month: A specific month in YYYYMM format to scan.
        """
        if single_month:
            month_dates = self._get_single_month_dates(single_month)
        else:
            month_dates = self._get_month_dates(months_back, include_current)

        # results: dict of (year, month) -> list of SoloSegment
        results: Dict[Tuple[int, int], List[SoloSegment]] = {}
        total_days = sum(len(dates) for dates in month_dates.values())
        scanned = 0

        for (year, month), dates in month_dates.items():
            month_name = calendar.month_name[month]
            segments: List[SoloSegment] = []

            for d in dates:
                scanned += 1
                date_str = d.strftime('%Y%m%d')
                print(
                    f"\rScanning {month_name} {year}... day {d.day} ({scanned}/{total_days})",
                    end='', file=sys.stderr
                )

                try:
                    result = self.commands.execute_command(
                        action='get_schedule_day',
                        date=date_str
                    )

                    if not result.get('success'):
                        print(
                            f"\n  Warning: Could not retrieve schedule for {date_str}: "
                            f"{result.get('error', 'unknown error')}",
                            file=sys.stderr
                        )
                        continue

                    raw = result.get('day_schedule', '{}')
                    day_schedule = DaySchedule.from_json(raw) if isinstance(raw, str) else raw

                    found = self._find_solo_segments(day_schedule, d)
                    segments.extend(found)

                except Exception as e:
                    print(
                        f"\n  Warning: Error processing {date_str}: {e}",
                        file=sys.stderr
                    )

                if scanned < total_days:
                    time.sleep(self.delay)

            print('', file=sys.stderr)  # newline after progress
            results[(year, month)] = segments

        report = self._format_report(results, months_back)
        print(report)

    def _get_month_dates(
        self, months_back: int, include_current: bool
    ) -> Dict[Tuple[int, int], List[date]]:
        """
        Build an ordered dict of (year, month) -> [date, ...] for the requested range.
        Months are ordered most-recent first.
        """
        today = date.today()
        month_dates: Dict[Tuple[int, int], List[date]] = {}

        # Optionally include current (partial) month
        if include_current:
            key = (today.year, today.month)
            month_dates[key] = [
                date(today.year, today.month, d)
                for d in range(1, today.day + 1)
            ]

        # Walk backward from previous month
        cursor_year = today.year
        cursor_month = today.month - 1
        if cursor_month < 1:
            cursor_month = 12
            cursor_year -= 1

        for _ in range(months_back):
            days_in_month = calendar.monthrange(cursor_year, cursor_month)[1]
            key = (cursor_year, cursor_month)
            month_dates[key] = [
                date(cursor_year, cursor_month, d)
                for d in range(1, days_in_month + 1)
            ]

            cursor_month -= 1
            if cursor_month < 1:
                cursor_month = 12
                cursor_year -= 1

        return month_dates

    def _get_single_month_dates(self, yyyymm: str) -> Dict[Tuple[int, int], List[date]]:
        """Build a dict for a single month given in YYYYMM format.

        If the month is the current month, caps dates at today.
        """
        year = int(yyyymm[:4])
        month = int(yyyymm[4:6])
        today = date.today()

        days_in_month = calendar.monthrange(year, month)[1]
        last_day = min(days_in_month, today.day) if (year, month) == (today.year, today.month) else days_in_month

        key = (year, month)
        return {key: [date(year, month, d) for d in range(1, last_day + 1)]}

    def _find_solo_segments(
        self, day_schedule: DaySchedule, date_obj: date
    ) -> List[SoloSegment]:
        """Return SoloSegments for any shift segment with exactly one active squad."""
        solos: List[SoloSegment] = []
        day_abbr = date_obj.strftime('%a')
        date_display = date_obj.strftime(f'%b %d ({day_abbr})')

        for shift in day_schedule.shifts:
            for segment in shift.segments:
                active_squads = [s for s in segment.squads if s.active]
                if len(active_squads) == 1:
                    # Calculate duration, handling overnight spans
                    start_dt = datetime.combine(date_obj, segment.start_time)
                    end_dt = datetime.combine(date_obj, segment.end_time)
                    if end_dt <= start_dt:
                        end_dt += timedelta(days=1)
                    hours = (end_dt - start_dt).total_seconds() / 3600

                    solos.append(SoloSegment(
                        date_obj=date_obj,
                        date_display=date_display,
                        shift_name=shift.name,
                        start_time=segment.start_time.strftime('%H:%M'),
                        end_time=segment.end_time.strftime('%H:%M'),
                        solo_squad_id=active_squads[0].id,
                        hours=hours,
                    ))

        return solos

    def _format_report(
        self,
        results: Dict[Tuple[int, int], List[SoloSegment]],
        months_back: int,
    ) -> str:
        """Build the full text report."""
        lines: List[str] = []
        all_segments: List[SoloSegment] = []

        # Determine period label
        keys = list(results.keys())
        if keys:
            earliest = keys[-1]
            latest = keys[0]
            period_start = f"{calendar.month_name[earliest[1]]} {earliest[0]}"
            period_end = f"{calendar.month_name[latest[1]]} {latest[0]}"
            period = f"{period_start} - {period_end}" if earliest != latest else period_start
        else:
            period = "N/A"

        lines.append("Solo Squad Report")
        lines.append("=================")
        lines.append(f"Period: {period}")
        lines.append(f"Generated: {date.today().isoformat()}")
        lines.append("")

        for (year, month), segments in results.items():
            month_label = f"{calendar.month_name[month]} {year}"
            count = len(segments)
            lines.append(f"--- {month_label} ({count} solo segment{'s' if count != 1 else ''}) ---")

            if segments:
                lines.append(f"  {'Date':<14}  {'Shift':<20}  {'Time Slot':<17}  {'Hours':<7}  Solo Squad")
                lines.append(f"  {'----------':<14}  {'--------------------':<20}  {'-'*17}  {'-'*7}  ----------")
                for seg in segments:
                    time_slot = f"{seg.start_time} - {seg.end_time}"
                    hours_str = f"{seg.hours:g}"
                    lines.append(
                        f"  {seg.date_display:<14}  {seg.shift_name:<20}  {time_slot:<17}  {hours_str:<7}  Squad {seg.solo_squad_id}"
                    )

            lines.append("")
            all_segments.extend(segments)

        # Summary
        lines.append("Summary")
        lines.append("-------")
        total_hours = sum(seg.hours for seg in all_segments)
        lines.append(f"Total solo segments: {len(all_segments)}")
        lines.append(f"Total solo hours: {total_hours:g}")
        lines.append(f"Months scanned: {len(results)}")

        if all_segments:
            freq: Dict[int, int] = Counter()
            hours_by_squad: Dict[int, float] = Counter()
            for seg in all_segments:
                freq[seg.solo_squad_id] += 1
                hours_by_squad[seg.solo_squad_id] += seg.hours
            lines.append("")
            lines.append("Solo frequency by squad:")
            for squad_id, count in freq.most_common():
                h = hours_by_squad[squad_id]
                lines.append(f"  Squad {squad_id}: {count} time{'s' if count != 1 else ''} ({h:g} hrs)")

        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Solo Squad Report - Identify shifts with only one active squad on duty',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan last 6 months (production data)
  PYTHONPATH=. python scripts/solo_squad_report.py --months 6 --prod

  # Scan a specific month
  PYTHONPATH=. python scripts/solo_squad_report.py --month 202510 --prod

  # Scan last 3 months including current partial month
  PYTHONPATH=. python scripts/solo_squad_report.py --months 3 --prod --include-current

  # Save report to file
  PYTHONPATH=. python scripts/solo_squad_report.py --months 6 --prod > solo_report.txt

  # Faster scanning (shorter delay between API calls)
  PYTHONPATH=. python scripts/solo_squad_report.py --months 1 --prod --delay 0.5

Environment Variables:
  SPREADSHEET_ID - Required. The Google Spreadsheet ID to read from.
        """
    )

    range_group = parser.add_mutually_exclusive_group(required=True)
    range_group.add_argument('--months', type=int,
                        help='Number of past months to scan (backward from current month)')
    range_group.add_argument('--month', type=str,
                        help='Specific month to scan in YYYYMM format (e.g., 202510)')
    parser.add_argument('--prod', action='store_true',
                        help='Use production data (default: testing mode)')
    parser.add_argument('--include-current', action='store_true',
                        help='Include the current (partial) month')
    parser.add_argument('--env-file', default='.env',
                        help='Path to env file (default: .env)')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Seconds between API calls (default: 1.0)')

    args = parser.parse_args()

    try:
        reporter = SoloSquadReporter(
            is_prod=args.prod,
            delay=args.delay,
            env_file=args.env_file,
        )
        if args.month:
            reporter.run(single_month=args.month)
        else:
            reporter.run(months_back=args.months, include_current=args.include_current)

    except EnvironmentError as e:
        print(f"\nEnvironment Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nScan interrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
