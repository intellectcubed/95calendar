# Quick deployment after code change
```shell

# On mac mini
cd /Users/gman/Projects/Python/95calendar

docker-compose up -d --build calendar-service
```

---
# Fresh Deployment Steps

  1. Prerequisites Check

  cd /Users/george.nowakowski/Projects/python/ems/95calendar

  # Verify you have all required files
  ls -la config/credentials.json    # Google service account credentials
  cat .env                           # Should have SPREADSHEET_ID, SUPABASE_URL, SUPABASE_KEY

  # Set deployment variables
  export BUCKET="your-s3-bucket-name"
  export ENVIRONMENT="production"
  export AWS_REGION="us-east-1"

  2. Create S3 Bucket (if needed)

  # Create bucket for deployment artifacts
  aws s3 mb s3://$BUCKET --region $AWS_REGION 2>/dev/null || echo "Bucket already exists"

  3. Build Lambda Layer (with Docker for Linux)

  # Build the layer with correct architecture
  docker run --rm \
    --platform linux/amd64 \
    --entrypoint /bin/bash \
    -v "$PWD":/workspace \
    -w /workspace \
    public.ecr.aws/lambda/python:3.12 \
    -c "
      rm -rf build/lambda-layer
      mkdir -p build/lambda-layer/python
      pip install -r requirements-lambda.txt -t build/lambda-layer/python --no-cache-dir
      cd build/lambda-layer/python
      find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
      find . -type f -name '*.pyc' -delete
    "

  # Create the layer zip
  cd build/lambda-layer
  zip -r9 ../output/layer.zip python
  cd ../..

  # Verify Linux binaries
  echo "Checking for Linux binaries:"
  unzip -l build/output/layer.zip | grep "pydantic_core.*\.so$"
  # Should show: .cpython-312-x86_64-linux-gnu.so (not darwin!)

  4. Build Lambda Function

  # Build function
  ./infrastructure/scripts/build-function.sh

  # Verify credentials are included
  unzip -l build/output/function.zip | grep credentials.json
  unzip -l build/output/function.zip | grep schedule_formatter

  5. Upload Artifacts to S3

  # Upload layer and function
  aws s3 cp build/output/layer.zip s3://$BUCKET/calendar-service/layer.zip
  aws s3 cp build/output/function.zip s3://$BUCKET/calendar-service/function.zip

  # Upload CloudFormation templates
  aws s3 cp infrastructure/cloudformation/ s3://$BUCKET/cloudformation/ --recursive

  echo "✅ Artifacts uploaded to S3"

  6. Create/Update Secrets in Secrets Manager

  # Check if secret exists
  aws secretsmanager describe-secret --secret-id calendar-service-secrets-production 2>/dev/null

  # If it doesn't exist, create it:
  aws secretsmanager create-secret \
    --name calendar-service-secrets-production \
    --secret-string "{
      \"SPREADSHEET_ID\": \"$(grep SPREADSHEET_ID .env | cut -d'=' -f2)\",
      \"SUPABASE_URL\": \"$(grep SUPABASE_URL .env | cut -d'=' -f2)\",
      \"SUPABASE_KEY\": \"$(grep SUPABASE_KEY .env | cut -d'=' -f2)\"
    }"

  # Or update if it exists:
  aws secretsmanager update-secret \
    --secret-id calendar-service-secrets-production \
    --secret-string "{
      \"SPREADSHEET_ID\": \"$(grep SPREADSHEET_ID .env | cut -d'=' -f2)\",
      \"SUPABASE_URL\": \"$(grep SUPABASE_URL .env | cut -d'=' -f2)\",
      \"SUPABASE_KEY\": \"$(grep SUPABASE_KEY .env | cut -d'=' -f2)\"
    }"

  7. Deploy CloudFormation Stack

  Option A: Deploy with master stack (recommended)

  aws cloudformation deploy \
    --template-file infrastructure/cloudformation/master-stack.yaml \
    --stack-name calendar-service-production \
    --parameter-overrides \
      Environment=production \
      SpreadsheetId="$(grep SPREADSHEET_ID .env | cut -d'=' -f2)" \
      SupabaseUrl="$(grep SUPABASE_URL .env | cut -d'=' -f2)" \
      SupabaseKey="$(grep SUPABASE_KEY .env | cut -d'=' -f2)" \
      LambdaCodeBucket=$BUCKET \
    --capabilities CAPABILITY_NAMED_IAM \
    --region us-east-1

  echo "✅ Stack deployment started"

  8. Wait for Deployment to Complete

  aws cloudformation wait stack-create-complete \
    --stack-name calendar-service-production \
    --region $AWS_REGION

  echo "✅ Deployment complete!"

  9. Get the API Gateway URL

  # Get outputs
  aws cloudformation describe-stacks \
    --stack-name calendar-service-production \
    --query 'Stacks[0].Outputs' \
    --output table

  # Get just the API URL
  API_URL=$(aws cloudformation describe-stacks \
    --stack-name calendar-service-production \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text)

  echo "🌐 API Gateway URL: $API_URL"

  10. Test the Deployment

  # Test directly in Lambda console with this event:
cat > test-event.json <<- 'EOF'
  {
    "httpMethod": "GET",
    "path": "/",
    "queryStringParameters": {
      "action": "get_schedule_day",
      "date": "20260110"
    },
    "headers": {
      "Content-Type": "application/json"
    },
    "body": null,
    "isBase64Encoded": false
  }
EOF

  # Invoke Lambda directly
  aws lambda invoke \
    --function-name calendar-service-production \
    --payload fileb://test-event.json \
    response.json

  cat response.json