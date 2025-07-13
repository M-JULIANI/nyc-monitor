#!/bin/bash

# Reset PNPM Installation Script
# This script completely resets pnpm and its cache, then reinstalls everything fresh

set -e

echo "🧹 Resetting pnpm installation..."

# 1. Remove all existing node_modules and lock files
echo "Removing existing node_modules and lock files..."
rm -rf /workspaces/atlas-bootstrapped/frontend/node_modules
rm -rf /workspaces/atlas-bootstrapped/frontend/package-lock.json
rm -rf /workspaces/atlas-bootstrapped/frontend/pnpm-lock.yaml
rm -rf /workspaces/atlas-bootstrapped/node_modules
rm -rf /workspaces/atlas-bootstrapped/.pnpm-store

# 2. Remove existing pnpm installation
echo "Removing existing pnpm installation..."
rm -rf ~/.local/share/pnpm
rm -rf ~/.npm/_npx
rm -rf ~/.cache/pnpm

# 3. Clean npm cache
echo "Cleaning npm cache..."
npm cache clean --force || true

# 4. Install pnpm fresh
echo "Installing pnpm fresh..."
curl -fsSL https://get.pnpm.io/install.sh | sh -

# 5. Add pnpm to current session PATH
export PATH="$HOME/.local/share/pnpm:$PATH"

# 6. Verify pnpm installation
echo "Verifying pnpm installation..."
which pnpm
pnpm --version

# 7. Install frontend dependencies
echo "Installing frontend dependencies..."
cd /workspaces/atlas-bootstrapped/frontend
pnpm install

# 8. Test mapbox import
echo "Testing mapbox-gl import..."
node -e "
try {
  const mapboxgl = require('mapbox-gl');
  console.log('✅ mapbox-gl loads successfully');
  console.log('✅ mapboxgl.Map exists:', typeof mapboxgl.Map);
  console.log('✅ Version:', mapboxgl.version);
} catch (e) {
  console.error('❌ Error loading mapbox-gl:', e.message);
  process.exit(1);
}
"

echo "Testing react-map-gl import..."
node -e "
try {
  const { Map } = require('react-map-gl');
  console.log('✅ react-map-gl Map import works:', typeof Map);
} catch (e) {
  console.error('❌ react-map-gl Map import failed:', e.message);
  process.exit(1);
}
"

echo "🎉 pnpm reset and installation completed successfully!"
echo "📝 To use pnpm in your current session, run:"
echo "    export PATH=\"\$HOME/.local/share/pnpm:\$PATH\"" 