import os
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

print(f"Testing API: {api_url}")

# Test the API
response = requests.get(
    f'{api_url}/?action=get_schedule_day&date=20260110',
    auth=auth
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")