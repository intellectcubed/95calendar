# Local Development Guide

This guide explains how to run the Calendar Service locally while maintaining compatibility with AWS Lambda deployment.

## Dual-Mode Architecture

The Calendar Service supports two deployment modes with **different HTTP handling** but **shared business logic**:

1. **Local Mode**: FastAPI + uvicorn server with `.env` file configuration
   - Uses FastAPI for routing, validation, and developer experience
   - Provides `/docs` endpoint for interactive API documentation
   - Hot reload for development

2. **Lambda Mode**: Simple event handler with Secrets Manager configuration
   - API Gateway handles HTTP routing and parsing
   - Lambda directly processes events (no FastAPI/Mangum)
   - Optimized for fast cold starts and minimal dependencies

**Key Point**: The business logic (`CalendarCommands`) is identical in both modes.
Only the HTTP handling layer differs. See [WHY_NO_FASTAPI_IN_LAMBDA.md](WHY_NO_FASTAPI_IN_LAMBDA.md) for rationale.

## Local Setup

### 1. Install Dependencies

Use the development requirements file which includes all Lambda dependencies plus local development tools:

```bash
# Activate virtual environment
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
SPREADSHEET_ID=your-spreadsheet-id-here
SUPABASE_URL=your-supabase-url-here
SUPABASE_KEY=your-supabase-anon-key-here
```

### 3. Start the Service

```bash
# From project root
uvicorn src.api.calendar_service:app --host 0.0.0.0 --port 8000

# With auto-reload for development
uvicorn src.api.calendar_service:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at: `http://localhost:8000`

## Configuration Manager

The service uses `src/config/aws_config.py` which provides a unified configuration interface:

```python
from src.config.aws_config import config

# Get configuration value (works in both local and Lambda modes)
spreadsheet_id = config.get_required('SPREADSHEET_ID')

# Check if running in Lambda
if config.is_lambda:
    print("Running in AWS Lambda")
else:
    print("Running locally")
```

### How It Works

- **Local Mode**: Loads configuration from `.env` file using `python-dotenv`
- **Lambda Mode**: Loads configuration from AWS Secrets Manager
- Automatic detection based on AWS Lambda environment variables

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_calendar_commands.py
```

### Manual API Testing

```bash
# Get schedule for a day
curl "http://localhost:8000/?action=get_schedule_day&date=20260110"

# Execute noCrew command
curl "http://localhost:8000/?action=noCrew&date=20260110&shift_start=1900&shift_end=2100&squad=34&preview=false"

# List backups
curl "http://localhost:8000/?action=list_backups&date=20260110"

# POST endpoint - Apply schedule
curl -X POST http://localhost:8000/calendar/day/20260110/apply \
  -H 'Content-Type: application/json' \
  -d '{
    "DaySchedule": "<DaySchedule JSON>",
    "commands": "Manual update"
  }'

# POST endpoint - Preview command
curl -X POST http://localhost:8000/calendar/day/20260110/preview \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "noCrew",
    "date": "20260110",
    "shift_start": "1900",
    "shift_end": "2100",
    "squad": 34,
    "day_schedule": "<DaySchedule JSON>"
  }'
```

## Development Workflow

### Making Changes

1. **Edit Code**: Make your changes in `src/`
2. **Test Locally**: Run the service locally with `--reload` flag
3. **Run Tests**: Ensure all tests pass with `pytest`
4. **Test Lambda Mode**: Optionally test in Lambda locally using SAM or LocalStack
5. **Deploy**: Deploy to AWS using deployment scripts

### Adding Dependencies

When adding new Python dependencies:

1. Add to `requirements-lambda.txt` if needed in production
2. Add to `requirements-dev.txt` if only needed for development
3. Rebuild Lambda layer: `./infrastructure/scripts/build-layer.sh`

```bash
# Example: Adding a new production dependency
echo "new-package==1.0.0" >> requirements-lambda.txt
pip install -r requirements-dev.txt

# Rebuild for Lambda deployment
./infrastructure/scripts/build-layer.sh
```

## Requirements Files

The project uses split requirements files:

- **`requirements-lambda.txt`**: Production dependencies for Lambda deployment
  - FastAPI, Pydantic, Google Sheets API, Supabase, boto3, etc.
  - Used by Lambda Layer build script

- **`requirements-dev.txt`**: All dependencies for local development
  - Includes everything from `requirements-lambda.txt`
  - Plus: uvicorn (local server), pytest (testing), etc.
  - Used for local development

- **`requirements.txt`** (legacy): Keep for backwards compatibility or remove

### Which File to Use?

```bash
# Local development
pip install -r requirements-dev.txt

# Lambda deployment (automated by build scripts)
pip install -r requirements-lambda.txt -t layer/python/
```

## Environment Detection

The configuration manager automatically detects the environment:

```python
# In src/config/aws_config.py
def _detect_lambda_environment(self) -> bool:
    return bool(os.environ.get('AWS_EXECUTION_ENV') or
               os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
```

You can also manually check:

```python
from src.config.aws_config import config

if config.is_lambda:
    # Lambda-specific logic
    print("Running in Lambda")
else:
    # Local-specific logic
    print("Running locally")
```

## Debugging

### Enable Debug Logging

```python
# In calendar_service.py, add at the top
import logging
logging.basicConfig(level=logging.DEBUG)
```

### VS Code Launch Configuration

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "src.api.calendar_service:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ],
            "jinja": true,
            "justMyCode": false
        }
    ]
}
```

### Testing Lambda Handler Locally

You can test the Lambda handler locally using the `python-lambda-local` package:

```bash
# Install testing tool
pip install python-lambda-local

# Create test event
cat > test_event.json << EOF
{
    "httpMethod": "GET",
    "path": "/",
    "queryStringParameters": {
        "action": "get_schedule_day",
        "date": "20260110"
    }
}
EOF

# Test Lambda handler locally
python-lambda-local -f lambda_handler src/api/lambda_handler.py test_event.json
```

## Common Issues

### Module Import Errors

If you get import errors:
```bash
# Ensure you're in the project root
cd /Users/george.nowakowski/Projects/python/ems/95calendar

# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements-dev.txt
```

### Port Already in Use

If port 8000 is already in use:
```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)

# Or use a different port
uvicorn src.api.calendar_service:app --port 8001
```

### Configuration Not Loading

Ensure `.env` file exists and is in the project root:
```bash
ls -la .env

# Check environment variables are loading
python -c "from src.config.aws_config import config; print(config.get('SPREADSHEET_ID'))"
```

## Switching Between Local and Lambda

No code changes needed! The same codebase works in both environments:

```bash
# Local development
uvicorn src.api.calendar_service:app --port 8000

# Deploy to Lambda
./infrastructure/scripts/deploy.sh --bucket your-bucket
```

The configuration manager handles the differences automatically.
