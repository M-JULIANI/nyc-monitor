.PHONY: install dev build test deploy clean lint format

# Variables
DOCKER_REGISTRY ?= $(shell grep DOCKER_REGISTRY .env 2>/dev/null | cut -d '=' -f2 || echo "localhost")
DOCKER_IMAGE_PREFIX ?= $(shell grep DOCKER_IMAGE_PREFIX .env 2>/dev/null | cut -d '=' -f2 || echo "atlas")
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")

# Development environment
install:
	@echo "Installing dependencies..."
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry install; \
	fi
	@if [ -f "frontend/package.json" ]; then \
		cd frontend && npm install; \
	fi

dev:
	@echo "Starting development environment..."
	docker compose up --build

dev-backend:
	@echo "Starting backend development server..."
	docker compose up backend

dev-frontend:
	@echo "Starting frontend development server..."
	docker compose up frontend

# Building
build:
	@echo "Building Docker images..."
	docker compose build

build-backend:
	@echo "Building backend Docker image..."
	docker compose build backend

build-frontend:
	@echo "Building frontend Docker image..."
	docker compose build frontend

# Testing
test:
	@echo "Running tests..."
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry run pytest; \
	fi
	@if [ -f "frontend/package.json" ]; then \
		cd frontend && npm test; \
	fi

test-backend:
	@echo "Running backend tests..."
	cd backend && poetry run pytest

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm test

# Linting and Formatting
lint:
	@echo "Running linters..."
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry run ruff check .; \
	fi
	@if [ -f "frontend/package.json" ]; then \
		cd frontend && npm run lint; \
	fi

format:
	@echo "Formatting code..."
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry run black . && poetry run ruff format .; \
	fi
	@if [ -f "frontend/package.json" ]; then \
		cd frontend && npm run format; \
	fi

# Deployment
deploy:
	@echo "Deploying to production..."
	# Build and push Docker images
	docker build -t $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-backend:$(VERSION) -f backend/Dockerfile backend/
	docker build -t $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:$(VERSION) -f frontend/Dockerfile frontend/
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-backend:$(VERSION)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:$(VERSION)
	# Deploy backend agent
	cd backend && poetry run python deployment/deploy.py

# Cleanup
clean:
	@echo "Cleaning up..."
	docker compose down -v
	rm -rf backend/.venv frontend/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Help
help:
	@echo "Available commands:"
	@echo "  make install        - Install all dependencies"
	@echo "  make dev           - Start development environment (both services)"
	@echo "  make dev-backend   - Start backend development server"
	@echo "  make dev-frontend  - Start frontend development server"
	@echo "  make build         - Build all Docker images"
	@echo "  make build-backend - Build backend Docker image"
	@echo "  make build-frontend- Build frontend Docker image"
	@echo "  make test          - Run all tests"
	@echo "  make test-backend  - Run backend tests"
	@echo "  make test-frontend - Run frontend tests"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo "  make deploy        - Deploy to production"
	@echo "  make clean         - Clean up development environment" 