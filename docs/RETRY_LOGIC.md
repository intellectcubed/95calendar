# Google Sheets API Retry Logic

## Overview

The `GoogleSheetsMaster` class now includes automatic retry logic with exponential backoff to handle rate limiting (HTTP 429 errors) from the Google Sheets API.

## Configuration

You can configure the retry behavior when initializing `GoogleSheetsMaster`:

```python
from google_sheets_master import GoogleSheetsMaster

# Default configuration (5 retries, 5 second base backoff)
sheets = GoogleSheetsMaster('credentials.json')

# Custom configuration
sheets = GoogleSheetsMaster(
    'credentials.json',
    max_retries=10,              # Retry up to 10 times
    retry_backoff_seconds=3.0    # Start with 3 second backoff
)
```

## Parameters

### max_retries
- **Type:** int
- **Default:** 5
- **Description:** Maximum number of retry attempts when encountering a 429 rate limit error

### retry_backoff_seconds
- **Type:** float
- **Default:** 5.0
- **Description:** Base backoff time in seconds. The actual wait time uses exponential backoff:
  - Attempt 1: 5 seconds
  - Attempt 2: 10 seconds
  - Attempt 3: 20 seconds
  - Attempt 4: 40 seconds
  - Attempt 5: 80 seconds

## How It Works

1. When any Google Sheets API call is made, it's wrapped with retry logic
2. If the API returns HTTP 429 (Too Many Requests), the system:
   - Waits for `retry_backoff_seconds * (2 ^ attempt_number)` seconds
   - Retries the request
   - Repeats up to `max_retries` times
3. If all retries are exhausted, the original error is raised
4. Non-429 errors are raised immediately without retry

## Affected Operations

All Google Sheets API operations are protected with retry logic:
- `read_territories()` - Reading territory assignments
- `populate_calendar()` - Populating calendar data
- `get_day()` - Reading a single day's schedule
- `put_day()` - Writing a single day's schedule
- All formatting operations (red text for [No Crew])

## Example Output

When rate limiting occurs, you'll see console output like:

```
Rate limit hit (429). Retrying in 5.0 seconds... (attempt 1/5)
Rate limit hit (429). Retrying in 10.0 seconds... (attempt 2/5)
Successfully updated day 15 in 'January 2026' (40 cells)
```

## Best Practices

1. **For bulk operations:** Increase `max_retries` to handle longer rate limit periods
2. **For time-sensitive operations:** Decrease `retry_backoff_seconds` for faster retries
3. **For production:** Use default values (5 retries, 5 second backoff) for balanced behavior

## Error Handling

If all retries are exhausted, you'll see:

```
Rate limit hit (429). Max retries (5) exhausted.
```

And the original `HttpError` will be raised, which you can catch in your code:

```python
from googleapiclient.errors import HttpError

try:
    sheets.populate_calendar(spreadsheet_id, schedule, tab_name, month, year)
except HttpError as err:
    if err.resp.status == 429:
        print("Rate limit exceeded even after retries")
    else:
        print(f"API error: {err}")
```
