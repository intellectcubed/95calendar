#!/bin/bash
# setup-api-gateway-logging.sh
# One-time setup for API Gateway CloudWatch logging (per AWS account/region)

set -e

AWS_REGION="${AWS_REGION:-us-east-1}"
ROLE_NAME="APIGatewayCloudWatchLogsRole"

echo "🔧 Setting up API Gateway CloudWatch Logs role for region: $AWS_REGION"

# Check if role already exists
if aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null; then
    echo "✅ IAM role $ROLE_NAME already exists"
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
else
    echo "📝 Creating IAM role $ROLE_NAME..."

    # Create trust policy
    cat > /tmp/api-gateway-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "apigateway.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create the role
    ROLE_ARN=$(aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/api-gateway-trust-policy.json \
        --description "Allows API Gateway to write logs to CloudWatch" \
        --query 'Role.Arn' \
        --output text)

    echo "✅ Created role: $ROLE_ARN"

    # Attach the managed policy
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"

    echo "✅ Attached CloudWatch Logs policy"

    # Wait for role to be ready
    echo "⏳ Waiting for role to propagate..."
    sleep 10

    # Clean up
    rm /tmp/api-gateway-trust-policy.json
fi

# Update API Gateway account settings
echo "🔧 Configuring API Gateway account settings..."
aws apigateway update-account \
    --region "$AWS_REGION" \
    --patch-operations op=replace,path=/cloudwatchRoleArn,value="$ROLE_ARN"

echo ""
echo "✅ API Gateway CloudWatch logging is now enabled for region: $AWS_REGION"
echo ""
echo "To enable logging in your API:"
echo "1. Update infrastructure/cloudformation/api-gateway.yaml"
echo "2. In ApiStage MethodSettings, add:"
echo "   LoggingLevel: INFO"
echo "   DataTraceEnabled: true"
echo "3. Redeploy the stack"
echo ""
echo "Note: This setup is per AWS account/region and only needs to be done once."
