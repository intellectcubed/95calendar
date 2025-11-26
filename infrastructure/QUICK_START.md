# Quick Start Guide

## Local Development

```bash
# 1. Setup
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env with your credentials

# 2. Start service
uvicorn src.api.calendar_service:app --host 0.0.0.0 --port 8000 --reload

# 3. Test
curl "http://localhost:8000/?action=get_schedule_day&date=20260110"
```

## AWS Lambda Deployment

```bash
# 1. Prerequisites
export SPREADSHEET_ID="your-spreadsheet-id"
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-supabase-key"
export S3_BUCKET="your-deployment-bucket"

# Create S3 bucket (one-time)
aws s3 mb s3://$S3_BUCKET --region us-east-1

# 2. Deploy
cd infrastructure/scripts
./deploy.sh --bucket $S3_BUCKET --environment production --region us-east-1

# 3. Get API URL
aws cloudformation describe-stacks \
    --stack-name calendar-service-production \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text
```

## Testing Lambda API

```bash
# Install testing tool
npm install -g aws-api-gateway-cli-test

# Test endpoint
apig-test \
    --username=$AWS_ACCESS_KEY_ID \
    --password=$AWS_SECRET_ACCESS_KEY \
    --invoke-url=https://your-api-id.execute-api.us-east-1.amazonaws.com/v1 \
    --api-gateway-region=us-east-1 \
    --path-template='/?action=get_schedule_day&date=20260110' \
    --method=GET
```

## Common Commands

### Build Lambda Artifacts
```bash
# Build layer
./infrastructure/scripts/build-layer.sh

# Build function
./infrastructure/scripts/build-function.sh
```

### Update Existing Deployment
```bash
# Update function code only
./infrastructure/scripts/build-function.sh
aws lambda update-function-code \
    --function-name calendar-service-production \
    --s3-bucket $S3_BUCKET \
    --s3-key calendar-service/function.zip
```

### View Logs
```bash
# Lambda logs
aws logs tail /aws/lambda/calendar-service-production --follow

# API Gateway logs
aws logs tail /aws/apigateway/calendar-service-production --follow
```

### Cleanup
```bash
# Delete all AWS resources
aws cloudformation delete-stack --stack-name calendar-service-production

# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name calendar-service-production
```

## Endpoints

### Local
- Base URL: `http://localhost:8000`
- No authentication required

### Lambda
- Base URL: `https://{api-id}.execute-api.{region}.amazonaws.com/v1`
- **IAM authentication required**

### Available Endpoints (Both)
- `GET /?action=get_schedule_day&date=YYYYMMDD`
- `GET /?action=noCrew&date=YYYYMMDD&shift_start=HHMM&shift_end=HHMM&squad=XX`
- `POST /calendar/day/{date}/apply` - Apply external schedule
- `POST /calendar/day/{date}/preview` - Preview command

## Troubleshooting

### Local: Module not found
```bash
# Reinstall dependencies
pip install -r requirements-dev.txt --force-reinstall
```

### Local: Port in use
```bash
# Kill process on port 8000
kill -9 $(lsof -ti:8000)
```

### Lambda: Deployment fails
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events \
    --stack-name calendar-service-production \
    --max-items 10
```

### Lambda: 403 Forbidden
```bash
# Attach invoke policy to your IAM user
POLICY_ARN=$(aws cloudformation describe-stacks \
    --stack-name calendar-service-api-production \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiInvokePolicyArn`].OutputValue' \
    --output text)

aws iam attach-user-policy \
    --user-name your-username \
    --policy-arn $POLICY_ARN
```

## File Structure

```
95calendar/
├── src/
│   ├── api/
│   │   ├── calendar_service.py    # Main FastAPI app
│   │   └── lambda_handler.py      # Lambda entry point
│   ├── config/
│   │   └── aws_config.py          # Config manager
│   ├── services/
│   ├── models/
│   └── ...
├── infrastructure/
│   ├── cloudformation/            # AWS CloudFormation templates
│   ├── scripts/                   # Build and deployment scripts
│   ├── AWS_DEPLOYMENT.md         # Detailed deployment guide
│   ├── LOCAL_DEVELOPMENT.md      # Local dev guide
│   └── QUICK_START.md            # This file
├── requirements-lambda.txt        # Lambda dependencies
├── requirements-dev.txt           # Dev dependencies
├── .env                          # Local config (not committed)
└── credentials.json              # Google credentials (not committed)
```

## Next Steps

- **Development**: See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
- **AWS Deployment**: See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)
- **Architecture**: See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
