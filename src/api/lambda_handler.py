# lambda_handler.py
"""
AWS Lambda handler for the calendar service.
Wraps the FastAPI application using Mangum.
"""
from mangum import Mangum
from src.api.calendar_service import app

# Create Lambda handler
handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Args:
        event: Lambda event from API Gateway
        context: Lambda context

    Returns:
        API Gateway response
    """
    return handler(event, context)
