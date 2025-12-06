#!/bin/bash
# Script to run calendar_service locally in PRODUCTION mode
# WARNING: This will connect to the production Google Calendar and Supabase!

echo "⚠️  WARNING: Starting Calendar Service in PRODUCTION mode ⚠️"
echo "============================================================="
echo "This will connect to the PRODUCTION Google Calendar and Supabase."
echo "Press Ctrl+C within 5 seconds to cancel..."
sleep 5

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Set environment to production
export ENVIRONMENT=production

# Run the service using uvicorn from the src.api module
uvicorn src.api.calendar_service:app --host 0.0.0.0 --port 8000 --reload
