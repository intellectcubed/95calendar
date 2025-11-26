# Lambda A → API Gateway B (Calendar Service) Integration Guide

## Architecture

```
JavaScript Client
    ↓
API Gateway A
    ↓
Lambda A (station95-api-proxy-dev)
    ↓ [IAM Signed Request]
API Gateway B (calendar-service-production)
    ↓
Lambda B (calendar-service-production)
```

## Setup Steps

### 1. Get the API Gateway B URL

```bash
# Get the API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name calendar-service-production \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

echo "Calendar Service API URL: $API_URL"
```

Or get from nested stack:
```bash
# Find the API Gateway stack
aws cloudformation list-stack-resources \
  --stack-name calendar-service-production \
  --query 'StackResourceSummaries[?contains(LogicalResourceId, `ApiGateway`)].PhysicalResourceId' \
  --output text

# Get URL from that stack
NESTED_STACK_NAME="<result-from-above>"
aws cloudformation describe-stacks \
  --stack-name $NESTED_STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text
```

### 2. Get the Invoke Policy ARN

```bash
# Get the invoke policy ARN
POLICY_ARN=$(aws cloudformation describe-stacks \
  --stack-name <ApiGateway-stack-name> \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiInvokePolicyArn`].OutputValue' \
  --output text)

echo "Policy ARN: $POLICY_ARN"
```

### 3. Attach Policy to Lambda A's Role

**Option A: Attach the managed policy (easiest)**

```bash
# Get Lambda A's role name
LAMBDA_A_ROLE=$(aws lambda get-function-configuration \
  --function-name station95-api-proxy-dev \
  --query 'Role' \
  --output text | awk -F'/' '{print $NF}')

echo "Lambda A Role: $LAMBDA_A_ROLE"

# Attach the invoke policy
aws iam attach-role-policy \
  --role-name $LAMBDA_A_ROLE \
  --policy-arn $POLICY_ARN

echo "✅ Policy attached!"
```

**Option B: Add inline policy (alternative)**

```bash
# Get API Gateway ID
API_ID=$(aws apigateway get-rest-apis \
  --query 'items[?name==`calendar-service-api-production`].id' \
  --output text)

# Add inline policy to Lambda A
aws iam put-role-policy \
  --role-name $LAMBDA_A_ROLE \
  --policy-name InvokeCalendarServiceApi \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": \"execute-api:Invoke\",
        \"Resource\": \"arn:aws:execute-api:*:*:${API_ID}/*/*/*\"
      }
    ]
  }"
```

### 4. Update Lambda A Code

**Add dependency to Lambda A's requirements.txt:**
```
requests-aws4auth==1.2.3
requests==2.32.3
```

**Lambda A Handler Code:**

```python
import json
import os
import boto3
import requests
from requests_aws4auth import AWS4Auth

# Get API URL from environment variable
CALENDAR_API_URL = os.environ.get('CALENDAR_API_URL')

def lambda_handler(event, context):
    """
    Lambda A handler - calls Calendar Service API with IAM auth.
    """

    # Get AWS credentials from Lambda's execution role
    session = boto3.Session()
    credentials = session.get_credentials()
    region = session.region_name or 'us-east-1'

    # Create AWS4Auth for signing requests
    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        'execute-api',
        session_token=credentials.token
    )

    # Example 1: Get schedule for a day
    try:
        response = requests.get(
            f"{CALENDAR_API_URL}/?action=get_schedule_day&date=20260110",
            auth=auth,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except requests.exceptions.RequestException as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to call Calendar Service'
            })
        }


# Helper functions for different calendar operations

def get_schedule_day(date: str, auth: AWS4Auth, api_url: str) -> dict:
    """Get schedule for a specific day."""
    response = requests.get(
        f"{api_url}/?action=get_schedule_day&date={date}",
        auth=auth
    )
    response.raise_for_status()
    return response.json()


def no_crew_command(date: str, shift_start: str, shift_end: str,
                    squad: int, preview: bool, auth: AWS4Auth, api_url: str) -> dict:
    """Mark squad as no crew for specified time."""
    response = requests.get(
        f"{api_url}/?action=noCrew&date={date}&shift_start={shift_start}"
        f"&shift_end={shift_end}&squad={squad}&preview={'true' if preview else 'false'}",
        auth=auth
    )
    response.raise_for_status()
    return response.json()


