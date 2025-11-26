import os
import sys
import json
import boto3
import requests
from requests_aws4auth import AWS4Auth

# Configuration
STACK_NAME = os.environ.get('STACK_NAME', 'calendar-service-production')
REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Get credentials from AWS CLI configuration
session = boto3.Session()
credentials = session.get_credentials()

# Create AWS4Auth using your configured credentials
auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    'execute-api',
    session_token=credentials.token
)

# Get API URL from CloudFormation output
cf_client = boto3.client('cloudformation', region_name=REGION)
response = cf_client.describe_stacks(StackName=STACK_NAME)
outputs = response['Stacks'][0]['Outputs']
api_url = next(o['OutputValue'] for o in outputs if o['OutputKey'] == 'ApiUrl')

print(f"Testing API: {api_url}\n")


# ============================================================================
# Test Functions
# ============================================================================

def test_get_schedule_day(date='20251126'):
    """Test GET /?action=get_schedule_day&date=YYYYMMDD"""
    print(f"[TEST] GET Schedule for {date}")
    print("-" * 60)

    response = requests.get(
        f'{api_url}/?action=get_schedule_day&date={date}',
        auth=auth
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    return response


def test_preview_add_shift(date='20260315'):
    """Test POST /calendar/day/{date}/preview with addShift payload"""
    print(f"[TEST] POST Preview Add Shift for {date}")
    print("-" * 60)

    payload = {
        "action": "addShift",
        "date": date,
        "shift_start": "0700",
        "shift_end": "0900",
        "squad": 42,
        "day_schedule": json.dumps({
            "day": "Sunday 2026-03-15",
            "shifts": [
                {
                    "name": "Day Shift",
                    "start_time": "06:00",
                    "end_time": "18:00",
                    "segments": [
                        {
                            "start_time": "06:00",
                            "end_time": "18:00",
                            "squads": [
                                {
                                    "id": 54,
                                    "territories": [34, 35, 42, 43, 54],
                                    "active": True
                                }
                            ]
                        }
                    ],
                    "tango": 54
                },
                {
                    "name": "Night Shift",
                    "start_time": "18:00",
                    "end_time": "06:00",
                    "segments": [
                        {
                            "start_time": "18:00",
                            "end_time": "06:00",
                            "squads": [
                                {
                                    "id": 42,
                                    "territories": [35, 42, 54],
                                    "active": True
                                },
                                {
                                    "id": 43,
                                    "territories": [34, 43],
                                    "active": True
                                }
                            ]
                        }
                    ],
                    "tango": 43
                }
            ]
        })
    }

    response = requests.post(
        f'{api_url}/calendar/day/{date}/preview',
        json=payload,
        auth=auth,
        headers={'Content-Type': 'application/json'}
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    return response


def test_list_backups(date='20251126'):
    """Test GET /?action=list_backups&date=YYYYMMDD"""
    print(f"[TEST] GET List Backups for {date}")
    print("-" * 60)

    response = requests.get(
        f'{api_url}/?action=list_backups&date={date}',
        auth=auth
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    return response


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    # Available tests
    tests = {
        'get_schedule': test_get_schedule_day,
        'preview_add_shift': test_preview_add_shift,
        'list_backups': test_list_backups,
    }

    # Determine which test to run
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == 'all':
            # Run all tests
            for name, test_func in tests.items():
                test_func()
        elif test_name in tests:
            # Run specific test
            tests[test_name]()
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(tests.keys())}, all")
            sys.exit(1)
    else:
        # Default: run get_schedule test
        test_get_schedule_day()