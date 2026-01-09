.PHONY: up down infra backend frontend logs reset clean build ps

# Start all services
up:
	docker compose up

# Start all services in detached mode
up-d:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Start only infrastructure (PostgreSQL + LocalStack)
infra:
	docker compose up postgres localstack

# Start infrastructure in detached mode
infra-d:
	docker compose up -d postgres localstack

# Run backend locally (requires venv activation first)
backend:
	cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Run frontend locally
frontend:
	cd frontend && npm run dev

# View logs from all services
logs:
	docker compose logs -f

# View logs from specific service (usage: make log-backend, make log-frontend)
log-%:
	docker compose logs -f $*

# Stop all services and remove volumes
reset:
	docker compose down -v

# Build/rebuild containers
build:
	docker compose build

# Show running containers
ps:
	docker compose ps

# Install frontend dependencies
install-frontend:
	cd frontend && npm install

# Install backend dependencies
install-backend:
	cd backend && pip install -r requirements.txt

# Install all dependencies
install: install-frontend install-backend

# Run frontend build
build-frontend:
	cd frontend && npm run build

# Lint frontend
lint:
	cd frontend && npm run lint
