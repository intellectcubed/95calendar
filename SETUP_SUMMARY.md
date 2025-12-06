# Calendar Service Local Setup - Summary

## What's Been Configured

Your calendar_service is now set up to run locally on your Mac with easy switching between test and production Google Calendars.

## Changes Made

### 1. Environment Configuration (.env)
- Added `ENVIRONMENT` variable (defaults to 'test')
- Separated spreadsheet IDs into `TEST_SPREADSHEET_ID` and `PROD_SPREADSHEET_ID`
- Separated Supabase configs into test and production variants
- Test calendar is now the default

### 2. Service Configuration (src/api/calendar_service.py)
- Modified to read `ENVIRONMENT` variable
- Automatically selects correct spreadsheet ID and Supabase credentials based on environment
- Displays startup message showing which mode (TEST or PRODUCTION) is active

### 3. Run Scripts
- `run_local.sh` - Starts service in TEST mode (safe for development)
- `run_local_prod.sh` - Starts service in PRODUCTION mode (with warning)
- Both scripts automatically activate virtual environment if present

### 4. Documentation
- `RUNNING_LOCALLY.md` - Complete guide for running the service
- `.env.example` - Updated template showing all required variables

## Quick Start

Simply run:

```bash
./run_local.sh
```

The service will start at `http://localhost:8000` and connect to your test calendar.

## Switching to Production

To point to the production calendar:

```bash
./run_local_prod.sh
```

Or manually set the environment variable:

```bash
export ENVIRONMENT=production
./run_local.sh
```

## Testing the Setup

1. Start the service: `./run_local.sh`
2. Check the startup messages - you should see:
   - "🧪 Running in TEST mode"
   - The test spreadsheet ID
   - The test Supabase URL
3. Visit `http://localhost:8000/docs` to see the API documentation
4. Test an endpoint (if you have data in your test calendar)

## Environment Variables

Your `.env` file now contains:

- `ENVIRONMENT` - 'test' or 'production'
- `TEST_SPREADSHEET_ID` - Your test Google Calendar spreadsheet ID
- `PROD_SPREADSHEET_ID` - Your production Google Calendar spreadsheet ID
- `TEST_SUPABASE_URL` / `TEST_SUPABASE_KEY` - Test Supabase credentials
- `PROD_SUPABASE_URL` / `PROD_SUPABASE_KEY` - Production Supabase credentials

## Safety Features

1. **Default to Test**: The environment defaults to 'test' mode
2. **Production Warning**: Running in production mode shows a warning with 5-second delay
3. **Clear Indicators**: Startup messages clearly show which environment is active
4. **Separate Credentials**: Test and production use completely separate Google Calendars and Supabase instances

## Next Steps

1. Verify your `.env` file has the correct spreadsheet IDs and Supabase credentials
2. Ensure `config/credentials.json` contains valid Google service account credentials
3. Run `./run_local.sh` to start in test mode
4. Test the API endpoints using the Swagger UI at `http://localhost:8000/docs`

## Need Help?

See `RUNNING_LOCALLY.md` for detailed instructions and troubleshooting.
