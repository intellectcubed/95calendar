# Running Calendar Service Locally

This guide explains how to run the calendar_service locally on your Mac.

## Quick Start

### Test Mode (Default - Recommended)

To run the service pointing to the **test calendar**:

```bash
./run_local.sh
```

This will start the service at `http://localhost:8000` using the test Google Calendar and test Supabase instance.

### Production Mode (Use with Caution)

To run the service pointing to the **production calendar**:

```bash
./run_local_prod.sh
```

⚠️ **WARNING**: This connects to the production calendar. The script includes a 5-second delay to give you time to cancel.

## Manual Startup

If you prefer to start the service manually:

```bash
# Activate virtual environment (if you have one)
source venv/bin/activate

# For test mode
export ENVIRONMENT=test
uvicorn src.api.calendar_service:app --host 0.0.0.0 --port 8000 --reload

# For production mode
export ENVIRONMENT=production
uvicorn src.api.calendar_service:app --host 0.0.0.0 --port 8000 --reload
```

**Note**: The run scripts automatically activate the virtual environment if it exists.

## Configuration

The service uses environment variables defined in the `.env` file:

- **ENVIRONMENT**: Set to `test` (default) or `production`
- **TEST_SPREADSHEET_ID**: Google Spreadsheet ID for test calendar
- **PROD_SPREADSHEET_ID**: Google Spreadsheet ID for production calendar
- **TEST_SUPABASE_URL** / **TEST_SUPABASE_KEY**: Test Supabase credentials
- **PROD_SUPABASE_URL** / **PROD_SUPABASE_KEY**: Production Supabase credentials

## Environment Switching

You can switch environments by:

1. **Editing `.env` file**: Change `ENVIRONMENT=test` to `ENVIRONMENT=production`
2. **Using environment variable**: `export ENVIRONMENT=production` before starting
3. **Using the run scripts**: `./run_local.sh` (test) or `./run_local_prod.sh` (production)

## Testing the Service

Once running, you can test the service:

```bash
# Check health
curl http://localhost:8000/docs

# Test a command (example)
curl "http://localhost:8000/?action=get_schedule_day&date=20260110&preview=true"
```

## Prerequisites

Make sure you have:

1. Python 3.14+ installed
2. Virtual environment activated (if using one)
3. Dependencies installed: `pip install -r requirements.txt`
4. Valid Google service account credentials in `config/credentials.json`
5. `.env` file configured with your spreadsheet IDs and Supabase credentials

## Troubleshooting

### Missing Dependencies

```bash
pip install -r requirements.txt
```

### Invalid Credentials

Ensure `config/credentials.json` contains valid Google service account credentials.

### Environment Variables Not Set

Check that your `.env` file has all required variables. See `.env.example` for the template.

### Port Already in Use

If port 8000 is already in use, you can specify a different port:

```bash
uvicorn src.api.calendar_service:app --host 0.0.0.0 --port 8001 --reload
```
