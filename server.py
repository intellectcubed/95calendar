"""
Server entry point for running the calendar service in Docker.
This replaces the Lambda handler when running as a standalone server.
"""
import uvicorn
from src.api.calendar_service import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
