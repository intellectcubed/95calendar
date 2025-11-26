# Client Examples

This directory contains example client code for calling the Calendar Service API.

## Python Client with IAM Authentication

The `lambda_client.py` provides a Python client for calling the Lambda API with IAM authentication.

### Installation

```bash
pip install requests requests-aws4auth boto3
```

### Usage

```bash
# Set your API URL
export API_URL="https://your-api-id.execute-api.us-east-1.amazonaws.com/v1"

# Run examples
python lambda_client.py
```

### As a Library

```python
from lambda_client import CalendarServiceClient

# Initialize client
client = CalendarServiceClient(
    api_url="https://your-api-id.execute-api.us-east-1.amazonaws.com/v1",
    region="us-east-1"
)

# Get schedule for a day
schedule = client.get_schedule_day("20260110")
print(schedule)

# Mark squad as no crew (preview mode)
result = client.no_crew(
    date="20260110",
    shift_start="1900",
    shift_end="2100",
    squad=34,
    preview=True
)
print(result)

# Apply the change (not preview)
result = client.no_crew(
    date="20260110",
    shift_start="1900",
    shift_end="2100",
    squad=34,
    preview=False
)
print(result)

# List backups
backups = client.list_backups("20260110")
print(backups)

# Rollback to a previous state
if backups and 'backups' in backups:
    change_id = backups['backups'][0]['changeId']
    result = client.rollback("20260110", change_id)
    print(result)
```

## Authentication

The client uses AWS IAM authentication via `requests-aws4auth`. It automatically uses credentials from:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM role (if running on EC2, ECS, Lambda, etc.)

### Required IAM Permissions

Your IAM user/role needs the API invoke policy:

```bash
# Attach the invoke policy created by CloudFormation
aws iam attach-user-policy \
    --user-name your-username \
    --policy-arn arn:aws:iam::ACCOUNT_ID:policy/calendar-service-api-invoke-production
```

Or create a custom policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "execute-api:Invoke",
            "Resource": "arn:aws:execute-api:REGION:ACCOUNT_ID:API_ID/*"
        }
    ]
}
```

## Alternative: Using curl with AWS Signature

For testing, you can use `awscurl`:

```bash
# Install awscurl
pip install awscurl

# Make a request
awscurl --service execute-api \
    --region us-east-1 \
    "https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/?action=get_schedule_day&date=20260110"
```

## Alternative: Using Postman

Postman supports AWS Signature authentication:

1. Create a new request
2. Set Authorization type to "AWS Signature"
3. Enter your Access Key and Secret Key
4. Set AWS Region and Service Name (`execute-api`)
5. Make the request

## Alternative: Using JavaScript/Node.js

```javascript
const AWS = require('aws-sdk');
const axios = require('axios');
const aws4 = require('aws4');

const apiUrl = 'https://your-api-id.execute-api.us-east-1.amazonaws.com/v1';
const region = 'us-east-1';

// Sign request with AWS4
const request = {
    host: new URL(apiUrl).hostname,
    path: '/?action=get_schedule_day&date=20260110',
    method: 'GET',
    region: region,
    service: 'execute-api'
};

// Sign with credentials from AWS SDK
aws4.sign(request);

// Make request with axios
axios({
    method: request.method,
    url: `${apiUrl}${request.path}`,
    headers: request.headers
}).then(response => {
    console.log(response.data);
}).catch(error => {
    console.error(error);
});
```
