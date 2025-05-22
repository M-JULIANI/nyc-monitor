.PHONY: install dev build test deploy clean lint format devcontainer-setup devcontainer-clean check-deps check-docker check-gcloud

# Variables
GOOGLE_CLOUD_PROJECT ?= $(shell grep -E '^GOOGLE_CLOUD_PROJECT=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
GOOGLE_CLOUD_LOCATION ?= $(shell grep -E '^GOOGLE_CLOUD_LOCATION=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ' || echo "us-central1")
STAGING_BUCKET ?= $(shell grep -E '^STAGING_BUCKET=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ' || echo "gs://$(GOOGLE_CLOUD_PROJECT)-vertex-deploy")
DOCKER_REGISTRY ?= $(shell grep -E '^DOCKER_REGISTRY=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ' || echo "localhost")
DOCKER_IMAGE_PREFIX ?= $(shell grep -E '^DOCKER_IMAGE_PREFIX=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ' || echo "atlas")
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")

# Ensure PATH includes user's local bin
SHELL := /bin/bash
export PATH := /home/vscode/.local/bin:$(PATH)

# Check dependencies
check-deps:
	@echo "Checking dependencies..."
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "Installing Poetry..."; \
		curl -sSL https://install.python-poetry.org | python3 -; \
	fi
	@if ! command -v npm >/dev/null 2>&1; then \
		echo "Installing Node.js..."; \
		curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -; \
		sudo apt-get install -y nodejs; \
	fi
	@echo "Updating npm to latest version..."
	@if command -v npm >/dev/null 2>&1; then \
		sudo npm install -g npm@latest; \
	fi
	@echo "Dependencies check complete"

# Check Google Cloud setup
check-gcloud:
	@echo "Checking Google Cloud setup..."
	@if ! command -v gcloud >/dev/null 2>&1; then \
		echo "Error: gcloud CLI not found. Please install Google Cloud SDK."; \
		exit 1; \
	fi
	@if [ -z "$(GOOGLE_CLOUD_PROJECT)" ]; then \
		echo "Error: GOOGLE_CLOUD_PROJECT not set in .env file"; \
		exit 1; \
	fi
	@if [ -z "$(STAGING_BUCKET)" ]; then \
		echo "Error: STAGING_BUCKET not set in .env file"; \
		exit 1; \
	fi
	@if ! gcloud projects describe "$(GOOGLE_CLOUD_PROJECT)" >/dev/null 2>&1; then \
		echo "Error: Project $(GOOGLE_CLOUD_PROJECT) not found or not accessible"; \
		exit 1; \
	fi
	@if ! gsutil ls "$(STAGING_BUCKET)" >/dev/null 2>&1; then \
		echo "Creating staging bucket $(STAGING_BUCKET)..."; \
		gsutil mb -l "$(GOOGLE_CLOUD_LOCATION)" "$(STAGING_BUCKET)"; \
	fi
	@echo "Google Cloud setup verified"

# Development environment
install: check-deps install-backend install-frontend
	@echo "All dependencies installed successfully"

install-backend:
	@echo "Installing backend dependencies..."
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry install; \
	else \
		echo "Warning: backend/pyproject.toml not found"; \
	fi

install-frontend:
	@echo "Installing frontend dependencies..."
	@if [ -f "frontend/package.json" ]; then \
		cd frontend && \
		npm install --no-audit --no-fund && \
		npm update --no-audit --no-fund; \
	else \
		echo "Warning: frontend/package.json not found"; \
	fi

# Devcontainer specific commands
devcontainer-setup: check-deps install check-gcloud
	@echo "Setting up devcontainer environment..."
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry config virtualenvs.in-project true; \
	fi
	@if [ -f "frontend/package.json" ]; then \
		cd frontend && npm config set prefix /home/vscode/.npm-global; \
	fi
	@echo "Running grant_permissions.sh..."
	@if [ -f "backend/deployment/grant_permissions.sh" ]; then \
		chmod +x backend/deployment/grant_permissions.sh && \
		./backend/deployment/grant_permissions.sh; \
	fi
	@echo "Devcontainer setup complete"

devcontainer-clean:
	@echo "Cleaning devcontainer environment..."
	rm -rf backend/.venv frontend/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Devcontainer cleanup complete"

# Development servers
dev:
	@echo "Starting development environment..."
	@echo "Starting backend..."
	@cd backend && poetry run uvicorn rag.main:app --host 0.0.0.0 --port 8000 --reload & \
	echo "Starting frontend..." && \
	cd frontend && npm run dev -- --host 0.0.0.0

dev-backend:
	@echo "Starting backend development server..."
	cd backend && poetry run uvicorn rag.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend:
	@echo "Starting frontend development server..."
	cd frontend && npm run dev -- --host 0.0.0.0

# Testing
test: test-backend test-frontend
	@echo "All tests completed"

test-backend:
	@echo "Running backend tests..."
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry run pytest; \
	fi

test-frontend:
	@echo "Running frontend tests..."
	@if [ -f "frontend/package.json" ]; then \
		cd frontend && npm test; \
	fi

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

# Check Docker permissions
check-docker:
	@echo "Checking Docker permissions..."
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Error: Docker is not installed. Required for building production images."; \
		exit 1; \
	fi
	@if ! docker info >/dev/null 2>&1; then \
		echo "Error: Docker daemon is not accessible. Please ensure:"; \
		echo "1. Docker daemon is running"; \
		echo "2. You have permission to access /var/run/docker.sock"; \
		echo "3. You are in the docker group"; \
		echo "Try rebuilding the devcontainer with: Dev Containers: Rebuild Container"; \
		exit 1; \
	fi

# Production Build (Frontend only - Backend uses Vertex AI)
build: build-frontend
	@echo "Production build completed"

build-frontend: check-docker
	@echo "Building frontend production image..."
	@if [ -f "frontend/Dockerfile" ]; then \
		docker build \
			-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:$(VERSION)" \
			-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:latest" \
			-f frontend/Dockerfile frontend/; \
	else \
		echo "Error: frontend/Dockerfile not found"; \
		exit 1; \
	fi

# Cloud Run Configuration (frontend)
CLOUD_RUN_SERVICE_NAME ?= $(DOCKER_IMAGE_PREFIX)-frontend
CLOUD_RUN_REGION ?= $(GOOGLE_CLOUD_LOCATION)
CLOUD_RUN_MIN_INSTANCES ?= 1
CLOUD_RUN_MAX_INSTANCES ?= 20
CLOUD_RUN_CPU ?= 1
CLOUD_RUN_MEMORY ?= 512Mi
CLOUD_RUN_CONCURRENCY ?= 80
CLOUD_RUN_TIMEOUT ?= 300s

# Deployment
deploy: deploy-backend deploy-frontend
	@echo "Deployment completed"

deploy-backend: check-gcloud
	@echo "Deploying backend to Vertex AI..."
	@if [ -f "backend/deployment/deploy.py" ]; then \
		cd backend && poetry run python deployment/deploy.py; \
	else \
		echo "Error: backend/deployment/deploy.py not found"; \
		exit 1; \
	fi

deploy-frontend: check-docker build-frontend deploy-cloudrun
	@echo "Frontend deployment completed"

deploy-cloudrun: check-gcloud
	@echo "Deploying frontend to Cloud Run..."
	@if [ -z "$(DOCKER_REGISTRY)" ] || [ "$(DOCKER_REGISTRY)" = "localhost" ]; then \
		echo "Error: DOCKER_REGISTRY must be set for frontend deployment"; \
		exit 1; \
	fi
	@echo "Building and pushing frontend images..."
	@if ! docker build \
		-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:$(VERSION)" \
		-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:latest" \
		-f frontend/Dockerfile frontend/; then \
		echo "Error: Failed to build frontend image"; \
		exit 1; \
	fi
	@echo "Pushing images to registry..."
	@if ! docker push "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:$(VERSION)"; then \
		echo "Error: Failed to push versioned image"; \
		exit 1; \
	fi
	@if ! docker push "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:latest"; then \
		echo "Error: Failed to push latest image"; \
		exit 1; \
	fi
	@echo "Getting backend endpoint URL..."
	@BACKEND_URL=$$(gcloud ai endpoints list \
		--project=$(GOOGLE_CLOUD_PROJECT) \
		--region=$(GOOGLE_CLOUD_LOCATION) \
		--format='value(displayName,id)' | grep "$(DOCKER_IMAGE_PREFIX)-backend" | head -n1 | awk '{print "https://$(GOOGLE_CLOUD_LOCATION)-$(GOOGLE_CLOUD_PROJECT).aiplatform.googleapis.com/v1/projects/$(GOOGLE_CLOUD_PROJECT)/locations/$(GOOGLE_CLOUD_LOCATION)/endpoints/" $$2}') && \
	if [ -z "$$BACKEND_URL" ]; then \
		echo "Warning: Could not find backend endpoint. Setting VITE_API_URL to empty string."; \
		BACKEND_URL=""; \
	fi
	@echo "Deploying to Cloud Run..."
	@gcloud run deploy $(CLOUD_RUN_SERVICE_NAME) \
		--image "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:$(VERSION)" \
		--platform managed \
		--region $(CLOUD_RUN_REGION) \
		--min-instances $(CLOUD_RUN_MIN_INSTANCES) \
		--max-instances $(CLOUD_RUN_MAX_INSTANCES) \
		--cpu $(CLOUD_RUN_CPU) \
		--memory $(CLOUD_RUN_MEMORY) \
		--concurrency $(CLOUD_RUN_CONCURRENCY) \
		--timeout $(CLOUD_RUN_TIMEOUT) \
		--allow-unauthenticated \
		--set-env-vars="VITE_API_URL=$$BACKEND_URL" \
		--port 8080 \
		--use-http2
	@echo "Cloud Run deployment completed. Service URL:"
	@gcloud run services describe $(CLOUD_RUN_SERVICE_NAME) \
		--platform managed \
		--region $(CLOUD_RUN_REGION) \
		--format='value(status.url)'

# Cleanup
clean:
	@echo "Cleaning up development environment..."
	rm -rf backend/.venv frontend/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Help
help:
	@echo "Development Commands:"
	@echo "  make install           - Install all dependencies"
	@echo "  make install-backend   - Install backend dependencies"
	@echo "  make install-frontend  - Install frontend dependencies"
	@echo "  make dev              - Start development environment (both services)"
	@echo "  make dev-backend      - Start backend development server"
	@echo "  make dev-frontend     - Start frontend development server"
	@echo "  make test             - Run all tests"
	@echo "  make test-backend     - Run backend tests"
	@echo "  make test-frontend    - Run frontend tests"
	@echo "  make lint             - Run linters"
	@echo "  make format           - Format code"
	@echo "  make clean            - Clean up development environment"
	@echo ""
	@echo "Devcontainer Commands:"
	@echo "  make devcontainer-setup  - Set up devcontainer environment"
	@echo "  make devcontainer-clean  - Clean devcontainer environment"
	@echo ""
	@echo "Production Commands:"
	@echo "  make build            - Build frontend production image"
	@echo "  make deploy           - Deploy both backend (Vertex AI) and frontend"
	@echo "  make deploy-backend   - Deploy backend agent to Vertex AI"
	@echo "  make deploy-frontend  - Deploy frontend container" 