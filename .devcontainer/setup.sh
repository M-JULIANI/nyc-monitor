#!/bin/bash

# Atlas NYC Monitor Development Container Setup Script
set -e  # Exit on any error

echo "🚀 Setting up Atlas NYC Monitor development environment..."

# Docker permissions setup
echo "🐳 Setting up Docker permissions..."
sudo groupadd -f docker || true
sudo usermod -aG docker vscode || true
sudo chown root:docker /var/run/docker.sock || true
sudo chmod 666 /var/run/docker.sock || true

# Install Poetry if not already installed
echo "📦 Installing Poetry..."
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
    echo "Poetry installed"
else
    echo "Poetry already installed"
fi

# Check if pnpm is available (should be installed globally in Dockerfile)
echo "📦 Checking pnpm installation..."
if command -v pnpm &> /dev/null; then
    echo "pnpm already installed"
else
    echo "⚠️  pnpm not found, installing..."
    npm install -g pnpm
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

# Install frontend dependencies
echo "🌐 Installing frontend dependencies..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    cd frontend
    pnpm install
    cd ..
    echo "Frontend dependencies installed"
else
    echo "⚠️  Frontend directory or package.json not found, skipping frontend setup"
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🔧 Available commands:"
echo "  make dev          - Start both backend and frontend"
echo "  make dev-api      - Start backend only"
echo "  make dev-web      - Start frontend only"
echo "  make test         - Run all tests"
echo "  make help         - Show all available commands" 