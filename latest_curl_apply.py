#!/usr/bin/env python3
"""
Generate curl command from latest PreviewState JSON file.
Reads the most recent PreviewState.json file and creates a curl command to apply it.
"""

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path


def find_latest_preview_state():
    """Find the latest PreviewState JSON file in the ~/Downloads directory."""
    downloads_dir = Path.home() / 'Downloads'
    
    # Find all PreviewState files
    preview_files = []
    
    # Check for PreviewState.json
    if (downloads_dir / 'PreviewState.json').exists():
        preview_files.append((str(downloads_dir / 'PreviewState.json'), 0))
    
    # Check for numbered versions: PreviewState (1).json, PreviewState (2).json, etc.
    for file in downloads_dir.glob('PreviewState*.json'):
        filename = file.name
        # Match pattern: PreviewState (N).json
        match = re.match(r'PreviewState \((\d+)\)\.json', filename)
        if match:
            number = int(match.group(1))
            preview_files.append((str(file), number))
    
    if not preview_files:
        return None
    
    # Sort by number and get the highest
    preview_files.sort(key=lambda x: x[1], reverse=True)
    return preview_files[0][0]


def parse_date_from_day_field(day_field):
    """
    Parse date from day field like 'Sunday 2026-03-15' and return YYYYMMDD format.
    
    Args:
        day_field: String like "Sunday 2026-03-15" or "2026-03-15"
    
    Returns:
        String in YYYYMMDD format like "20260315"
    """
    # Extract date portion (YYYY-MM-DD)
    date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', day_field)
    if date_match:
        year, month, day = date_match.groups()
        return f"{year}{month}{day}"
    
    raise ValueError(f"Could not parse date from day field: {day_field}")


def escape_json_for_curl(json_str):
    """
    Escape JSON string for use in curl command.
    Escapes double quotes and backslashes.
    """
    # Escape backslashes first, then double quotes
    escaped = json_str.replace('\\', '\\\\').replace('"', '\\"')
    return escaped


def generate_curl_command(preview_data):
    """
    Generate curl command from preview state data.
    
    Args:
        preview_data: Dictionary containing the preview state
    
    Returns:
        String containing the curl command
    """
    # Extract date from day field
    day_field = preview_data.get('day', '')
    date_yyyymmdd = parse_date_from_day_field(day_field)
    
    # Convert preview data to JSON string
    json_str = json.dumps(preview_data)
    
    # Escape for curl
    escaped_json = escape_json_for_curl(json_str)
    
    # Build curl command
    curl_command = f'''curl -X POST http://localhost:8000/calendar/day/{date_yyyymmdd}/apply \\
  -H 'Content-Type: application/json' \\
  -d '{{"DaySchedule": "{escaped_json}"}}'
'''
    
    return curl_command


def copy_to_clipboard(text):
    """
    Copy text to clipboard using pbcopy (macOS).
    
    Args:
        text: String to copy to clipboard
    
    Returns:
        True if successful, False otherwise
    """
    try:
        process = subprocess.Popen(
            ['pbcopy'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        process.communicate(text.encode('utf-8'))
        return process.returncode == 0
    except Exception as e:
        print(f"Error copying to clipboard: {e}")
        return False


def main():
    """Main function."""
    print("Looking for latest PreviewState JSON file in ~/Downloads...")
    
    # Find latest file
    latest_file = find_latest_preview_state()
    
    if not latest_file:
        print("❌ No PreviewState JSON files found in ~/Downloads directory.")
        print("   Expected files: PreviewState.json, PreviewState (1).json, etc.")
        return 1
    
    print(f"✓ Found: {Path(latest_file).name}")
    
    # Read the file
    try:
        with open(latest_file, 'r') as f:
            preview_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading {latest_file}: {e}")
        return 1
    
    print(f"✓ Loaded preview state for: {preview_data.get('day', 'unknown date')}")
    
    # Generate curl command
    try:
        curl_command = generate_curl_command(preview_data)
    except Exception as e:
        print(f"❌ Error generating curl command: {e}")
        return 1
    
    print(f"✓ Generated curl command")
    
    # Copy to clipboard
    if copy_to_clipboard(curl_command):
        print("✓ Curl command copied to clipboard!")
        print("\nYou can now paste and run the command to apply the schedule.")
        print("\nPreview of command:")
        print("-" * 80)
        # Show first 500 characters
        if len(curl_command) > 500:
            print(curl_command[:500] + "...")
        else:
            print(curl_command)
        print("-" * 80)
    else:
        print("⚠ Could not copy to clipboard, but here's the command:")
        print("-" * 80)
        print(curl_command)
        print("-" * 80)
    
    return 0


if __name__ == "__main__":
    exit(main())
