.PHONY: install dev build test deploy clean lint format devcontainer-setup devcontainer-clean check-deps check-docker check-gcloud deploy-monitor build-monitor setup-monitor test-monitor check-domain remove-domain list-domains setup-domain-direct

# Variables
GOOGLE_CLOUD_PROJECT ?= $(shell grep -E '^GOOGLE_CLOUD_PROJECT=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
GOOGLE_CLOUD_LOCATION ?= $(shell grep -E '^GOOGLE_CLOUD_LOCATION=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ' || echo "us-central1")
STAGING_BUCKET ?= $(shell grep -E '^STAGING_BUCKET=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ' || echo "gs://$(GOOGLE_CLOUD_PROJECT)-vertex-deploy")
DOCKER_REGISTRY ?= $(shell grep -E '^DOCKER_REGISTRY=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ' || echo "localhost")
DOCKER_IMAGE_PREFIX ?= $(shell grep -E '^DOCKER_IMAGE_PREFIX=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ' || echo "atlas")
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")

# Auth variables - check environment first, then .env file
ifeq ($(origin GOOGLE_CLIENT_ID), environment)
    # Use environment variable as-is
else
    GOOGLE_CLIENT_ID := $(shell grep -E '^GOOGLE_CLIENT_ID=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
endif

ifeq ($(origin RAG_CORPUS), environment)
    # Use environment variable as-is
else
    RAG_CORPUS := $(shell grep -E '^RAG_CORPUS=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
endif

# Email whitelist variables
ifeq ($(origin ADMIN_EMAILS), environment)
    # Use environment variable as-is
else
    ADMIN_EMAILS := $(shell grep -E '^ADMIN_EMAILS=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
endif

ifeq ($(origin JUDGE_EMAILS), environment)
    # Use environment variable as-is
else
    JUDGE_EMAILS := $(shell grep -E '^JUDGE_EMAILS=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
endif

# Google Slides integration variables
ifeq ($(origin GOOGLE_DRIVE_FOLDER_ID), environment)
    # Use environment variable as-is
else
    GOOGLE_DRIVE_FOLDER_ID := $(shell grep -E '^GOOGLE_DRIVE_FOLDER_ID=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
endif

ifeq ($(origin STATUS_TRACKER_TEMPLATE_ID), environment)
    # Use environment variable as-is
else
    STATUS_TRACKER_TEMPLATE_ID := $(shell grep -E '^STATUS_TRACKER_TEMPLATE_ID=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
endif

# Google Custom Search fallback variables
ifeq ($(origin GOOGLE_CUSTOM_SEARCH_API_KEY), environment)
    # Use environment variable as-is
else
    GOOGLE_CUSTOM_SEARCH_API_KEY := $(shell grep -E '^GOOGLE_CUSTOM_SEARCH_API_KEY=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
endif

ifeq ($(origin GOOGLE_CUSTOM_SEARCH_ENGINE_ID), environment)
    # Use environment variable as-is
else
    GOOGLE_CUSTOM_SEARCH_ENGINE_ID := $(shell grep -E '^GOOGLE_CUSTOM_SEARCH_ENGINE_ID=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
endif

# Google Maps API key (for map image generation)
ifeq ($(origin GOOGLE_MAPS_API_KEY), environment)
    # Use environment variable as-is
else
    GOOGLE_MAPS_API_KEY := $(shell grep -E '^GOOGLE_MAPS_API_KEY=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
endif

# NYC 311 API token (for 311 service requests data)
ifeq ($(origin NYC_311_APP_TOKEN), environment)
    # Use environment variable as-is
else
    NYC_311_APP_TOKEN := $(shell grep -E '^NYC_311_APP_TOKEN=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
endif

# Monitor system variables
MONITOR_SERVICE_ACCOUNT ?= atlas-monitor-service
MONITOR_JOB_NAME ?= atlas-monitor
MONITOR_SCHEDULER_NAME ?= atlas-monitor-monitor
MONITOR_IMAGE ?= $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-monitor

# NYC 311 job variables
NYC311_JOB_NAME ?= atlas-nyc311
NYC311_SCHEDULER_NAME ?= atlas-nyc311-daily
NYC311_IMAGE ?= $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-nyc311

# Get project number for Cloud Run API endpoints (needed for scheduler URLs)
GOOGLE_CLOUD_PROJECT_NUMBER ?= $(shell gcloud projects describe $(GOOGLE_CLOUD_PROJECT) --format='value(projectNumber)')

# Cloud Run API URLs for scheduler
CLOUD_RUN_API_BASE := https://$(GOOGLE_CLOUD_LOCATION)-run.googleapis.com/apis/run.googleapis.com/v1
CLOUD_RUN_JOB_URL := $(CLOUD_RUN_API_BASE)/namespaces/$(GOOGLE_CLOUD_PROJECT_NUMBER)/jobs/$(MONITOR_JOB_NAME):run
NYC311_JOB_EXEC_URL := https://run.googleapis.com/v2/projects/$(GOOGLE_CLOUD_PROJECT)/locations/$(GOOGLE_CLOUD_LOCATION)/jobs/$(NYC311_JOB_NAME):run

# Alternative: Use gcloud execution URL for Cloud Run Jobs
CLOUD_RUN_JOB_EXEC_URL := https://run.googleapis.com/v2/projects/$(GOOGLE_CLOUD_PROJECT)/locations/$(GOOGLE_CLOUD_LOCATION)/jobs/$(MONITOR_JOB_NAME):run

# Reddit API credentials (for monitor system)
REDDIT_CLIENT_ID ?= $(shell grep -E '^REDDIT_CLIENT_ID=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
REDDIT_CLIENT_SECRET ?= $(shell grep -E '^REDDIT_CLIENT_SECRET=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
REDDIT_REFRESH_TOKEN ?= $(shell grep -E '^REDDIT_REFRESH_TOKEN=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')

# Twitter API credentials (for monitor system)
TWITTER_API_KEY ?= $(shell grep -E '^TWITTER_API_KEY=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
TWITTER_API_KEY_SECRET ?= $(shell grep -E '^TWITTER_API_KEY_SECRET=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')
TWITTER_BEARER_TOKEN ?= $(shell grep -E '^TWITTER_BEARER_TOKEN=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')

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
install: check-deps install-api install-web
	@echo "All dependencies installed successfully"

install-api:
	@echo "Installing backend dependencies..."
	@echo "DOCKER_REGISTRY is: '$(DOCKER_REGISTRY)'"
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry install; \
	else \
		echo "Warning: backend/pyproject.toml not found"; \
	fi

install-web:
	@echo "Installing frontend dependencies with pnpm..."
	@if ! command -v pnpm >/dev/null 2>&1; then \
		echo "Installing pnpm..."; \
		curl -fsSL https://get.pnpm.io/install.sh | sh -; \
	fi
	@if [ -f "frontend/package.json" ]; then \
		cd frontend && PATH="$$HOME/.local/share/pnpm:$$PATH" pnpm install; \
	else \
		echo "Warning: frontend/package.json not found"; \
	fi

install-web-test:
	@echo "Installing frontend test dependencies (Vitest, TypeScript)..."
	cd frontend && \
	npm install --save-dev vitest

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

dev-api:
	@echo "Starting backend development server..."
	cd backend && poetry run uvicorn rag.main:app --host 0.0.0.0 --port 8000 --reload

dev-web:
	@echo "Starting frontend development server..."
	@if ! command -v pnpm >/dev/null 2>&1; then \
		echo "pnpm not found, installing..."; \
		curl -fsSL https://get.pnpm.io/install.sh | sh -; \
	fi
	cd frontend && PATH="$$HOME/.local/share/pnpm:$$PATH" pnpm run dev -- --host 0.0.0.0

# Test against deployed backend
dev-web-deployed:
	@echo "Starting frontend with deployed backend..."
	@echo "Backend URL: https://atlas-backend-blz2r3yjgq-uc.a.run.app"
	@if ! command -v pnpm >/dev/null 2>&1; then \
		echo "pnpm not found, installing..."; \
		curl -fsSL https://get.pnpm.io/install.sh | sh -; \
	fi
	@cd frontend && PATH="$$HOME/.local/share/pnpm:$$PATH" REACT_APP_USE_DEPLOYED_BACKEND=true pnpm run dev -- --host 0.0.0.0

# Get deployed backend URL
get-api-url: check-gcloud
	@echo "🔗 Deployed backend URL:"
	@gcloud run services describe $(CLOUD_RUN_BACKEND_SERVICE_NAME) \
		--platform managed \
		--region $(CLOUD_RUN_REGION) \
		--format='value(status.url)'

# Test deployed services
test-deployed-api:
	@echo "🧪 Testing deployed backend health..."
	@BACKEND_URL=$$(gcloud run services describe $(CLOUD_RUN_BACKEND_SERVICE_NAME) --platform managed --region $(CLOUD_RUN_REGION) --format='value(status.url)' 2>/dev/null || echo "https://atlas-backend-blz2r3yjgq-uc.a.run.app"); \
	echo "Testing: $$BACKEND_URL/api/health"; \
	curl -f "$$BACKEND_URL/api/health" || echo "❌ Backend health check failed"

# Testing
test: test-api test-web
	@echo "All tests completed"

test-api:
	@echo "Running backend tests (excluding real integration tests)..."
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry run pytest -m "not real_integration"; \
	fi

test-web:
	@echo "Running frontend tests..."
	@if ! command -v pnpm >/dev/null 2>&1; then \
		echo "pnpm not found, installing..."; \
		curl -fsSL https://get.pnpm.io/install.sh | sh -; \
	fi
	@if [ -f "frontend/package.json" ]; then \
		cd frontend && PATH="$$HOME/.local/share/pnpm:$$PATH" pnpm test; \
	fi

# Backend test variants
test-unit:
	@echo "Running unit tests only..."
	cd backend && poetry run pytest -m unit

test-integration:
	@echo "Running mocked integration tests..."
	cd backend && poetry run pytest -m integration

test-integration-real:
	@echo "🚨 Running REAL integration tests (requires API credentials)..."
	@echo "⚠️  This will make actual API calls and may cost money!"
	@echo "⚠️  Ensure you have the following environment variables set:"
	@echo "   - GOOGLE_MAPS_API_KEY"
	@echo "   - GOOGLE_CUSTOM_SEARCH_API_KEY"
	@echo "   - GOOGLE_DRIVE_FOLDER_ID"
	@echo "   - STATUS_TRACKER_TEMPLATE_ID"
	@echo "   - GOOGLE_SLIDES_SERVICE_ACCOUNT_KEY_BASE64"
	@read -p "Continue? (y/N) " -n 1 -r; echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd backend && poetry run pytest -m real_integration; \
	else \
		echo "Cancelled."; \
	fi

# Linting and Formatting
lint:
	@echo "Running linters..."
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry run ruff check .; \
	fi
	@if [ -f "frontend/package.json" ]; then \
		if ! command -v pnpm >/dev/null 2>&1; then \
			echo "pnpm not found, installing..."; \
			curl -fsSL https://get.pnpm.io/install.sh | sh -; \
		fi; \
		cd frontend && PATH="$$HOME/.local/share/pnpm:$$PATH" pnpm run lint; \
	fi

format:
	@echo "Formatting code..."
	@if [ -f "backend/pyproject.toml" ]; then \
		cd backend && poetry run black . && poetry run ruff format .; \
	fi
	@if [ -f "frontend/package.json" ]; then \
		if ! command -v pnpm >/dev/null 2>&1; then \
			echo "pnpm not found, installing..."; \
			curl -fsSL https://get.pnpm.io/install.sh | sh -; \
		fi; \
		cd frontend && PATH="$$HOME/.local/share/pnpm:$$PATH" pnpm run format; \
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
build: build-web build-api
	@echo "Production build completed"

build-web: check-docker
	@echo "Building frontend production image..."
	@if [ -f "frontend/Dockerfile" ]; then \
		docker build \
			-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:$(VERSION)" \
			-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:latest" \
			-f frontend/Dockerfile .; \
	else \
		echo "Error: frontend/Dockerfile not found"; \
		exit 1; \
	fi

build-api: check-docker
	@echo "Building backend production image..."
	@if [ -f "backend/Dockerfile" ]; then \
		docker build \
			-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-backend:$(VERSION)" \
			-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-backend:latest" \
			-f backend/Dockerfile .; \
	else \
		echo "Error: backend/Dockerfile not found"; \
		exit 1; \
	fi

build-monitor: check-docker
	@echo "Building monitor system image..."
	@if [ -f "backend/monitor/Dockerfile" ]; then \
		docker build \
			--platform linux/amd64 \
			-t "$(MONITOR_IMAGE):$(VERSION)" \
			-t "$(MONITOR_IMAGE):latest" \
			-f backend/monitor/Dockerfile backend/; \
	else \
		echo "Error: backend/monitor/Dockerfile not found"; \
		exit 1; \
	fi

# Simplified deployment variables
CLOUD_RUN_SERVICE_NAME ?= $(DOCKER_IMAGE_PREFIX)-frontend
CLOUD_RUN_REGION ?= $(GOOGLE_CLOUD_LOCATION)
CLOUD_RUN_BACKEND_SERVICE_NAME ?= $(DOCKER_IMAGE_PREFIX)-backend

# Deployment
deploy: deploy-api deploy-web deploy-monitor
	@echo "Deployment completed"

deploy-api: check-docker check-gcloud
	@echo "Deploying FastAPI backend to Cloud Run..."
	@if [ -z "$(GOOGLE_CLIENT_ID)" ]; then \
		echo "Error: GOOGLE_CLIENT_ID not found in .env file"; \
		exit 1; \
	fi
	@if [ -z "$(RAG_CORPUS)" ]; then \
		echo "Warning: RAG_CORPUS not found in .env file (chat functionality may not work)"; \
	fi
	@echo "✅ Using GOOGLE_CLIENT_ID: $(shell echo "$(GOOGLE_CLIENT_ID)" | head -c 20)..."
	@echo "✅ Using RAG_CORPUS: $(RAG_CORPUS)"
	@docker build \
		--platform linux/amd64 \
		-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-backend:$(VERSION)" \
		-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-backend:latest" \
		-f backend/Dockerfile . 
	@docker push "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-backend:$(VERSION)"
	@docker push "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-backend:latest"
	@echo "Creating YAML env vars file..."
	@echo "ENV: production" > /tmp/deploy-env-vars.yaml
	@echo "GOOGLE_CLIENT_ID: \"$(GOOGLE_CLIENT_ID)\"" >> /tmp/deploy-env-vars.yaml
	@echo "RAG_CORPUS: \"$(RAG_CORPUS)\"" >> /tmp/deploy-env-vars.yaml
	@echo "GOOGLE_CLOUD_PROJECT: \"$(GOOGLE_CLOUD_PROJECT)\"" >> /tmp/deploy-env-vars.yaml
	@echo "GOOGLE_CLOUD_LOCATION: \"$(GOOGLE_CLOUD_LOCATION)\"" >> /tmp/deploy-env-vars.yaml
	@if [ -n "$(ADMIN_EMAILS)" ]; then \
		echo "ADMIN_EMAILS: \"$(ADMIN_EMAILS)\"" >> /tmp/deploy-env-vars.yaml; \
	fi
	@if [ -n "$(JUDGE_EMAILS)" ]; then \
		echo "JUDGE_EMAILS: \"$(JUDGE_EMAILS)\"" >> /tmp/deploy-env-vars.yaml; \
	fi
	@if [ -n "$(GOOGLE_DRIVE_FOLDER_ID)" ]; then \
		echo "GOOGLE_DRIVE_FOLDER_ID: \"$(GOOGLE_DRIVE_FOLDER_ID)\"" >> /tmp/deploy-env-vars.yaml; \
	fi
	@if [ -n "$(STATUS_TRACKER_TEMPLATE_ID)" ]; then \
		echo "STATUS_TRACKER_TEMPLATE_ID: \"$(STATUS_TRACKER_TEMPLATE_ID)\"" >> /tmp/deploy-env-vars.yaml; \
	fi
	@if [ -n "$(GOOGLE_SLIDES_SERVICE_ACCOUNT_KEY_BASE64)" ]; then \
		echo "GOOGLE_SLIDES_SERVICE_ACCOUNT_KEY_BASE64: \"$(GOOGLE_SLIDES_SERVICE_ACCOUNT_KEY_BASE64)\"" >> /tmp/deploy-env-vars.yaml; \
	fi
	@if [ -n "$(GOOGLE_CUSTOM_SEARCH_API_KEY)" ]; then \
		echo "GOOGLE_CUSTOM_SEARCH_API_KEY: \"$(GOOGLE_CUSTOM_SEARCH_API_KEY)\"" >> /tmp/deploy-env-vars.yaml; \
	fi
	@if [ -n "$(GOOGLE_CUSTOM_SEARCH_ENGINE_ID)" ]; then \
		echo "GOOGLE_CUSTOM_SEARCH_ENGINE_ID: \"$(GOOGLE_CUSTOM_SEARCH_ENGINE_ID)\"" >> /tmp/deploy-env-vars.yaml; \
	fi
	@if [ -n "$(GOOGLE_MAPS_API_KEY)" ]; then \
		echo "GOOGLE_MAPS_API_KEY: \"$(GOOGLE_MAPS_API_KEY)\"" >> /tmp/deploy-env-vars.yaml; \
	fi
	@if [ -n "$(NYC_311_APP_TOKEN)" ]; then \
		echo "NYC_311_APP_TOKEN: \"$(NYC_311_APP_TOKEN)\"" >> /tmp/deploy-env-vars.yaml; \
	fi
	@echo "📋 Environment variables being set:"
	@cat /tmp/deploy-env-vars.yaml
	@echo "Deploying to Cloud Run..."
	@gcloud run deploy $(CLOUD_RUN_BACKEND_SERVICE_NAME) \
		--image "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-backend:$(VERSION)" \
		--platform managed \
		--region $(CLOUD_RUN_REGION) \
		--allow-unauthenticated \
		--port 8000 \
		--memory=1Gi \
		--cpu=2 \
		--min-instances=1 \
		--max-instances=50 \
		--concurrency=100 \
		--timeout=900 \
		--env-vars-file /tmp/deploy-env-vars.yaml
	@rm -f /tmp/deploy-env-vars.yaml
	@echo "Backend API deployed. Service URL:"
	@gcloud run services describe $(CLOUD_RUN_BACKEND_SERVICE_NAME) \
		--platform managed \
		--region $(CLOUD_RUN_REGION) \
		--format='value(status.url)'

deploy-web: check-docker check-gcloud
	@echo "Building and deploying frontend..."
	@if [ -z "$(DOCKER_REGISTRY)" ] || [ "$(DOCKER_REGISTRY)" = "localhost" ]; then \
		echo "Error: DOCKER_REGISTRY must be set for frontend deployment"; \
		exit 1; \
	fi
	@echo "Building frontend image..."
	@docker build \
		--platform linux/amd64 \
		-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:$(VERSION)" \
		-t "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:latest" \
		-f frontend/Dockerfile .
	@echo "Pushing image to registry..."
	@docker push "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:$(VERSION)"
	@docker push "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:latest"
	@echo "Deploying to Cloud Run..."
	@gcloud run deploy $(CLOUD_RUN_SERVICE_NAME) \
		--image "$(DOCKER_REGISTRY)/$(DOCKER_IMAGE_PREFIX)-frontend:$(VERSION)" \
		--platform managed \
		--region $(CLOUD_RUN_REGION) \
		--allow-unauthenticated \
		--port 8080
	@echo "Deployment completed. Service URL:"
	@gcloud run services describe $(CLOUD_RUN_SERVICE_NAME) \
		--platform managed \
		--region $(CLOUD_RUN_REGION) \
		--format='value(status.url)'

# NYC Monitor System Deployment
setup-monitor: check-gcloud
	@echo "🚀 Setting up NYC Monitor System infrastructure..."
	@echo "Project: $(GOOGLE_CLOUD_PROJECT)"
	@echo "Region: $(GOOGLE_CLOUD_LOCATION)"
	@echo ""
	@echo "🔧 Enabling required Google Cloud APIs..."
	@gcloud services enable firestore.googleapis.com --quiet
	@gcloud services enable aiplatform.googleapis.com --quiet
	@gcloud services enable run.googleapis.com --quiet
	@gcloud services enable cloudbuild.googleapis.com --quiet
	@gcloud services enable cloudscheduler.googleapis.com --quiet
	@echo ""
	@echo "👤 Creating service account..."
	@if ! gcloud iam service-accounts describe $(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com >/dev/null 2>&1; then \
		gcloud iam service-accounts create $(MONITOR_SERVICE_ACCOUNT) \
			--description="Service account for Atlas monitor system" \
			--display-name="Atlas Monitor Service" --quiet; \
	else \
		echo "Service account already exists, skipping creation."; \
	fi
	@echo ""
	@echo "🔐 Granting minimal permissions to service account..."
	@gcloud projects add-iam-policy-binding $(GOOGLE_CLOUD_PROJECT) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/datastore.user" --quiet >/dev/null 2>&1 || true
	@gcloud projects add-iam-policy-binding $(GOOGLE_CLOUD_PROJECT) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/aiplatform.user" --quiet >/dev/null 2>&1 || true
	@gcloud projects add-iam-policy-binding $(GOOGLE_CLOUD_PROJECT) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/logging.logWriter" --quiet >/dev/null 2>&1 || true
	@gcloud projects add-iam-policy-binding $(GOOGLE_CLOUD_PROJECT) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/monitoring.metricWriter" --quiet >/dev/null 2>&1 || true
	@gcloud projects add-iam-policy-binding $(GOOGLE_CLOUD_PROJECT) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/iam.serviceAccountTokenCreator" --quiet >/dev/null 2>&1 || true
	@echo ""
	@echo "✅ Monitor system infrastructure setup complete!"
	@echo "(Assuming Firestore database already exists)"

deploy-monitor: build-monitor check-gcloud
	@echo "☁️ Deploying NYC Monitor System..."
	@echo ""
	@echo "🐳 Pushing Docker image..."
	@docker push "$(MONITOR_IMAGE):$(VERSION)"
	@docker push "$(MONITOR_IMAGE):latest"
	@echo ""
	@echo "📦 Deploying Cloud Run Job..."
	@if gcloud run jobs describe $(MONITOR_JOB_NAME) --region=$(GOOGLE_CLOUD_LOCATION) >/dev/null 2>&1; then \
		echo "Updating existing Cloud Run Job..."; \
		gcloud run jobs update $(MONITOR_JOB_NAME) \
			--image="$(MONITOR_IMAGE):$(VERSION)" \
			--region=$(GOOGLE_CLOUD_LOCATION) \
			--service-account="$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
			--set-env-vars="GOOGLE_CLOUD_PROJECT=$(GOOGLE_CLOUD_PROJECT)" \
			--set-env-vars="VERTEX_AI_LOCATION=$(GOOGLE_CLOUD_LOCATION)" \
			--set-env-vars="REDDIT_CLIENT_ID=$(REDDIT_CLIENT_ID)" \
			--set-env-vars="REDDIT_CLIENT_SECRET=$(REDDIT_CLIENT_SECRET)" \
			--set-env-vars="REDDIT_REFRESH_TOKEN=$(REDDIT_REFRESH_TOKEN)" \
			--set-env-vars="TWITTER_API_KEY=$(TWITTER_API_KEY)" \
			--set-env-vars="TWITTER_API_KEY_SECRET=$(TWITTER_API_KEY_SECRET)" \
			--set-env-vars="TWITTER_BEARER_TOKEN=$(TWITTER_BEARER_TOKEN)" \
			--quiet; \
	else \
		echo "Creating new Cloud Run Job..."; \
		gcloud run jobs create $(MONITOR_JOB_NAME) \
			--image="$(MONITOR_IMAGE):$(VERSION)" \
			--service-account="$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
			--region=$(GOOGLE_CLOUD_LOCATION) \
			--memory=1Gi \
			--cpu=1 \
			--task-timeout=900 \
			--parallelism=1 \
			--set-env-vars="GOOGLE_CLOUD_PROJECT=$(GOOGLE_CLOUD_PROJECT)" \
			--set-env-vars="VERTEX_AI_LOCATION=$(GOOGLE_CLOUD_LOCATION)" \
			--set-env-vars="REDDIT_CLIENT_ID=$(REDDIT_CLIENT_ID)" \
			--set-env-vars="REDDIT_CLIENT_SECRET=$(REDDIT_CLIENT_SECRET)" \
			--set-env-vars="REDDIT_REFRESH_TOKEN=$(REDDIT_REFRESH_TOKEN)" \
			--set-env-vars="TWITTER_API_KEY=$(TWITTER_API_KEY)" \
			--set-env-vars="TWITTER_API_KEY_SECRET=$(TWITTER_API_KEY_SECRET)" \
			--set-env-vars="TWITTER_BEARER_TOKEN=$(TWITTER_BEARER_TOKEN)" \
			--max-retries=3 --quiet; \
	fi
	@echo ""
	@echo "⚠️ Ensuring Cloud Scheduler service account can invoke job..."
	@gcloud run jobs add-iam-policy-binding $(MONITOR_JOB_NAME) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/run.invoker" \
		--region=$(GOOGLE_CLOUD_LOCATION) \
		--quiet || true
	@echo "⚠️ Ensuring Cloud Scheduler service account can create OIDC tokens..."
	@gcloud projects add-iam-policy-binding $(GOOGLE_CLOUD_PROJECT) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/iam.serviceAccountTokenCreator" \
		--quiet || true
	@echo ""
	@echo "⏰ Setting up Cloud Scheduler..."
	@if gcloud scheduler jobs describe $(MONITOR_SCHEDULER_NAME) --location=$(GOOGLE_CLOUD_LOCATION) >/dev/null 2>&1; then \
		echo "Updating existing scheduler job..."; \
		gcloud scheduler jobs update http $(MONITOR_SCHEDULER_NAME) \
			--schedule="0 */12 * * *" \
			--uri="$(CLOUD_RUN_JOB_EXEC_URL)" \
			--http-method=POST \
			--location=$(GOOGLE_CLOUD_LOCATION) \
			--oauth-service-account-email="$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
			--quiet; \
	else \
		echo "Creating new scheduler job..."; \
		gcloud scheduler jobs create http $(MONITOR_SCHEDULER_NAME) \
			--schedule="0 */12 * * *" \
			--uri="$(CLOUD_RUN_JOB_EXEC_URL)" \
			--http-method=POST \
			--location=$(GOOGLE_CLOUD_LOCATION) \
			--oauth-service-account-email="$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
			--quiet; \
	fi
	@echo ""
	@echo "✅ Monitor system deployment complete!"
	@echo ""
	@echo "📊 Monitor System Status:"
	@echo "- Cloud Run Job: https://console.cloud.google.com/run/jobs/details/$(GOOGLE_CLOUD_LOCATION)/$(MONITOR_JOB_NAME)"
	@echo "- Cloud Scheduler: https://console.cloud.google.com/cloudscheduler/jobs/$(GOOGLE_CLOUD_LOCATION)/$(MONITOR_SCHEDULER_NAME)"
	@echo "- Firestore: https://console.cloud.google.com/firestore/data"
	@echo ""
	@echo "🔧 To test the job manually:"
	@echo "make test-monitor"
	@echo ""
	@echo "⚠️  Remember to set up Reddit API credentials as secrets or environment variables!"
	@echo "   - REDDIT_CLIENT_ID"
	@echo "   - REDDIT_CLIENT_SECRET"
	@echo "   - REDDIT_REFRESH_TOKEN"

test-monitor: check-gcloud
	@echo "🧪 Testing monitor system..."
	@echo "Checking if job exists..."
	@gcloud run jobs describe $(MONITOR_JOB_NAME) --region=$(GOOGLE_CLOUD_LOCATION) --format="value(metadata.name)" || (echo "❌ Job not found!" && exit 1)
	@echo "Executing job..."
	@gcloud run jobs execute $(MONITOR_JOB_NAME) --region=$(GOOGLE_CLOUD_LOCATION) --wait
	@echo "📝 Recent logs:"
	@gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="$(MONITOR_JOB_NAME)"' \
		--limit=10 \
		--format='table(timestamp,textPayload)' \
		--freshness=5m

logs-monitor: check-gcloud
	@echo "📝 Viewing monitor system logs..."
	@gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="$(MONITOR_JOB_NAME)"' \
		--limit=50 \
		--format='table(timestamp,textPayload)' \
		--freshness=1d

verify-monitor: check-gcloud
	@echo "🔍 Verifying monitor system..."
	cd backend && poetry run python ../scripts/verify_monitor_system.py

# Debug scheduler and job execution
debug-scheduler: check-gcloud
	@echo "🔍 DEBUGGING SCHEDULER EXECUTION HISTORY..."
	@echo "Scheduler job: $(MONITOR_SCHEDULER_NAME)"
	@echo "Region: $(GOOGLE_CLOUD_LOCATION)"
	@echo ""
	@echo "📅 Recent scheduler executions (last 7 days):"
	@gcloud logging read 'resource.type="cloud_scheduler_job" AND resource.labels.job_id="$(MONITOR_SCHEDULER_NAME)"' \
		--limit=20 \
		--format='table(timestamp,severity,jsonPayload.message)' \
		--freshness=7d || echo "No scheduler logs found"
	@echo ""
	@echo "📊 Scheduler job details:"
	@gcloud scheduler jobs describe $(MONITOR_SCHEDULER_NAME) --location=$(GOOGLE_CLOUD_LOCATION) || echo "Scheduler job not found"

debug-job-executions: check-gcloud
	@echo "🔍 DEBUGGING CLOUD RUN JOB EXECUTIONS..."
	@echo "Job name: $(MONITOR_JOB_NAME)"
	@echo "Region: $(GOOGLE_CLOUD_LOCATION)"
	@echo ""
	@echo "📋 Recent job executions (last 7 days):"
	@gcloud run jobs executions list \
		--job=$(MONITOR_JOB_NAME) \
		--region=$(GOOGLE_CLOUD_LOCATION) \
		--limit=10 \
		--format='table(metadata.name,status.completionTime,status.conditions[0].type,status.conditions[0].status,status.conditions[0].reason)' || echo "No executions found"
	@echo ""
	@echo "🏃 Job configuration:"
	@gcloud run jobs describe $(MONITOR_JOB_NAME) --region=$(GOOGLE_CLOUD_LOCATION) \
		--format='table(metadata.name,spec.template.spec.template.spec.containers[0].image,spec.template.spec.template.spec.serviceAccountName)'

debug-job-logs: check-gcloud
	@echo "🔍 DEBUGGING CLOUD RUN JOB LOGS..."
	@echo "Recent job logs (last 24 hours):"
	@echo ""
	@gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="$(MONITOR_JOB_NAME)"' \
		--limit=100 \
		--format='table(timestamp,severity,textPayload)' \
		--freshness=1d

debug-monitor-full: debug-scheduler debug-job-executions debug-job-logs
	@echo ""
	@echo "🎯 SUMMARY:"
	@echo "1. Check scheduler logs above - should show HTTP POST requests every 3 hours"
	@echo "2. Check job executions - should show successful completions"
	@echo "3. Check job logs - should show monitor cycle completion messages"
	@echo ""
	@echo "💡 TROUBLESHOOTING TIPS:"
	@echo "- If no scheduler logs: Check if scheduler job exists and is enabled"
	@echo "- If scheduler logs show errors: Check IAM permissions"
	@echo "- If no job executions: Check if scheduler is triggering the job"
	@echo "- If job executions fail: Check job logs for errors"

# Cleanup tasks to remove excessive permissions
cleanup-monitor-permissions: check-gcloud
	@echo "🧹 Cleaning up excessive monitor permissions..."
	@echo "Removing unnecessary roles from service account..."
	@gcloud projects remove-iam-policy-binding $(GOOGLE_CLOUD_PROJECT) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/run.invoker" --quiet >/dev/null 2>&1 || true
	@gcloud projects remove-iam-policy-binding $(GOOGLE_CLOUD_PROJECT) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/run.developer" --quiet >/dev/null 2>&1 || true
	@gcloud projects remove-iam-policy-binding $(GOOGLE_CLOUD_PROJECT) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/run.admin" --quiet >/dev/null 2>&1 || true
	@echo "✅ Cleanup complete!"

# Help
help:
	@echo "Development Commands:"
	@echo "  make install           - Install all dependencies"
	@echo "  make install-api   - Install backend dependencies"
	@echo "  make install-web  - Install frontend dependencies"
	@echo "  make dev              - Start development environment (both services)"
	@echo "  make dev-api      - Start backend development server"
	@echo "  make dev-web     - Start frontend development server"
	@echo "  make dev-web-deployed - Start frontend using deployed backend"
	@echo "  make test             - Run all tests (excludes real integration tests)"
	@echo "  make test-api         - Run backend tests (excludes real integration tests)"
	@echo "  make test-web         - Run frontend tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run mocked integration tests"
	@echo "  make test-integration-real - Run REAL integration tests (requires credentials)"
	@echo "  make test-deployed-api    - Test deployed backend health"
	@echo "  make get-api-url  - Get deployed backend URL"
	@echo "  make lint             - Run linters"
	@echo "  make format           - Format code"
	@echo "Devcontainer Commands:"
	@echo "  make devcontainer-setup  - Set up devcontainer environment"
	@echo "  make devcontainer-clean  - Clean devcontainer environment"
	@echo ""
	@echo "Production Commands:"
	@echo "  make build            - Build all production images"
	@echo "  make build-web   - Build frontend production image"
	@echo "  make build-api    - Build backend production image"
	@echo "  make build-monitor - Build monitor system image"
	@echo "  make deploy           - Deploy all services (backend, frontend, monitor)"
	@echo "  make deploy-api   - Deploy fastapi backend"
	@echo "  make deploy-web  - Deploy frontend container"
	@echo "  make deploy-web-secure - Deploy frontend with Cloud Armor protection"
	@echo ""
	@echo "Security Commands (Cloud Armor):"
	@echo "  make setup-cloud-armor    - Set up Cloud Armor protection for frontend"
	@echo "  make check-cloud-armor    - Check Cloud Armor policy status"
	@echo "  make logs-cloud-armor     - View Cloud Armor security logs"
	@echo "  make test-cloud-armor     - Test Cloud Armor protection"
	@echo "  make get-secure-frontend-url - Get Cloud Armor protected frontend URL"
	@echo "  make remove-cloud-armor   - Remove Cloud Armor setup (cleanup)"
	@echo ""
	@echo "NYC Monitor System Commands:"
	@echo "  make setup-monitor    - Set up monitor system infrastructure (ONE TIME ONLY)"
	@echo "  make deploy-monitor   - Deploy monitor system code updates"
	@echo "  make test-monitor     - Run monitor job manually"
	@echo "  make logs-monitor     - View monitor system logs"
	@echo "  make verify-monitor   - Verify monitor system"
	@echo "  make debug-scheduler  - Check scheduler execution history"
	@echo "  make debug-job-executions - Check job executions"
	@echo "  make debug-job-logs   - Check job logs"
	@echo "  make debug-monitor-full - Run all debug checks"
	@echo ""
	@echo "Testing Against Deployed Services:"
	@echo "  make dev-web-deployed - Test frontend locally against deployed backend"
	@echo "  make test-deployed-api    - Check if deployed backend is healthy"
	@echo "  make get-api-url  - Get the deployed backend URL"
	@echo ""
	@echo "Troubleshooting:"
	@echo "  If monitor not running automatically, use 'make debug-monitor-full'"
	@echo "  to check scheduler logs, job executions, and job logs"

# Domain management
CUSTOM_DOMAIN ?= $(shell grep -E '^CUSTOM_DOMAIN=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' ')

# Cloud Armor security policy variables
CLOUD_ARMOR_POLICY_NAME ?= atlas-frontend-security-policy
CLOUD_ARMOR_LB_BACKEND_SERVICE ?= atlas-frontend-lb-backend-service
CLOUD_ARMOR_URL_MAP ?= atlas-frontend-url-map
CLOUD_ARMOR_STATIC_IP ?= atlas-frontend-ip


check-domain: check-gcloud
	@if [ -z "$(CUSTOM_DOMAIN)" ]; then \
		echo "Error: CUSTOM_DOMAIN not set in .env file"; \
		exit 1; \
	fi
	@echo "🔍 Checking domain mapping status for $(CUSTOM_DOMAIN)..."
	@gcloud alpha run domain-mappings describe --domain="$(CUSTOM_DOMAIN)" \
		--region=$(CLOUD_RUN_REGION) \
		--format="yaml" || echo "Domain mapping not found"

remove-domain: check-gcloud
	@if [ -z "$(CUSTOM_DOMAIN)" ]; then \
		echo "Error: CUSTOM_DOMAIN not set in .env file"; \
		exit 1; \
	fi
	@echo "🗑️ Removing domain mapping for $(CUSTOM_DOMAIN)..."
	@gcloud alpha run domain-mappings delete --domain="$(CUSTOM_DOMAIN)" \
		--region=$(CLOUD_RUN_REGION) \
		--quiet

list-domains: check-gcloud
	@echo "📋 Listing all domain mappings..."
	@gcloud alpha run domain-mappings list \
		--region=$(CLOUD_RUN_REGION)

setup-domain-direct: check-gcloud
	@if [ -z "$(CUSTOM_DOMAIN)" ]; then \
		echo "Error: CUSTOM_DOMAIN not set in .env file"; \
		echo "Add CUSTOM_DOMAIN=your-domain.com to your .env file"; \
		exit 1; \
	fi
	@chmod +x scripts/setup-custom-domain-direct.sh
	@./scripts/setup-custom-domain-direct.sh "$(CUSTOM_DOMAIN)"

# Build NYC 311 image
build-nyc311: check-docker check-gcloud
	@echo "🐳 Building NYC 311 Daily Collector image..."
	@echo "Image tag: $(NYC311_IMAGE):$(VERSION)"
	@echo ""
	@docker build \
		--platform linux/amd64 \
		-f backend/monitor/Dockerfile.nyc311 \
		-t "$(NYC311_IMAGE):$(VERSION)" \
		-t "$(NYC311_IMAGE):latest" \
		backend/
	@echo "✅ NYC 311 image built successfully"

# Deploy NYC 311 Daily Collection Job
deploy-nyc311: build-nyc311 check-gcloud
	@echo "☁️ Deploying NYC 311 Daily Collection Job..."
	@echo ""
	@echo "🐳 Pushing Docker image..."
	@docker push "$(NYC311_IMAGE):$(VERSION)"
	@docker push "$(NYC311_IMAGE):latest"
	@echo ""
	@echo "📦 Deploying Cloud Run Job..."
	@if gcloud run jobs describe $(NYC311_JOB_NAME) --region=$(GOOGLE_CLOUD_LOCATION) >/dev/null 2>&1; then \
		echo "Updating existing NYC 311 Cloud Run Job..."; \
		gcloud run jobs update $(NYC311_JOB_NAME) \
			--image="$(NYC311_IMAGE):$(VERSION)" \
			--region=$(GOOGLE_CLOUD_LOCATION) \
			--service-account="$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
			--set-env-vars="GOOGLE_CLOUD_PROJECT=$(GOOGLE_CLOUD_PROJECT)" \
			--set-env-vars="NYC_311_APP_TOKEN=$(NYC_311_APP_TOKEN)" \
			--quiet; \
	else \
		echo "Creating new NYC 311 Cloud Run Job..."; \
		gcloud run jobs create $(NYC311_JOB_NAME) \
			--image="$(NYC311_IMAGE):$(VERSION)" \
			--service-account="$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
			--region=$(GOOGLE_CLOUD_LOCATION) \
			--memory=1Gi \
			--cpu=1 \
			--task-timeout=1800 \
			--parallelism=1 \
			--set-env-vars="GOOGLE_CLOUD_PROJECT=$(GOOGLE_CLOUD_PROJECT)" \
			--set-env-vars="NYC_311_APP_TOKEN=$(NYC_311_APP_TOKEN)" \
			--max-retries=2 --quiet; \
	fi
	@echo ""
	@echo "⚠️ Ensuring Cloud Scheduler service account can invoke NYC 311 job..."
	@gcloud run jobs add-iam-policy-binding $(NYC311_JOB_NAME) \
		--member="serviceAccount:$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
		--role="roles/run.invoker" \
		--region=$(GOOGLE_CLOUD_LOCATION) \
		--quiet || true
	@echo ""
	@echo "⏰ Setting up daily Cloud Scheduler..."
	@if gcloud scheduler jobs describe $(NYC311_SCHEDULER_NAME) --location=$(GOOGLE_CLOUD_LOCATION) >/dev/null 2>&1; then \
		echo "Updating existing NYC 311 scheduler job..."; \
		gcloud scheduler jobs update http $(NYC311_SCHEDULER_NAME) \
			--schedule="0 6 * * *" \
			--time-zone="America/New_York" \
			--uri="$(NYC311_JOB_EXEC_URL)" \
			--http-method=POST \
			--location=$(GOOGLE_CLOUD_LOCATION) \
			--oauth-service-account-email="$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
			--quiet; \
	else \
		echo "Creating new NYC 311 scheduler job..."; \
		gcloud scheduler jobs create http $(NYC311_SCHEDULER_NAME) \
			--schedule="0 6 * * *" \
			--time-zone="America/New_York" \
			--uri="$(NYC311_JOB_EXEC_URL)" \
			--http-method=POST \
			--location=$(GOOGLE_CLOUD_LOCATION) \
			--oauth-service-account-email="$(MONITOR_SERVICE_ACCOUNT)@$(GOOGLE_CLOUD_PROJECT).iam.gserviceaccount.com" \
			--quiet; \
	fi
	@echo ""
	@echo "✅ NYC 311 daily collection system deployment complete!"
	@echo ""
	@echo "📊 NYC 311 System Status:"
	@echo "- Cloud Run Job: https://console.cloud.google.com/run/jobs/details/$(GOOGLE_CLOUD_LOCATION)/$(NYC311_JOB_NAME)"
	@echo "- Cloud Scheduler: https://console.cloud.google.com/cloudscheduler/jobs/$(GOOGLE_CLOUD_LOCATION)/$(NYC311_SCHEDULER_NAME)"
	@echo "- Firestore Collection: https://console.cloud.google.com/firestore/data/nyc_311_signals"
	@echo ""
	@echo "🔧 To test the NYC 311 job manually:"
	@echo "make test-nyc311"
	@echo ""
	@echo "📅 Scheduled to run daily at 6 AM EST"

test-nyc311: check-gcloud
	@echo "🧪 Testing NYC 311 daily collection job..."
	@echo "Checking if job exists..."
	@gcloud run jobs describe $(NYC311_JOB_NAME) --region=$(GOOGLE_CLOUD_LOCATION) --format="value(metadata.name)" || (echo "❌ NYC 311 job not found!" && exit 1)
	@echo "Executing NYC 311 job..."
	@gcloud run jobs execute $(NYC311_JOB_NAME) --region=$(GOOGLE_CLOUD_LOCATION) --wait
	@echo "📝 Recent NYC 311 job logs:"
	@gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="$(NYC311_JOB_NAME)"' \
		--limit=10 \
		--format='table(timestamp,textPayload)' \
		--freshness=5m

logs-nyc311: check-gcloud
	@echo "📝 Viewing NYC 311 system logs..."
	@gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="$(NYC311_JOB_NAME)"' \
		--limit=50 \
		--format='table(timestamp,textPayload)' \
		--freshness=1d

# Test NYC 311 job locally
test-nyc311-local:
	@echo "🧪 Testing NYC 311 job locally..."
	cd backend && poetry run python test_nyc311_job.py

# Cloud Armor Security Setup
setup-cloud-armor: check-gcloud
	@echo "🛡️  Setting up Cloud Armor protection for frontend..."
	@if [ ! -f "scripts/setup-cloud-armor.sh" ]; then \
		echo "Error: scripts/setup-cloud-armor.sh not found"; \
		exit 1; \
	fi
	@chmod +x scripts/setup-cloud-armor.sh
	@./scripts/setup-cloud-armor.sh

# Deploy frontend with Cloud Armor protection
deploy-web-secure: deploy-web setup-cloud-armor
	@echo "✅ Frontend deployed with Cloud Armor protection!"

# Check Cloud Armor policy status
check-cloud-armor: check-gcloud
	@echo "🔍 Checking Cloud Armor policy status..."
	@if gcloud compute security-policies describe $(CLOUD_ARMOR_POLICY_NAME) >/dev/null 2>&1; then \
		echo "📋 Cloud Armor Policy: $(CLOUD_ARMOR_POLICY_NAME)"; \
		gcloud compute security-policies describe $(CLOUD_ARMOR_POLICY_NAME) \
			--format="table(name,description,rules.len():label=RULES)"; \
		echo ""; \
		echo "🔧 Security Rules:"; \
		gcloud compute security-policies rules list $(CLOUD_ARMOR_POLICY_NAME) \
			--format="table(priority,action,description)"; \
	else \
		echo "❌ Cloud Armor policy '$(CLOUD_ARMOR_POLICY_NAME)' not found"; \
		echo "Run 'make setup-cloud-armor' to create it"; \
	fi

# View Cloud Armor logs
logs-cloud-armor: check-gcloud
	@echo "📝 Viewing Cloud Armor security logs (last 24 hours)..."
	@gcloud logging read 'resource.type="gce_backend_service" AND (jsonPayload.securityPolicyRequestData.action="deny" OR jsonPayload.securityPolicyRequestData.action="rate_limit")' \
		--limit=50 \
		--format='table(timestamp,httpRequest.remoteIp,httpRequest.userAgent,jsonPayload.securityPolicyRequestData.action,jsonPayload.securityPolicyRequestData.ruleName)' \
		--freshness=1d || echo "No security events found in logs"

# Test Cloud Armor protection
test-cloud-armor: check-gcloud
	@echo "🧪 Testing Cloud Armor protection..."
	@if [ -z "$(CLOUD_ARMOR_STATIC_IP)" ]; then \
		echo "Error: Could not determine static IP. Check if Cloud Armor is set up."; \
		exit 1; \
	fi
	@STATIC_IP=$$(gcloud compute addresses describe $(CLOUD_ARMOR_STATIC_IP) --global --format='value(address)' 2>/dev/null || echo ""); \
	if [ -z "$$STATIC_IP" ]; then \
		echo "❌ Static IP not found. Run 'make setup-cloud-armor' first."; \
		exit 1; \
	fi; \
	echo "🌐 Testing HTTP access to $$STATIC_IP..."; \
	if curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "http://$$STATIC_IP"; then \
		echo "✅ HTTP access successful"; \
	else \
		echo "❌ HTTP access failed"; \
	fi; \
	echo ""; \
	echo "🚀 Testing rate limiting (this may take a moment)..."; \
	echo "Sending rapid requests to trigger rate limiting..."; \
	for i in {1..15}; do \
		curl -s -o /dev/null -w "Request $$i: %{http_code}\n" "http://$$STATIC_IP" & \
	done; \
	wait; \
	echo ""; \
	echo "📊 Check 'make logs-cloud-armor' to see if rate limiting was triggered"

# Remove Cloud Armor setup (cleanup)
remove-cloud-armor: check-gcloud
	@echo "🗑️  Removing Cloud Armor setup..."
	@echo "⚠️  This will remove ALL Cloud Armor protection!"
	@read -p "Are you sure? (y/N) " -n 1 -r; echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Removing forwarding rules..."; \
		gcloud compute forwarding-rules delete atlas-frontend-forwarding-rule-http --global --quiet || true; \
		gcloud compute forwarding-rules delete atlas-frontend-forwarding-rule-https --global --quiet || true; \
		echo "Removing HTTP(S) proxies..."; \
		gcloud compute target-http-proxies delete atlas-frontend-http-proxy --global --quiet || true; \
		gcloud compute target-https-proxies delete atlas-frontend-https-proxy --global --quiet || true; \
		echo "Removing URL map..."; \
		gcloud compute url-maps delete $(CLOUD_ARMOR_URL_MAP) --global --quiet || true; \
		echo "Removing backend service..."; \
		gcloud compute backend-services delete $(CLOUD_ARMOR_LB_BACKEND_SERVICE) --global --quiet || true; \
		echo "Removing network endpoint group..."; \
		gcloud compute network-endpoint-groups delete atlas-frontend-neg --region=$(GOOGLE_CLOUD_LOCATION) --quiet || true; \
		echo "Removing security policy..."; \
		gcloud compute security-policies delete $(CLOUD_ARMOR_POLICY_NAME) --quiet || true; \
		echo "Static IP '$(CLOUD_ARMOR_STATIC_IP)' preserved (delete manually if needed)"; \
		echo "✅ Cloud Armor setup removed"; \
	else \
		echo "Cancelled."; \
	fi

# Get Cloud Armor protected frontend URL
get-secure-frontend-url: check-gcloud
	@echo "🔗 Cloud Armor protected frontend URLs:"
	@STATIC_IP=$$(gcloud compute addresses describe $(CLOUD_ARMOR_STATIC_IP) --global --format='value(address)' 2>/dev/null || echo ""); \
	if [ -n "$$STATIC_IP" ]; then \
		echo "HTTP:  http://$$STATIC_IP"; \
		echo "HTTPS: https://$$STATIC_IP (if SSL certificate is configured)"; \
	else \
		echo "❌ Static IP not found. Run 'make setup-cloud-armor' first."; \
	fi
