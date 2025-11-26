#!/usr/bin/env python3
"""
Example client for calling the Calendar Service Lambda API with IAM authentication.

Requirements:
    pip install requests requests-aws4auth boto3

Usage:
    # Set your API URL
    export API_URL="https://your-api-id.execute-api.us-east-1.amazonaws.com/v1"

    # Run
    python lambda_client.py
"""

import os
import json
import requests
from requests_aws4auth import AWS4Auth
import boto3


class CalendarServiceClient:
    """Client for Calendar Service Lambda API with IAM authentication."""

    def __init__(self, api_url: str, region: str = 'us-east-1'):
        """
        Initialize client.

        Args:
            api_url: Base URL of the API (e.g., https://xxx.execute-api.us-east-1.amazonaws.com/v1)
            region: AWS region where API is deployed
        """
        self.api_url = api_url.rstrip('/')
        self.region = region
        self.auth = self._get_auth()

    def _get_auth(self):
        """Get AWS4Auth using boto3 credentials."""
        # Get credentials from boto3 (uses ~/.aws/credentials or environment variables)
        session = boto3.Session()
        credentials = session.get_credentials()

        return AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.region,
            'execute-api',
            session_token=credentials.token
        )

    def get_schedule_day(self, date: str) -> dict:
        """
        Get schedule for a specific day.

        Args:
            date: Date in YYYYMMDD format (e.g., "20260110")

        Returns:
            API response as dict
        """
        url = f"{self.api_url}/?action=get_schedule_day&date={date}"
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()

    def no_crew(self, date: str, shift_start: str, shift_end: str, squad: int, preview: bool = False) -> dict:
        """
        Mark a squad as having no crew for specified time window.

        Args:
            date: Date in YYYYMMDD format
            shift_start: Start time in HHMM format
            shift_end: End time in HHMM format
            squad: Squad number
            preview: If True, preview changes without applying

        Returns:
            API response as dict
        """
        url = (
            f"{self.api_url}/"
            f"?action=noCrew"
            f"&date={date}"
            f"&shift_start={shift_start}"
            f"&shift_end={shift_end}"
            f"&squad={squad}"
            f"&preview={'true' if preview else 'false'}"
        )
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()

    def add_shift(self, date: str, shift_start: str, shift_end: str, squad: int, preview: bool = False) -> dict:
        """
        Add a squad for specified time window.

        Args:
            date: Date in YYYYMMDD format
            shift_start: Start time in HHMM format
            shift_end: End time in HHMM format
            squad: Squad number
            preview: If True, preview changes without applying

        Returns:
            API response as dict
        """
        url = (
            f"{self.api_url}/"
            f"?action=addShift"
            f"&date={date}"
            f"&shift_start={shift_start}"
            f"&shift_end={shift_end}"
            f"&squad={squad}"
            f"&preview={'true' if preview else 'false'}"
        )
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()

    def list_backups(self, date: str) -> dict:
        """
        List all backups for a specific date.

        Args:
            date: Date in YYYYMMDD format

        Returns:
            API response with list of backups
        """
        url = f"{self.api_url}/?action=list_backups&date={date}"
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()

    def rollback(self, date: str, change_id: str) -> dict:
        """
        Rollback to a previous snapshot.

        Args:
            date: Date in YYYYMMDD format
            change_id: Change/snapshot ID to rollback to

        Returns:
            API response as dict
        """
        url = f"{self.api_url}/?action=rollback&date={date}&change_id={change_id}"
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()

    def apply_schedule(self, date: str, day_schedule_json: str, commands: str = None) -> dict:
        """
        Apply an externally provided DaySchedule.

        Args:
            date: Date in YYYYMMDD format
            day_schedule_json: JSON string of DaySchedule object
            commands: Optional description of commands

        Returns:
            API response as dict
        """
        url = f"{self.api_url}/calendar/day/{date}/apply"
        payload = {
            "DaySchedule": day_schedule_json,
            "commands": commands
        }
        response = requests.post(url, json=payload, auth=self.auth)
        response.raise_for_status()
        return response.json()

    def preview_command(self, date: str, action: str, day_schedule_json: str,
                       shift_start: str = None, shift_end: str = None, squad: int = None) -> dict:
        """
        Preview a command without applying it.

        Args:
            date: Date in YYYYMMDD format
            action: Action to preview (e.g., "noCrew", "addShift")
            day_schedule_json: JSON string of current DaySchedule
            shift_start: Optional start time in HHMM format
            shift_end: Optional end time in HHMM format
            squad: Optional squad number

        Returns:
            API response with previewed changes
        """
        url = f"{self.api_url}/calendar/day/{date}/preview"
        payload = {
            "action": action,
            "date": date,
            "day_schedule": day_schedule_json
        }

        if shift_start:
            payload["shift_start"] = shift_start
        if shift_end:
            payload["shift_end"] = shift_end
        if squad is not None:
            payload["squad"] = squad

        response = requests.post(url, json=payload, auth=self.auth)
        response.raise_for_status()
        return response.json()


def main():
    """Example usage."""
    # Get API URL from environment
    api_url = os.environ.get('API_URL')
    if not api_url:
        print("Error: Set API_URL environment variable")
        print("Example: export API_URL='https://xxx.execute-api.us-east-1.amazonaws.com/v1'")
        return

    # Initialize client
    client = CalendarServiceClient(api_url)

    # Example 1: Get schedule for a day
    print("Example 1: Get schedule for January 10, 2026")
    try:
        result = client.get_schedule_day("20260110")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

    # Example 2: Mark squad as no crew (preview mode)
    print("\nExample 2: Preview marking squad 34 as no crew")
    try:
        result = client.no_crew(
            date="20260110",
            shift_start="1900",
            shift_end="2100",
            squad=34,
            preview=True
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

    # Example 3: List backups
    print("\nExample 3: List backups for January 10, 2026")
    try:
        result = client.list_backups("20260110")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
