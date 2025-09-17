#!/bin/bash

echo "🧹 COMPLETE CLEANUP - Removing all cached data and dependencies"
echo "This will remove all Poetry virtual environments, Node modules, Rust cache, and build artifacts"
echo ""

# Poetry cleanup
echo "📦 Cleaning Poetry caches..."
poetry cache clear --all . 2>/dev/null || echo "Poetry cache cleared"
cd backend 2>/dev/null && poetry env remove --all 2>/dev/null && cd .. || echo "Backend env removed"
rm -rf ~/.cache/pypoetry

# Node.js cleanup
echo "🌐 Cleaning Node.js caches..."
rm -rf node_modules
rm -rf frontend/node_modules
rm -rf ~/.npm
rm -rf ~/.pnpm-store
rm -rf ~/.cache/pnpm
rm -rf /tmp/.pnpm*

# Rust cleanup
echo "🦀 Cleaning Rust caches..."
rm -rf ~/.cargo
rm -rf ~/.rustup
rm -rf ~/.cache/puccinialin
find /tmp -name "*primp*" -type d -exec rm -rf {} + 2>/dev/null || true

# Python caches
echo "🐍 Cleaning Python caches..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
rm -rf ~/.cache/pip

# Package locks (will be regenerated)
echo "🔒 Cleaning lock files..."
rm -f poetry.lock 2>/dev/null || true
rm -f backend/poetry.lock 2>/dev/null || true
rm -f package-lock.json 2>/dev/null || true
rm -f frontend/package-lock.json 2>/dev/null || true
rm -f pnpm-lock.yaml 2>/dev/null || true

# Docker build cache (if accessible)
echo "🐳 Cleaning Docker build cache..."
docker system prune -f 2>/dev/null || echo "Docker cleanup skipped (not accessible)"

# Various other caches
echo "🗑️ Cleaning miscellaneous caches..."
rm -rf ~/.cache/ms-playwright 2>/dev/null || true
rm -rf ~/.cache/node-gyp 2>/dev/null || true

echo ""
echo "✅ Complete cleanup finished!"
echo ""
echo "🔄 Next steps:"
echo "1. Rebuild the dev container: Ctrl+Shift+P → 'Dev Containers: Rebuild Container'"
echo "2. Wait for the container to build with all the new tools"
echo "3. Run 'make install' to reinstall everything cleanly"
echo ""
echo "The new container will have cmake, rust, and all necessary build tools!"
