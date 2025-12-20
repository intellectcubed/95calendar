# Docker Deployment Guide

This guide explains how to run the Calendar Service as a Docker container instead of an AWS Lambda function.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, but recommended)
- Google Service Account credentials
- Environment variables configured

## Quick Start

### Using Docker Compose (Recommended)

1. **Configure environment variables**

   Copy the example environment file and update with your values:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set your configuration:
   - `ENVIRONMENT` - Set to `test` or `production`
   - `TEST_SPREADSHEET_ID` - Your test Google Sheets ID
   - `PROD_SPREADSHEET_ID` - Your production Google Sheets ID
   - `TEST_SUPABASE_URL` and `TEST_SUPABASE_KEY` - Test Supabase credentials
   - `PROD_SUPABASE_URL` and `PROD_SUPABASE_KEY` - Production Supabase credentials

2. **Set up Google Service Account credentials**

   Place your service account JSON file in the `credentials/` directory:
   ```bash
   mkdir -p credentials
   cp /path/to/your/service-account.json credentials/
   ```

3. **Start the service**
   ```bash
   docker-compose up -d
   ```

4. **Check the service is running**
   ```bash
   curl http://localhost:8000/health
   ```

### Using Docker Directly

1. **Build the image**
   ```bash
   docker build -t calendar-service .
   ```

2. **Run the container**
   ```bash
   docker run -d \
     --name calendar-service \
     -p 8000:8000 \
     --env-file .env \
     -v $(pwd)/credentials:/app/credentials:ro \
     calendar-service
   ```

## API Endpoints

The service exposes the following endpoints:

- `GET /health` - Health check endpoint
- `GET /?action=<action>&date=<date>&...` - Execute calendar commands
- `POST /calendar/day/{date}/apply` - Apply external schedule
- `POST /calendar/day/{date}/preview` - Preview command without applying

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment mode | `test` or `production` |
| `TEST_SPREADSHEET_ID` | Test Google Sheets ID | `1abc...xyz` |
| `PROD_SPREADSHEET_ID` | Production Google Sheets ID | `1abc...xyz` |
| `TEST_SUPABASE_URL` | Test Supabase URL | `https://xxx.supabase.co` |
| `TEST_SUPABASE_KEY` | Test Supabase anon key | `eyJ...` |
| `PROD_SUPABASE_URL` | Production Supabase URL | `https://xxx.supabase.co` |
| `PROD_SUPABASE_KEY` | Production Supabase key | `eyJ...` |

## Development

For development with live code reloading:

1. The `docker-compose.yml` is already configured to mount the `src/` directory
2. Make changes to your code
3. The server will automatically reload (uvicorn auto-reload is enabled in development)

To view logs:
```bash
docker-compose logs -f calendar-service
```

## Production Deployment

### Building for Production

1. **Build the production image**
   ```bash
   docker build -t calendar-service:latest .
   ```

2. **Tag for your registry**
   ```bash
   docker tag calendar-service:latest your-registry.com/calendar-service:latest
   ```

3. **Push to registry**
   ```bash
   docker push your-registry.com/calendar-service:latest
   ```

### Deployment Options

#### Option 1: Amazon ECS/Fargate

1. Create an ECS task definition using your Docker image
2. Configure environment variables in the task definition
3. Mount secrets from AWS Secrets Manager if needed
4. Deploy to ECS cluster or Fargate

#### Option 2: Kubernetes

Create a deployment YAML:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calendar-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: calendar-service
  template:
    metadata:
      labels:
        app: calendar-service
    spec:
      containers:
      - name: calendar-service
        image: your-registry.com/calendar-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        envFrom:
        - secretRef:
            name: calendar-service-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: calendar-service
spec:
  selector:
    app: calendar-service
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### Option 3: Docker Swarm

```bash
docker service create \
  --name calendar-service \
  --replicas 3 \
  --publish 8000:8000 \
  --env-file .env \
  --mount type=bind,source=/path/to/credentials,target=/app/credentials,readonly \
  calendar-service:latest
```

## Monitoring

The container includes a built-in health check that runs every 30 seconds:

```bash
# Check container health
docker ps

# View health check logs
docker inspect --format='{{json .State.Health}}' calendar-service | jq
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs calendar-service
```

### Can't connect to Google Sheets

1. Verify credentials file is mounted correctly
2. Check `GOOGLE_APPLICATION_CREDENTIALS` environment variable
3. Ensure service account has proper permissions

### Environment variables not loading

1. Verify `.env` file exists and has correct values
2. Check docker-compose.yml has `env_file` configured
3. Restart containers after changing `.env`

## Differences from Lambda Deployment

| Aspect | Lambda | Docker |
|--------|--------|--------|
| Entry Point | `lambda_handler.py` with Mangum | `server.py` with uvicorn |
| Secrets | AWS Secrets Manager | Environment variables or mounted secrets |
| Scaling | Auto-scales per request | Manual scaling with orchestrator |
| Cold Start | Yes (can be slow) | No (always warm) |
| Cost Model | Pay per request | Pay for uptime |

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
