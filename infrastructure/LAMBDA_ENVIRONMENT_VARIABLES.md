# Lambda Environment Variables

## Reserved Environment Variables

AWS Lambda automatically sets these environment variables. **You cannot override them** in your function configuration.

### Runtime Environment Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `AWS_REGION` | AWS region where the Lambda is running | `us-east-1` |
| `AWS_DEFAULT_REGION` | Same as AWS_REGION | `us-east-1` |
| `AWS_EXECUTION_ENV` | Runtime identifier | `AWS_Lambda_python3.12` |
| `AWS_LAMBDA_FUNCTION_NAME` | Name of the function | `calendar-service-production` |
| `AWS_LAMBDA_FUNCTION_MEMORY_SIZE` | Memory allocated | `512` |
| `AWS_LAMBDA_FUNCTION_VERSION` | Function version | `$LATEST` or `1` |
| `AWS_LAMBDA_LOG_GROUP_NAME` | CloudWatch log group | `/aws/lambda/calendar-service-production` |
| `AWS_LAMBDA_LOG_STREAM_NAME` | CloudWatch log stream | `2024/01/15/[$LATEST]abc123...` |
| `AWS_LAMBDA_RUNTIME_API` | Runtime API endpoint | `127.0.0.1:9001` |
| `LAMBDA_TASK_ROOT` | Function code directory | `/var/task` |
| `LAMBDA_RUNTIME_DIR` | Runtime directory | `/var/runtime` |
| `_HANDLER` | Handler location | `src.api.lambda_handler_simple.lambda_handler` |
| `TZ` | Timezone | `UTC` |

### Security/Auth Variables

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | Temporary access key from execution role |
| `AWS_SECRET_ACCESS_KEY` | Temporary secret key from execution role |
| `AWS_SESSION_TOKEN` | Temporary session token from execution role |

### X-Ray Tracing (if enabled)

| Variable | Description |
|----------|-------------|
| `_X_AMZN_TRACE_ID` | X-Ray tracing header |
| `AWS_XRAY_CONTEXT_MISSING` | X-Ray error handling mode |
| `AWS_XRAY_DAEMON_ADDRESS` | X-Ray daemon endpoint |

## Custom Environment Variables

You **can** set custom environment variables in your Lambda function configuration:

```yaml
# Good - Custom variables
Environment:
  Variables:
    SECRET_NAME: calendar-service-secrets-production
    ENVIRONMENT: production
    GOOGLE_CREDENTIALS_SECRET: arn:aws:secretsmanager:...
```

```yaml
# Bad - Trying to set reserved variables
Environment:
  Variables:
    AWS_REGION: us-east-1  # ❌ ERROR: Reserved variable
    SECRET_NAME: my-secret # ✅ OK: Custom variable
```

## Accessing Environment Variables in Code

### Reserved Variables (Automatically Available)

```python
import os

# These are always available in Lambda
region = os.environ['AWS_REGION']  # Automatically set
function_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']
log_group = os.environ['AWS_LAMBDA_LOG_GROUP_NAME']
```

### Custom Variables

```python
import os

# Set in CloudFormation/Lambda configuration
secret_name = os.environ.get('SECRET_NAME')
environment = os.environ.get('ENVIRONMENT', 'development')
```

## Using boto3 with Automatic Region

boto3 automatically uses `AWS_REGION` - no need to specify:

```python
import boto3

# Automatically uses AWS_REGION from environment
client = boto3.client('secretsmanager')

# You can verify which region is being used
print(f"Region: {client.meta.region_name}")
```

## Common Mistakes

### ❌ Don't Do This

```yaml
# CloudFormation - Will fail
Environment:
  Variables:
    AWS_REGION: !Ref AWS::Region  # Error: Reserved variable
```

```python
# Python - Redundant
client = boto3.client(
    'secretsmanager',
    region_name=os.environ['AWS_REGION']  # Not needed
)
```

### ✅ Do This Instead

```yaml
# CloudFormation - Let Lambda set it automatically
Environment:
  Variables:
    SECRET_NAME: !Select [6, !Split [':', !Ref SecretArn]]
    # AWS_REGION is automatically available, no need to set it
```

```python
# Python - Let boto3 use it automatically
client = boto3.client('secretsmanager')  # Uses AWS_REGION automatically
```

## Our Configuration

### CloudFormation (lambda.yaml)

```yaml
Environment:
  Variables:
    SECRET_NAME: !Select [6, !Split [':', !Ref SecretArn]]
    ENVIRONMENT: !Ref Environment
    GOOGLE_CREDENTIALS_SECRET: !If [HasGoogleCredentials, !Ref GoogleCredentialsSecretArn, '']
    # AWS_REGION is NOT set here - it's automatically available
```

### Python (aws_config.py)

```python
# boto3 automatically detects region from AWS_REGION environment variable
session = boto3.session.Session()
client = session.client(service_name='secretsmanager')

# Verify which region is being used
region = client.meta.region_name
print(f"Using AWS region: {region}")
```

## References

- [AWS Lambda Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
- [Reserved Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html#configuration-envvars-runtime)
