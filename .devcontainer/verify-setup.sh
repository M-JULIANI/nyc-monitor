#!/bin/bash

# Simple verification script to test devcontainer setup
echo "🔍 Verifying devcontainer setup..."

# Check if basic system commands are available
echo "Checking basic system commands..."
basic_commands=("cat" "sleep" "curl" "which")
for cmd in "${basic_commands[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        echo "✅ $cmd: available"
    else
        echo "❌ $cmd: not found"
    fi
done

echo ""
echo "Checking development tools..."

# Check if development commands are available
dev_commands=("node" "npm" "pnpm" "python3" "docker")
for cmd in "${dev_commands[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        version=$($cmd --version 2>/dev/null | head -1 || echo "unknown")
        echo "✅ $cmd: $version"
    else
        echo "❌ $cmd: not found"
    fi
done

# Check Poetry specifically
echo ""
echo "Checking Poetry..."
if command -v poetry &> /dev/null; then
    version=$(poetry --version 2>/dev/null || echo "unknown")
    echo "✅ poetry: $version"
else
    echo "❌ poetry: not found"
fi

# Check Docker permissions
echo ""
echo "Checking Docker permissions..."
if docker ps &> /dev/null; then
    echo "✅ Docker permissions: OK"
else
    echo "⚠️  Docker permissions: may need setup (run setup.sh)"
fi

# Check Poetry configuration
echo ""
echo "Checking Poetry configuration..."
if [ -f "backend/pyproject.toml" ] && command -v poetry &> /dev/null; then
    cd backend
    if poetry check &> /dev/null; then
        echo "✅ Poetry configuration: OK"
    else
        echo "⚠️  Poetry configuration: needs dependencies installed"
    fi
    cd ..
else
    echo "❌ Poetry or backend/pyproject.toml: not found"
fi

# Check pnpm workspace
echo ""
echo "Checking pnpm workspace..."
if [ -f "pnpm-workspace.yaml" ] && [ -f "frontend/package.json" ]; then
    if pnpm list --depth=0 &> /dev/null; then
        echo "✅ pnpm workspace: OK"
    else
        echo "⚠️  pnpm workspace: needs dependencies installed"
    fi
else
    echo "❌ pnpm workspace files: not found"
fi

echo ""
echo "🎉 Verification complete!"
echo "💡 If you see warnings above, run: bash .devcontainer/setup.sh" 