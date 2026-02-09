# MRRPulse Quick Start Guide

## 🚀 Starting the Application

### Using the Startup Script (Recommended)

```bash
./start-all.sh
```

This script will:
- Check if Docker Desktop is running (and start it if needed)
- Start all required services (PostgreSQL, LocalStack, Backend, Frontend)
- Display service status and URLs

### Manual Startup

If you prefer to start services manually:

```bash
# Start Docker Desktop (if not running)
open -a Docker

# Wait for Docker to be ready, then start services
docker compose up -d

# Check service status
docker compose ps
```

## 🔐 Test User Credentials

### Default Test User
- **Email**: `test@example.com`
- **Password**: `Test123!`
- **Workspace**: Test User's Workspace (Starter Plan)

### Creating Additional Users

```bash
# Create default test user
docker compose exec backend python scripts/create_test_user.py

# Create admin user
docker compose exec backend python scripts/create_test_user.py --admin
```

## 🌐 Application URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## 📦 Service Management

### View Service Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
docker compose logs -f localstack
```

### Stop Services
```bash
docker compose down
```

### Restart Services
```bash
docker compose restart
```

### Rebuild Services (after code changes)
```bash
# Rebuild and restart
docker compose up -d --build

# Rebuild specific service
docker compose up -d --build backend
```

## 🗄️ Database Management

### Run Migrations
```bash
docker compose exec backend alembic upgrade head
```

### Create New Migration
```bash
docker compose exec backend alembic revision --autogenerate -m "description"
```

### Access PostgreSQL
```bash
docker compose exec postgres psql -U postgres -d mrrpulse
```

Database credentials:
- **Host**: localhost
- **Port**: 5432
- **Database**: mrrpulse
- **Username**: postgres
- **Password**: postgres

## 🔧 Development

### Backend Development (Standalone)
```bash
cd backend
pip install -r requirements.txt

# Set environment variables (or use .env file)
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mrrpulse
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export SQS_EVENTS_QUEUE_URL=http://localhost:4566/000000000000/mrrpulse-events
export SQS_NOTIFICATIONS_QUEUE_URL=http://localhost:4566/000000000000/mrrpulse-notifications
export SQS_RISK_QUEUE_URL=http://localhost:4566/000000000000/mrrpulse-risk
export FRONTEND_URL=http://localhost:3000
export DEBUG=true

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Development (Standalone)
```bash
cd frontend
npm install
npm run dev
```

## 🐛 Troubleshooting

### Docker Desktop Not Starting
```bash
# Check if Docker is running
docker info

# If not, start it manually
open -a Docker

# Wait a few seconds and try again
docker info
```

### Services Not Starting
```bash
# Check logs for errors
docker compose logs

# Try rebuilding
docker compose down
docker compose up -d --build
```

### Database Connection Issues
```bash
# Restart PostgreSQL
docker compose restart postgres

# Check PostgreSQL logs
docker compose logs postgres
```

### Port Already in Use
If you get errors about ports already being used:

```bash
# Check what's using the port (example for port 8000)
lsof -i :8000

# Stop the process or change the port in docker-compose.yml
```

### Clear Everything and Start Fresh
```bash
# Stop and remove all containers, networks, and volumes
docker compose down -v

# Start fresh
docker compose up -d

# Recreate test user
docker compose exec backend python scripts/create_test_user.py
```

## 📝 Notes

- The application uses Docker containers for all services
- LocalStack emulates AWS SQS for local development
- Frontend runs on Next.js 14 with hot reload
- Backend runs on FastAPI with auto-reload enabled
- Database schema is managed with Alembic migrations
- Email verification is bypassed for test users created via script

## 🆘 Need Help?

- Check the main [README.md](./README.md) for detailed documentation
- View API documentation at http://localhost:8000/docs
- Check logs: `docker compose logs -f`
