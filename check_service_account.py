#!/usr/bin/env python3
"""
Check service account credentials
"""

import json

with open('credentials.json', 'r') as f:
    creds = json.load(f)

print("Service Account Information:")
print("="*60)
print(f"Type: {creds.get('type')}")
print(f"Project ID: {creds.get('project_id')}")
print(f"Service Account Email: {creds.get('client_email')}")
print("="*60)
print("\nTo grant access to your Google Spreadsheet:")
print("1. Open the spreadsheet in Google Sheets")
print("2. Click 'Share' button")
print(f"3. Add this email: {creds.get('client_email')}")
print("4. Give it 'Editor' permissions")
print("5. Click 'Send' or 'Done'")
