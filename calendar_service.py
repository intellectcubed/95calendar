# calendar_service.py
import os
from fastapi import FastAPI, Request
from calendar_commands import CalendarCommands
from dotenv import load_dotenv

load_dotenv()

spreadsheet_id = os.environ.get('SPREADSHEET_ID')
if not spreadsheet_id:
    raise EnvironmentError(
        "SPREADSHEET_ID environment variable is not set.\n"
        "Please set it in .env file or with: export SPREADSHEET_ID='your-spreadsheet-id'"
    )

app = FastAPI(title="Calendar Command Service")
calendar = CalendarCommands(spreadsheet_id, live_test=False)

@app.get("/")
async def execute(request: Request):
    """
    Handle command URL of format:
    /?action=noCrew&date=20251110&shift_start=1800&shift_end=0600&squad=42&preview=false
    """
    params = dict(request.query_params)
    action = params.pop("action", None)
    if not action:
        return {"status": "error", "message": "Missing 'action' parameter"}

    try:
        # Convert string parameters to appropriate types
        if "squad" in params:
            params["squad"] = int(params["squad"])
        
        # Convert preview parameter from string to boolean
        if "preview" in params:
            preview_str = params["preview"].lower()
            params["preview"] = preview_str in ("true", "1", "yes")
        
        result = calendar.execute_command(action, **params)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
