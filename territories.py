import os
from dotenv import load_dotenv
from google_sheets_master import GoogleSheetsMaster

load_dotenv()

spreadsheet_id = os.getenv('SPREADSHEET_ID')
if not spreadsheet_id:
    raise ValueError("SPREADSHEET_ID not found in environment variables")

master = GoogleSheetsMaster()
territories = master.read_territories(spreadsheet_id)
print(territories)