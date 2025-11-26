# AWS Lambda Deployment Guide

This guide explains how to deploy the Calendar Service to AWS Lambda with API Gateway.

## Architecture Overview

The Calendar Service is deployed as:
- **AWS Lambda**: Simple event handler (no web framework - API Gateway handles HTTP)
- **API Gateway**: REST API with IAM authentication, routing, and request parsing
- **Secrets Manager**: Stores sensitive configuration (SPREADSHEET_ID, Supabase credentials) - created separately
- **Lambda Layer**: Contains Python dependencies (minimal - no FastAPI/Mangum overhead)
- **CloudWatch**: Logs and monitoring

**Important**: Secrets Manager secrets are created manually and exist independently of the CloudFormation stack. The Lambda function references secrets by name at runtime.

**Note**: The Lambda function uses a simplified handler (`lambda_handler_simple.py`) that directly
processes API Gateway events. This is more efficient than using FastAPI+Mangum because API Gateway
already handles HTTP routing, parsing, and response formatting. See [WHY_NO_FASTAPI_IN_LAMBDA.md](WHY_NO_FASTAPI_IN_LAMBDA.md)
for detailed explanation.

## Prerequisites

1. **AWS CLI** installed and configured with credentials
2. **AWS Account** with permissions to create:
   - Lambda functions
   - API Gateway APIs
   - Secrets Manager secrets
   - IAM roles and policies
   - S3 buckets
   - CloudWatch log groups

3. **S3 Bucket** for deployment artifacts
   ```bash
   aws s3 mb s3://your-deployment-bucket --region us-east-1
   ```

4. **Environment Variables**:
   - `SPREADSHEET_ID`: Google Spreadsheet ID
   - `SUPABASE_URL`: Supabase URL for backup system
   - `SUPABASE_KEY`: Supabase anonymous key

## Deployment Steps

### 1. Create Secrets Manager Secret

**Important**: The secret must be created before deploying the stack. The Lambda function expects a secret named `calendar-service-secrets-{environment}` (e.g., `calendar-service-secrets-production`).

```bash
# Set your values
export SPREADSHEET_ID="your-spreadsheet-id"
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-supabase-key"
export ENVIRONMENT="production"

# Create the secret
aws secretsmanager create-secret \
    --name "calendar-service-secrets-${ENVIRONMENT}" \
    --description "Calendar Service configuration for ${ENVIRONMENT}" \
    --secret-string "{
        \"SPREADSHEET_ID\": \"${SPREADSHEET_ID}\",
        \"SUPABASE_URL\": \"${SUPABASE_URL}\",
        \"SUPABASE_KEY\": \"${SUPABASE_KEY}\"
    }"
```

To update existing secrets:
```bash
aws secretsmanager update-secret \
    --secret-id "calendar-service-secrets-${ENVIRONMENT}" \
    --secret-string "{
        \"SPREADSHEET_ID\": \"${SPREADSHEET_ID}\",
        \"SUPABASE_URL\": \"${SUPABASE_URL}\",
        \"SUPABASE_KEY\": \"${SUPABASE_KEY}\"
    }"
```

### 2. Set Deployment Variables

```bash
export S3_BUCKET="your-deployment-bucket"
export AWS_REGION="us-east-1"
export ENVIRONMENT="production"
```

### 3. Run Deployment Script

```bash
cd infrastructure/scripts
./deploy.sh --bucket your-deployment-bucket --environment production --region us-east-1
```

The deployment script will:
1. Build the Lambda Layer with dependencies
2. Build the Lambda function package
3. Upload artifacts to S3
4. Deploy CloudFormation stacks (Lambda + API Gateway)
5. Output the API Gateway URL

**Note**: The script does NOT create secrets - you must create them manually first (see Step 1 above).

### 3. Verify Deployment

```bash
# Get the API URL
aws cloudformation describe-stacks \
    --stack-name calendar-service-production \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text
```

## Manual Deployment (Step-by-Step)

If you prefer manual deployment or need to troubleshoot:

### Step 1: Build Lambda Layer

```bash
cd infrastructure/scripts
./build-layer.sh
```

This creates `build/output/layer.zip` containing all Python dependencies.

### Step 2: Build Lambda Function

```bash
./build-function.sh
```

This creates `build/output/function.zip` containing your source code.

### Step 3: Upload to S3

```bash
aws s3 cp build/output/layer.zip s3://$S3_BUCKET/calendar-service/layer.zip
aws s3 cp build/output/function.zip s3://$S3_BUCKET/calendar-service/function.zip
aws s3 cp infrastructure/cloudformation/ s3://$S3_BUCKET/cloudformation/ --recursive
```

### Step 4: Deploy Master Stack

Deploy all infrastructure (Lambda + API Gateway) in one command:

```bash
aws cloudformation deploy \
    --template-file infrastructure/cloudformation/master-stack.yaml \
    --stack-name calendar-service-production \
    --parameter-overrides \
        Environment=production \
        LambdaCodeBucket=$S3_BUCKET \
    --capabilities CAPABILITY_NAMED_IAM
```

Or deploy individually:

### Step 4a: Deploy Lambda Stack

