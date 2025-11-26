#!/bin/bash
# deploy.sh
# Deploys the Calendar Service to AWS

set -e

# Configuration
ENVIRONMENT="${ENVIRONMENT:-production}"
AWS_REGION="${AWS_REGION:-us-east-1}"
S3_BUCKET="${S3_BUCKET:-}"
STACK_NAME="calendar-service-${ENVIRONMENT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Environment (production|staging|development) [default: production]"
    echo "  -r, --region REGION      AWS region [default: us-east-1]"
    echo "  -b, --bucket BUCKET      S3 bucket for deployment artifacts (required)"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Environment variables required:"
    echo "  SPREADSHEET_ID          Google Spreadsheet ID"
    echo "  SUPABASE_URL           Supabase URL"
    echo "  SUPABASE_KEY           Supabase Key"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -b|--bucket)
            S3_BUCKET="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [ -z "$S3_BUCKET" ]; then
    echo -e "${RED}Error: S3 bucket is required${NC}"
    usage
fi

if [ -z "$SPREADSHEET_ID" ] || [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo -e "${RED}Error: Missing required environment variables${NC}"
    echo "Please set: SPREADSHEET_ID, SUPABASE_URL, SUPABASE_KEY"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${GREEN}🚀 Deploying Calendar Service${NC}"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "S3 Bucket: $S3_BUCKET"
echo ""

# Step 1: Build artifacts
echo -e "${YELLOW}📦 Step 1: Building artifacts...${NC}"
bash "$SCRIPT_DIR/build-layer.sh"
bash "$SCRIPT_DIR/build-function.sh"

# Step 2: Upload to S3
echo -e "${YELLOW}☁️  Step 2: Uploading to S3...${NC}"
aws s3 cp "$PROJECT_ROOT/build/output/layer.zip" "s3://$S3_BUCKET/calendar-service/layer.zip" --region "$AWS_REGION"
aws s3 cp "$PROJECT_ROOT/build/output/function.zip" "s3://$S3_BUCKET/calendar-service/function.zip" --region "$AWS_REGION"

# Upload CloudFormation templates
aws s3 cp "$PROJECT_ROOT/infrastructure/cloudformation/" "s3://$S3_BUCKET/cloudformation/" --recursive --region "$AWS_REGION"

# Step 3: Deploy CloudFormation stack
echo -e "${YELLOW}🏗️  Step 3: Deploying CloudFormation stack...${NC}"
aws cloudformation deploy \
    --template-file "$PROJECT_ROOT/infrastructure/cloudformation/master-stack.yaml" \
    --stack-name "$STACK_NAME" \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
        SpreadsheetId="$SPREADSHEET_ID" \
        SupabaseUrl="$SUPABASE_URL" \
        SupabaseKey="$SUPABASE_KEY" \
        LambdaCodeBucket="$S3_BUCKET" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$AWS_REGION"

# Get outputs
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Stack outputs:"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo -e "${GREEN}🎉 Calendar Service deployed successfully!${NC}"
