# calendar_service.py
import os
from fastapi import FastAPI, Request, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
from src.services.calendar_commands import CalendarCommands
from src.models.calendar_models import DaySchedule
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


# Request models for POST endpoints
class ApplyScheduleRequest(BaseModel):
    DaySchedule: str  # JSON string of DaySchedule object
    commands: Optional[str] = None  # Optional description of commands that led to this schedule


class PreviewCommandRequest(BaseModel):
    action: str
    date: str
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None
    squad: Optional[int] = None
    day_schedule: str  # JSON string of DaySchedule object

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


@app.post("/calendar/day/{calendar_date}/apply")
async def apply_external_schedule(calendar_date: str, request: ApplyScheduleRequest):
    """
    Apply an externally provided DaySchedule to the calendar.
    
    Args:
        calendar_date: Date in YYYYMMDD format (e.g., "20251110")
        request: Request body containing DaySchedule JSON
        
    Returns:
        Result with success status and changeId
    """
    try:
        # Parse the DaySchedule from JSON
        day_schedule = DaySchedule.from_json(request.DaySchedule)
        
        # Call apply_external_schedule command
        result = calendar.execute_command(
            action='apply_external_schedule',
            date=calendar_date,
            external_mod_day_schedule=request.DaySchedule,
            commands=request.commands
        )
        
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/calendar/day/{calendar_date}/preview")
async def preview_command(calendar_date: str, request: PreviewCommandRequest):
    """
    Preview a calendar command without applying it to Google Sheets.
    
    Args:
        calendar_date: Date in YYYYMMDD format (e.g., "20251110")
        request: Request body containing command parameters and DaySchedule JSON
        
    Returns:
        Result with modified schedule as JSON
    """
    try:
        # Parse the DaySchedule from JSON
        day_schedule = DaySchedule.from_json(request.day_schedule)
        
        # Build kwargs for execute_command
        kwargs = {
            'date': request.date,
            'day_schedule': day_schedule,
            'preview': True  # Always preview mode for this endpoint
        }
        
        # Add optional parameters
        if request.shift_start:
            kwargs['shift_start'] = request.shift_start
        if request.shift_end:
            kwargs['shift_end'] = request.shift_end
        if request.squad:
            kwargs['squad'] = request.squad
        
        # Execute the command in preview mode
        result = calendar.execute_command(action=request.action, **kwargs)
        
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

# ###########################################
# How to start:
#  uvicorn calendar_service:app --host 0.0.0.0 --port 8000
# ###########################################
