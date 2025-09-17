#!/bin/bash

# Atlas NYC Monitor Development Container Setup Script
set -e  # Exit on any error

echo "🚀 Setting up Atlas NYC Monitor development environment..."

# Ensure we're in the workspace directory
cd /workspaces/atlas-bootstrapped

# Skip Docker setup - not needed for development
echo "ℹ️  Skipping Docker setup - using simplified devcontainer"

# Ensure PATH includes necessary directories
export PATH="/home/vscode/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Install Poetry if not already installed
echo "📦 Installing Poetry..."
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="/home/vscode/.local/bin:$PATH"
    echo "Poetry installed"
else
    echo "Poetry already installed: $(poetry --version)"
fi

# Ensure pnpm is available
echo "📦 Checking pnpm installation..."
if command -v pnpm &> /dev/null; then
    echo "pnpm already installed: $(pnpm --version)"
else
    echo "⚠️  pnpm not found in PATH, trying to install..."
    npm install -g pnpm
    # Add to current session
    export PATH="/usr/local/lib/node_modules/pnpm/bin:$PATH"
fi

# Install backend dependencies
echo "🐍 Installing backend dependencies..."
if [ -d "backend" ] && [ -f "backend/pyproject.toml" ]; then
    cd backend
    poetry install --no-interaction --no-ansi
    cd ..
    echo "Backend dependencies installed"
else
    echo "⚠️  Backend directory or pyproject.toml not found, skipping backend setup"
fi

# Clean and install frontend dependencies using pnpm workspaces
echo "🌐 Installing frontend dependencies..."
if [ -f "pnpm-workspace.yaml" ] && [ -f "frontend/package.json" ]; then
    # Clean node_modules to fix hoist pattern conflicts
    echo "🧹 Cleaning node_modules to fix hoist pattern conflicts..."
    rm -rf node_modules frontend/node_modules
    
    # Install from workspace root to handle workspace dependencies
    pnpm install
    echo "Frontend dependencies installed via workspace"
else
    echo "⚠️  pnpm-workspace.yaml or frontend/package.json not found, trying individual install..."
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        # Clean node_modules first
        rm -rf frontend/node_modules
        cd frontend
        pnpm install
        cd ..
        echo "Frontend dependencies installed individually"
    else
        echo "⚠️  Frontend directory or package.json not found, skipping frontend setup"
    fi
fi

# Set up development environment variables
echo "🔧 Setting up development environment variables..."
if [ ! -f ".env" ]; then
    echo "📝 Creating development .env file..."
    cat > .env << 'EOF'
# Development environment configuration
# For local development - you can override these values

# Google Cloud Project (required for Vertex AI)
# Set this to your actual GCP project ID, or use the default for local dev
GOOGLE_CLOUD_PROJECT=atlas-dev-local

# Google Cloud location
GOOGLE_CLOUD_LOCATION=us-central1

# Docker registry (for local development)
DOCKER_REGISTRY=localhost

# Development flags
ENV=development

# Optional: Add your actual project ID here when ready
# GOOGLE_CLOUD_PROJECT=your-actual-project-id
EOF
    echo "✅ Created .env file with development defaults"
    echo "📋 To use with real Google Cloud:"
    echo "   1. Set GOOGLE_CLOUD_PROJECT in .env to your actual project ID"
    echo "   2. Run: gcloud auth application-default login"
    echo "   3. Run: gcloud config set project YOUR_PROJECT_ID"
else
    echo "✅ .env file already exists"
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🔧 Available commands:"
echo "  make dev          - Start both backend and frontend"
echo "  make dev-api      - Start backend only"
echo "  make dev-web      - Start frontend only"
echo "  make test         - Run all tests"
echo "  make help         - Show all available commands"
echo ""
echo "⚠️  Note: To use Google Cloud services, configure your .env file with real project ID" 