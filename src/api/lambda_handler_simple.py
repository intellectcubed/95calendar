# lambda_handler_simple.py
"""
Simplified AWS Lambda handler that directly processes API Gateway events.
No FastAPI/Mangum overhead - just direct event processing.
"""
import json
import os
from typing import Dict, Any
from src.services.calendar_commands import CalendarCommands
from src.models.calendar_models import DaySchedule
from src.config.aws_config import config


# Initialize CalendarCommands once (outside handler for warm starts)
spreadsheet_id = config.get_required('SPREADSHEET_ID')
# In Lambda, credentials.json is at the root of the package
credentials_path = 'credentials.json' if config.is_lambda else 'config/credentials.json'
calendar = CalendarCommands(spreadsheet_id, credentials_path=credentials_path, live_test=False)


def create_response(status_code: int, body: Any) -> Dict[str, Any]:
    """
    Create API Gateway response.

    Args:
        status_code: HTTP status code
        body: Response body (will be JSON encoded)

    Returns:
        API Gateway response dict
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # Adjust for your CORS needs
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(body)
    }


def handle_get_root(query_params: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle GET / endpoint with query parameters.

    Args:
        query_params: Query string parameters from API Gateway

    Returns:
        API Gateway response
    """
    action = query_params.get('action')
    if not action:
        return create_response(400, {
            'status': 'error',
            'message': "Missing 'action' parameter"
        })

    try:
        # Convert string parameters to appropriate types
        params = dict(query_params)
        params.pop('action')  # Remove action from params

        if 'squad' in params:
            params['squad'] = int(params['squad'])

        # Convert preview parameter from string to boolean
        if 'preview' in params:
            preview_str = params['preview'].lower()
            params['preview'] = preview_str in ('true', '1', 'yes')

        # Execute the command
        result = calendar.execute_command(action, **params)
        return create_response(200, result)

    except ValueError as e:
        return create_response(400, {
            'status': 'error',
            'message': f'Invalid parameter value: {str(e)}'
        })
    except Exception as e:
        return create_response(500, {
            'status': 'error',
            'message': str(e)
        })


def handle_post_apply(path_params: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /calendar/day/{calendar_date}/apply endpoint.

    Args:
        path_params: Path parameters from API Gateway
        body: Request body

    Returns:
        API Gateway response
    """
    try:
        calendar_date = path_params.get('calendar_date')
        if not calendar_date:
            return create_response(400, {
                'success': False,
                'error': 'Missing calendar_date in path'
            })

        day_schedule_json = body.get('DaySchedule')
        if not day_schedule_json:
            return create_response(400, {
                'success': False,
                'error': 'Missing DaySchedule in request body'
            })

        commands = body.get('commands')

        # Parse the DaySchedule to validate it
        day_schedule = DaySchedule.from_json(day_schedule_json)

        # Execute the command
        result = calendar.execute_command(
            action='apply_external_schedule',
            date=calendar_date,
            external_mod_day_schedule=day_schedule_json,
            commands=commands
        )

        return create_response(200, result)

    except json.JSONDecodeError as e:
        return create_response(400, {
            'success': False,
            'error': f'Invalid JSON in DaySchedule: {str(e)}'
        })
    except Exception as e:
        return create_response(500, {
            'success': False,
            'error': str(e)
        })


def handle_post_preview(path_params: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /calendar/day/{calendar_date}/preview endpoint.

    Args:
        path_params: Path parameters from API Gateway
        body: Request body

    Returns:
        API Gateway response
    """
    try:
        calendar_date = path_params.get('calendar_date')
        if not calendar_date:
            return create_response(400, {
                'success': False,
                'error': 'Missing calendar_date in path'
            })

        action = body.get('action')
        if not action:
            return create_response(400, {
                'success': False,
                'error': 'Missing action in request body'
            })

        day_schedule_json = body.get('day_schedule')
        if not day_schedule_json:
            return create_response(400, {
                'success': False,
                'error': 'Missing day_schedule in request body'
            })

        # Parse the DaySchedule
        day_schedule = DaySchedule.from_json(day_schedule_json)

        # Build kwargs for execute_command
        kwargs = {
            'date': body.get('date', calendar_date),
            'day_schedule': day_schedule,
            'preview': True  # Always preview mode for this endpoint
        }

        # Add optional parameters
        if body.get('shift_start'):
            kwargs['shift_start'] = body['shift_start']
        if body.get('shift_end'):
            kwargs['shift_end'] = body['shift_end']
        if body.get('squad') is not None:
            kwargs['squad'] = int(body['squad'])

        # Execute the command in preview mode
        result = calendar.execute_command(action=action, **kwargs)

        return create_response(200, result)

    except json.JSONDecodeError as e:
        return create_response(400, {
            'success': False,
            'error': f'Invalid JSON in day_schedule: {str(e)}'
        })
    except Exception as e:
        return create_response(500, {
            'success': False,
            'error': str(e)
        })


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for API Gateway events.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        query_params = event.get('queryStringParameters') or {}
        path_params = event.get('pathParameters') or {}

        # Parse body if present
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return create_response(400, {
                    'status': 'error',
                    'message': 'Invalid JSON in request body'
                })

        # Route based on method and path
        if http_method == 'GET' and path == '/':
            return handle_get_root(query_params)

        elif http_method == 'POST' and '/apply' in path:
            return handle_post_apply(path_params, body)

        elif http_method == 'POST' and '/preview' in path:
            return handle_post_preview(path_params, body)

        elif http_method == 'OPTIONS':
            # Handle CORS preflight
            return create_response(200, {})

        else:
            return create_response(404, {
                'status': 'error',
                'message': f'Not found: {http_method} {path}'
            })

    except Exception as e:
        # Catch-all error handler
        print(f"Unhandled error: {str(e)}")
        import traceback
        traceback.print_exc()

        return create_response(500, {
            'status': 'error',
            'message': 'Internal server error'
        })
