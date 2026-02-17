# API Configuration

## Overview

The frontend is configured to work with different API URLs in different environments:

- **Local Development**: Uses `http://localhost:8000`
- **Deployed/Production**: Uses the ALB URL (configured at runtime)

## How It Works

### Build Time
During the Docker build, the API URL is set to a placeholder `__RUNTIME_API_URL__` which gets compiled into the JavaScript bundles.

### Runtime (Deployed Environment)
When the Docker container starts:
1. The `docker-entrypoint.sh` script runs
2. It reads the `NEXT_PUBLIC_API_URL` environment variable from ECS
3. It uses `sed` to replace all occurrences of `__RUNTIME_API_URL__` with the actual API URL
4. The Next.js server starts with the correct API URL

### Local Development
For local development, use the `.env.local` file:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This file is already configured and works with `npm run dev`.

## Testing

### Deployed Environment
```bash
# Check the API URL in use
curl -s http://<alb-dns-name>/api/health

# Test login endpoint
curl -X POST http://<alb-dns-name>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

### Local Environment
```bash
# Start the backend
cd backend
uvicorn app.main:app --reload

# In another terminal, start the frontend
cd frontend
npm run dev
```

Then visit http://localhost:3000 and the frontend will call http://localhost:8000/api/*

## Files Modified

- `frontend/Dockerfile` - Updated to use placeholder and entrypoint script
- `frontend/docker-entrypoint.sh` - Script to replace API URL at runtime
- `frontend/.env.local` - Local development configuration (already existed)

## Troubleshooting

If API calls are going to the wrong URL:

1. **In deployed environment**: Check CloudWatch logs for "Configuring API URL" message
2. **In local environment**: Verify `.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000`
3. **In browser**: Open Developer Tools > Network tab to see actual API calls
