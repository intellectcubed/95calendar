# Project Objective
Convert the calendar_commands service to AWS Lambda while maintaining the ability to run it as a local service.

## Technical Requirements

### 1. Lambda Conversion
- Adapt calendar_service to run as an AWS Lambda function
- Support the following endpoints:
  - `GET /`
  - `POST /calendar/day/{calendar_date}/apply`
  - `POST /calendar/day/{calendar_date}/preview`

### 2. API Gateway Integration
- Configure API Gateway to route requests to the Lambda function
- Implement authentication for API Gateway endpoints

### 3. Infrastructure as Code
- Create CloudFormation templates for all AWS resources (Lambda, API Gateway, Secrets Manager, etc.)

### 4. Configuration Management
- Migrate credentials from `.env` to AWS Secrets Manager
- Note: Manual creation of secrets is acceptable if needed

## Questions to Address

### Dependencies (requirements.txt)
- Review and identify unnecessary dependencies
- Confirm which dependencies are essential (e.g., Supabase)
- Determine deployment strategy for Lambda dependencies:
  - Should we use Lambda Layers?
  - Are there alternative approaches?

### API Gateway Security
- What authentication method should we implement for API Gateway?
- Options to consider: API keys, IAM, Cognito, custom authorizers, etc.
