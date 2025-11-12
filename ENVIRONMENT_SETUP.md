# Environment Variables Setup

## Overview

The project now uses environment variables to manage configuration, specifically the Google Spreadsheet ID. This makes it easier to switch between different spreadsheets and keeps sensitive IDs out of the codebase.

## Quick Start

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your spreadsheet ID:**
   ```
   SPREADSHEET_ID=your-spreadsheet-id-here
   ```

3. **Install python-dotenv (if not already installed):**
   ```bash
   pip install -r requirements.txt
   ```

## Environment Variables

### SPREADSHEET_ID
- **Required:** Yes
- **Description:** The Google Spreadsheet ID for your calendar
- **Example:** `1123GTUB-rmttty-C7GwMXZCe9fvdb_hKd62S19Pvs`
- **Used by:** All scripts that interact with Google Sheets

## Files Updated

The following files now read `SPREADSHEET_ID` from environment variables:

1. **calendar_builder.py** - Main schedule builder
2. **calendar_commands.py** - Command execution for calendar modifications
3. **man_update_calendar.py** - Manual calendar update CLI
4. **test_calendar_commands_2.py** - Test suite
5. **territories.py** - Territory reading utility

## Command Line Override

You can still override the spreadsheet ID via command line in `calendar_builder.py`:

```bash
python calendar_builder.py --spreadsheet-id YOUR_ID --populate-google-calendar
```

If not provided via command line, it will fall back to the environment variable.

## Security

- `.env` is added to `.gitignore` to prevent committing sensitive data
- `.env.example` is provided as a template (safe to commit)
- Never commit your actual `.env` file to version control

## Troubleshooting

### Error: "SPREADSHEET_ID not found in environment variables"

**Solution:** Make sure you have:
1. Created a `.env` file in the project root
2. Added `SPREADSHEET_ID=your-id` to the file
3. The `.env` file is in the same directory where you run the scripts

### Environment variable not loading

**Solution:** 
- Make sure `python-dotenv` is installed: `pip install python-dotenv`
- Check that `.env` file has no syntax errors
- Verify the file is named exactly `.env` (not `.env.txt` or similar)
