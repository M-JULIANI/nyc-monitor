#!/bin/bash

# Atlas NYC Monitor Development Container Setup Script
set -e  # Exit on any error

echo "🚀 Setting up Atlas NYC Monitor development environment..."

# Ensure we're in the workspace directory
cd /workspaces/atlas-bootstrapped

# Docker permissions setup
echo "🐳 Setting up Docker permissions..."
sudo groupadd -f docker || true
sudo usermod -aG docker vscode || true
sudo chown root:docker /var/run/docker.sock || true
sudo chmod 666 /var/run/docker.sock || true

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

# Install frontend dependencies using pnpm workspaces
echo "🌐 Installing frontend dependencies..."
if [ -f "pnpm-workspace.yaml" ] && [ -f "frontend/package.json" ]; then
    # Install from workspace root to handle workspace dependencies
    pnpm install
    echo "Frontend dependencies installed via workspace"
else
    echo "⚠️  pnpm-workspace.yaml or frontend/package.json not found, trying individual install..."
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        cd frontend
        pnpm install
        cd ..
        echo "Frontend dependencies installed individually"
    else
        echo "⚠️  Frontend directory or package.json not found, skipping frontend setup"
    fi
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🔧 Available commands:"
echo "  make dev          - Start both backend and frontend"
echo "  make dev-api      - Start backend only"
echo "  make dev-web      - Start frontend only"
echo "  make test         - Run all tests"
echo "  make help         - Show all available commands" 