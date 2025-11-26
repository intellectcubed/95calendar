# Why We Don't Use FastAPI in Lambda

## The Question

If we're using FastAPI for local development, why not use it in Lambda too?

## The Answer

**API Gateway already does what FastAPI does**, so using FastAPI in Lambda is redundant and adds unnecessary overhead.

## What API Gateway Provides

When you use API Gateway with Lambda, API Gateway handles:

1. **HTTP Routing** - Maps URLs to your Lambda function
2. **Request Parsing** - Parses HTTP requests into structured events
3. **Response Formatting** - Converts Lambda response to HTTP response
4. **Validation** - Can validate request/response schemas
5. **Authentication** - Supports IAM, Cognito, custom authorizers
6. **CORS** - Handles CORS preflight and headers
7. **Throttling** - Rate limiting and quotas
8. **Caching** - Can cache responses

## What FastAPI Provides

FastAPI is a web framework that handles:

1. **HTTP Routing** - Maps URLs to handler functions ❌ Redundant with API Gateway
2. **Request Parsing** - Parses HTTP requests ❌ Redundant with API Gateway
3. **Response Formatting** - Formats HTTP responses ❌ Redundant with API Gateway
4. **Validation** - Pydantic validation ❌ Redundant with API Gateway schemas
5. **Documentation** - Auto-generated OpenAPI docs ✅ Useful locally, not in Lambda
6. **Dependency Injection** - For shared resources ❌ Not needed for simple handlers
7. **Middleware** - Request/response processing ❌ API Gateway handles this

## The Redundancy Problem

```
┌──────────────────────────────────────────────────┐
│              With FastAPI + Mangum               │
├──────────────────────────────────────────────────┤
│                                                  │
│  API Gateway                                     │
│    │                                             │
│    ├─ Parses HTTP request                       │
│    ├─ Creates Lambda event                      │
│    │                                             │
│    ▼                                             │
│  Lambda                                          │
│    │                                             │
│    ├─ Mangum converts event back to HTTP ❌     │
│    ├─ FastAPI parses HTTP again ❌              │
│    ├─ FastAPI routes to handler ❌              │
│    ├─ Handler processes request ✅              │
│    ├─ FastAPI formats response ❌               │
│    ├─ Mangum converts response to event ❌      │
│    │                                             │
│    ▼                                             │
│  API Gateway                                     │
│    │                                             │
│    ├─ Converts event to HTTP response ❌        │
│    │                                             │
│    ▼                                             │
│  Client gets response                            │
│                                                  │
└──────────────────────────────────────────────────┘

❌ = Redundant work
✅ = Actual business logic
```

## The Simplified Approach

```
┌──────────────────────────────────────────────────┐
│         Without FastAPI (Direct Handler)         │
├──────────────────────────────────────────────────┤
│                                                  │
│  API Gateway                                     │
│    │                                             │
│    ├─ Parses HTTP request                       │
│    ├─ Creates Lambda event                      │
│    │                                             │
│    ▼                                             │
│  Lambda                                          │
│    │                                             │
│    ├─ Handler processes event directly ✅       │
│    ├─ Returns response dict ✅                  │
│    │                                             │
│    ▼                                             │
│  API Gateway                                     │
│    │                                             │
│    ├─ Converts response to HTTP                 │
│    │                                             │
│    ▼                                             │
│  Client gets response                            │
│                                                  │
└──────────────────────────────────────────────────┘

✅ = Necessary work only
```

## Performance Impact

### With FastAPI + Mangum

```python
# Lambda package size
Layer: ~80 MB (FastAPI, Starlette, Pydantic, Mangum, + dependencies)

# Cold start time
~800ms - 1200ms

# Dependencies to manage
- fastapi
- starlette
- pydantic
- mangum
- uvicorn (indirectly)
- + all their dependencies
```

### Without FastAPI (Direct Handler)

```python
# Lambda package size
Layer: ~40 MB (Google Sheets, Supabase, boto3)

# Cold start time
~400ms - 600ms

# Dependencies to manage
- Only what we actually need
- No web framework overhead
```

**Result**: ~50% smaller package, ~50% faster cold starts

## When to Use FastAPI in Lambda

FastAPI + Mangum makes sense when:

1. **Not using API Gateway** - If Lambda is invoked directly or via ALB
2. **Complex middleware** - If you need FastAPI-specific middleware
3. **Code reuse** - If you're deploying the exact same FastAPI app to both Lambda and containers
4. **Rapid prototyping** - When you want to quickly deploy existing FastAPI app

## Our Approach: Best of Both Worlds

### Local Development (FastAPI)
```python
# src/api/calendar_service.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def execute(request: Request):
    # Rich developer experience:
    # - Auto-reload on changes
    # - Interactive docs at /docs
    # - Request validation
    # - Better error messages
    return calendar.execute_command(...)
```

Run with: `uvicorn src.api.calendar_service:app --reload`

### Lambda Production (Direct Handler)
```python
# src/api/lambda_handler_simple.py
def lambda_handler(event, context):
    # Optimized for production:
    # - Minimal dependencies
    # - Fast cold starts
    # - Direct event processing
    query = event.get('queryStringParameters', {})
    return {
        'statusCode': 200,
        'body': json.dumps(
            calendar.execute_command(...)
        )
    }
```

### Shared Business Logic
```python
# src/services/calendar_commands.py
class CalendarCommands:
    def execute_command(self, action, **kwargs):
        # Same logic used by both!
        # No duplication, no divergence
        ...
```

## Key Insight

**Separation of concerns**:
- **API Gateway**: HTTP handling (routing, parsing, auth)
- **Lambda**: Business logic only
- **FastAPI locally**: Developer experience
- **Simple handler in Lambda**: Production efficiency

Don't pay the FastAPI overhead cost in Lambda when API Gateway already provides those features.

## Comparison Table

| Feature | Local (FastAPI) | Lambda (Simple Handler) |
|---------|----------------|------------------------|
| HTTP Routing | FastAPI | API Gateway |
| Request Parsing | FastAPI | API Gateway |
| Validation | Pydantic | Handled in code |
| Auto Docs | ✅ /docs endpoint | ❌ Not needed |
| Auto Reload | ✅ --reload flag | ❌ Not applicable |
| Type Safety | ✅ Pydantic models | ✅ Type hints |
| Dependencies | All (FastAPI+) | Minimal (no web framework) |
| Cold Start | N/A (always warm) | Fast (~400-600ms) |
| Package Size | N/A (local) | Small (~40 MB) |
| Cost | $0 (local) | Pay-per-invoke |

## Conclusion

Using FastAPI in Lambda with API Gateway is like having two translators translate the same message twice. It works, but it's redundant and slow.

Instead:
- **Local**: Use FastAPI for excellent developer experience
- **Lambda**: Use simple event handlers for optimal performance
- **Shared**: Business logic is the same in both

This gives you the best of both worlds: productive development and efficient production.
