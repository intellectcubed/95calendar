import os
from dotenv import load_dotenv
from google_sheets_master import GoogleSheetsMaster

load_dotenv()

# Select spreadsheet based on environment
environment = os.getenv('ENVIRONMENT', 'test')
if environment == 'test':
    spreadsheet_id = os.getenv('TEST_SPREADSHEET_ID')
else:
    spreadsheet_id = os.getenv('PROD_SPREADSHEET_ID')

if not spreadsheet_id:
    raise ValueError(f"{environment.upper()}_SPREADSHEET_ID not found in environment variables")

master = GoogleSheetsMaster()
territories = master.read_territories(spreadsheet_id)
print(territories)