```bash
aws cloudformation deploy \
    --template-file infrastructure/cloudformation/lambda.yaml \
    --stack-name calendar-service-lambda-production \
    --parameter-overrides \
        Environment=production \
        LambdaCodeBucket=$S3_BUCKET \
    --capabilities CAPABILITY_NAMED_IAM
```

### Step 4b: Deploy API Gateway Stack

```bash
# Get the Lambda ARN from previous stack
FUNCTION_ARN=$(aws cloudformation describe-stacks \
    --stack-name calendar-service-lambda-production \
    --query 'Stacks[0].Outputs[?OutputKey==`FunctionArn`].OutputValue' \
    --output text)

aws cloudformation deploy \
    --template-file infrastructure/cloudformation/api-gateway.yaml \
    --stack-name calendar-service-api-production \
    --parameter-overrides \
        Environment=production \
        LambdaFunctionArn=$FUNCTION_ARN
```

## Testing the Deployment

### Get API URL

```bash
API_URL=$(aws cloudformation describe-stacks \
    --stack-name calendar-service-api-production \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text)

echo "API URL: $API_URL"
```

### Test with IAM Authentication

Since the API uses IAM authentication, you need to sign requests with AWS credentials:

```bash
# Using aws-api-gateway-cli-test (npm install -g aws-api-gateway-cli-test)
apig-test \
    --username=$AWS_ACCESS_KEY_ID \
    --password=$AWS_SECRET_ACCESS_KEY \
    --invoke-url=$API_URL \
    --api-gateway-region=$AWS_REGION \
    --path-template='/?action=get_schedule_day&date=20260110' \
    --method=GET
```

Or using Python with `requests-aws4auth`:

```python
import requests
from requests_aws4auth import AWS4Auth

auth = AWS4Auth(
    'YOUR_ACCESS_KEY',
    'YOUR_SECRET_KEY',
    'us-east-1',
    'execute-api'
)

api_url = 'https://your-api-id.execute-api.us-east-1.amazonaws.com/v1'
response = requests.get(
    f'{api_url}/?action=get_schedule_day&date=20260110',
    auth=auth
)
print(response.json())
```

## Updating the Deployment

To update your Lambda function after making code changes:

```bash
# Rebuild and deploy
./infrastructure/scripts/deploy.sh --bucket $S3_BUCKET
```

Or update just the function:

```bash
./infrastructure/scripts/build-function.sh
aws lambda update-function-code \
    --function-name calendar-service-production \
    --s3-bucket $S3_BUCKET \
    --s3-key calendar-service/function.zip
```

## Managing Google Credentials

The Google service account credentials (`credentials.json`) are included in the Lambda deployment package. For enhanced security, you can optionally store them in Secrets Manager:

### Option 1: Include in Deployment (Current)

The `credentials.json` file is packaged with the function code. This is simpler but less secure.

### Option 2: Store in Secrets Manager (Recommended for Production)

1. Create a secret for Google credentials:
   ```bash
   aws secretsmanager create-secret \
       --name calendar-service-google-credentials-production \
       --secret-string file://credentials.json
   ```

2. Update Lambda code to read from Secrets Manager:
   ```python
   # In google_sheets_master.py or wherever credentials are loaded
   from src.config.aws_config import config
   import json

   if config.is_lambda:
       creds_json = config.get('GOOGLE_CREDENTIALS_JSON')
       credentials = json.loads(creds_json)
   else:
       with open('credentials.json') as f:
           credentials = json.load(f)
   ```

## Monitoring

### CloudWatch Logs

```bash
# Lambda logs
aws logs tail /aws/lambda/calendar-service-production --follow

# API Gateway logs
aws logs tail /aws/apigateway/calendar-service-production --follow
```

### Metrics

View metrics in CloudWatch Console:
- Lambda invocations, errors, duration
- API Gateway requests, 4xx/5xx errors, latency

## Troubleshooting

### Lambda Timeout

If requests timeout, increase Lambda timeout in `infrastructure/cloudformation/lambda.yaml`:
```yaml
Timeout: 120  # Increase from 60 to 120 seconds
```

### Permission Errors

Ensure the Lambda execution role has permissions for:
- Secrets Manager: `secretsmanager:GetSecretValue`
- CloudWatch Logs: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### API Gateway 403 Forbidden

Ensure your IAM user/role has the invoke policy:
```bash
# Attach the invoke policy to your IAM user
aws iam attach-user-policy \
    --user-name your-username \
    --policy-arn arn:aws:iam::ACCOUNT_ID:policy/calendar-service-api-invoke-production
```

## Cost Optimization

- **Lambda**: Free tier includes 1M requests/month
- **API Gateway**: Free tier includes 1M requests/month for first 12 months
- **Secrets Manager**: $0.40/secret/month + $0.05 per 10,000 API calls
- **CloudWatch Logs**: First 5GB ingestion free

Estimated monthly cost for low-medium usage: **$1-5/month**

## Cleanup

To delete all resources:

```bash
# Delete master stack (deletes all nested stacks)
aws cloudformation delete-stack --stack-name calendar-service-production

# Delete S3 artifacts
aws s3 rm s3://$S3_BUCKET/calendar-service/ --recursive
aws s3 rm s3://$S3_BUCKET/cloudformation/ --recursive
```