def apply_schedule(date: str, day_schedule_json: str, commands: str,
                   auth: AWS4Auth, api_url: str) -> dict:
    """Apply an external schedule."""
    response = requests.post(
        f"{api_url}/calendar/day/{date}/apply",
        json={
            'DaySchedule': day_schedule_json,
            'commands': commands
        },
        auth=auth
    )
    response.raise_for_status()
    return response.json()


def list_backups(date: str, auth: AWS4Auth, api_url: str) -> dict:
    """List backups for a specific date."""
    response = requests.get(
        f"{api_url}/?action=list_backups&date={date}",
        auth=auth
    )
    response.raise_for_status()
    return response.json()


def rollback(date: str, change_id: str, auth: AWS4Auth, api_url: str) -> dict:
    """Rollback to a previous snapshot."""
    response = requests.get(
        f"{api_url}/?action=rollback&date={date}&change_id={change_id}",
        auth=auth
    )
    response.raise_for_status()
    return response.json()
```

### 5. Set Environment Variable in Lambda A

```bash
# Set the Calendar API URL in Lambda A
aws lambda update-function-configuration \
  --function-name station95-api-proxy-dev \
  --environment Variables="{CALENDAR_API_URL=$API_URL}"
```

Or add to your CloudFormation/Serverless config for Lambda A.

### 6. Test the Integration

Create a test event in Lambda A console:
```json
{
  "action": "test_calendar_service",
  "date": "20260110"
}
```

You should see Lambda A successfully call API Gateway B and get a response.

## Error Handling

### Common Errors

**403 Forbidden - AccessDeniedException:**
- Lambda A's role doesn't have execute-api:Invoke permission
- Check the policy is attached correctly
- Verify the API Gateway resource ARN matches

**401 Unauthorized:**
- Request not properly signed
- Check AWS4Auth is using correct credentials
- Verify session_token is included for Lambda credentials

**Connection timeout:**
- Check API Gateway URL is correct
- Ensure Lambda A has internet access (if in VPC, needs NAT Gateway)
- Verify API Gateway B is deployed

### Debugging

```python
# Add debug logging
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Log request details
logger.info(f"Calling: {api_url}")
logger.info(f"Region: {region}")
logger.info(f"Auth headers: {dict(auth.get_auth_headers())}")
```

## Security Best Practices

1. ✅ **Use IAM roles** - No hardcoded credentials
2. ✅ **Least privilege** - Only grant execute-api:Invoke for specific API
3. ✅ **Use HTTPS** - API Gateway enforces this
4. ✅ **Set timeouts** - Prevent hanging requests
5. ✅ **Error handling** - Don't expose sensitive info in errors
6. ✅ **CloudTrail** - All API calls are logged

## Cost Optimization

- Lambda A invokes are billed normally
- API Gateway B invokes are billed normally
- No additional cost for IAM authentication
- Consider caching in Lambda A if calling frequently

## Monitoring

### CloudWatch Logs

**Lambda A logs:**
```bash
aws logs tail /aws/lambda/station95-api-proxy-dev --follow
```

**Lambda B logs:**
```bash
aws logs tail /aws/lambda/calendar-service-production --follow
```

### CloudWatch Metrics

- Lambda A: Invocations, Duration, Errors
- API Gateway B: Count, Latency, 4XXError, 5XXError
- Lambda B: Invocations, Duration, Errors

### CloudTrail

All API Gateway invocations are logged with caller identity:
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::ApiGateway::RestApi \
  --max-results 10
```

## Complete Example

```python
import json
import os
import boto3
import requests
from requests_aws4auth import AWS4Auth

CALENDAR_API_URL = os.environ.get('CALENDAR_API_URL')

def lambda_handler(event, context):
    # Setup AWS auth
    session = boto3.Session()
    credentials = session.get_credentials()
    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        session.region_name or 'us-east-1',
        'execute-api',
        session_token=credentials.token
    )

    # Parse incoming request
    action = event.get('action')
    date = event.get('date', '20260110')

    try:
        if action == 'get_schedule':
            result = requests.get(
                f"{CALENDAR_API_URL}/?action=get_schedule_day&date={date}",
                auth=auth,
                timeout=30
            ).json()

        elif action == 'no_crew':
            result = requests.get(
                f"{CALENDAR_API_URL}/?action=noCrew"
                f"&date={date}"
                f"&shift_start={event['shift_start']}"
                f"&shift_end={event['shift_end']}"
                f"&squad={event['squad']}"
                f"&preview=true",
                auth=auth,
                timeout=30
            ).json()

        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Unknown action'})
            }

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```
