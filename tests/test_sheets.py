#!/usr/bin/env python3
"""
Test script for GoogleSheetsMaster
"""

from src.integrations.google_sheets_master import GoogleSheetsMaster

# Test authentication
try:
    print("Initializing GoogleSheetsMaster...")
    master = GoogleSheetsMaster('config/credentials.json')
    print("✓ Authentication successful!")
    print(f"✓ Service account: mrscoveragewebsite@appspot.gserviceaccount.com")
    print("\nTo test reading territories, provide a spreadsheet ID:")
    print("  python test_sheets.py <spreadsheet-id>")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
