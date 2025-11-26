#!/bin/bash
  set -e

  # Configuration
  export BUCKET="station95-deployment-894033577592"
  export ENVIRONMENT="production"
  export AWS_REGION="us-east-1"

  cd /Users/george.nowakowski/Projects/python/ems/95calendar

  echo "🏗️  Building Lambda Layer..."
  docker run --rm --platform linux/amd64 --entrypoint /bin/bash \
    -v "$PWD":/workspace -w /workspace \
    public.ecr.aws/lambda/python:3.12 -c "
      mkdir -p build/lambda-layer/python build/output
      pip install -r requirements-lambda.txt -t build/lambda-layer/python --no-cache-dir
      cd build/lambda-layer && zip -r9 ../output/layer.zip python
    "

  echo "📦 Building Function..."
  ./infrastructure/scripts/build-function.sh

  echo "☁️  Uploading to S3..."
  aws s3 cp build/output/layer.zip s3://$BUCKET/calendar-service/layer.zip
  aws s3 cp build/output/function.zip s3://$BUCKET/calendar-service/function.zip
  aws s3 cp infrastructure/cloudformation/ s3://$BUCKET/cloudformation/ --recursive

  echo "🚀 Deploying CloudFormation..."
  aws cloudformation deploy \
    --template-file infrastructure/cloudformation/master-stack.yaml \
    --stack-name calendar-service-production \
    --parameter-overrides \
      Environment=production \
      SpreadsheetId="$(grep SPREADSHEET_ID .env | cut -d'=' -f2)" \
      SupabaseUrl="$(grep SUPABASE_URL .env | cut -d'=' -f2)" \
      SupabaseKey="$(grep SUPABASE_KEY .env | cut -d'=' -f2)" \
      LambdaCodeBucket=$BUCKET \
    --capabilities CAPABILITY_NAMED_IAM

  echo "✅ Deployment complete!"
  aws cloudformation describe-stacks \
    --stack-name calendar-service-production \
    --query 'Stacks[0].Outputs' \
    --output table

