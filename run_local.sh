#!/bin/bash
# Script to run calendar_service locally in TEST mode

echo "Starting Calendar Service in TEST mode..."
echo "========================================="

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Ensure we're using test environment
export ENVIRONMENT=test

# Run the service using uvicorn from the src.api module
uvicorn src.api.calendar_service:app --host 0.0.0.0 --port 8000 --reload
