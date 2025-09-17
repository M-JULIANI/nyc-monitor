# Dev Container Troubleshooting Guide

## Current Issue: `cmake not installed` Error

### Problem
The `make install` command fails with:
```
is `cmake` not installed?
```

This happens because you're still in the old container that doesn't have the build tools.

### Solution

1. **Complete cleanup** (already done):
   ```bash
   ./.devcontainer/clean-all.sh
   ```

2. **Rebuild the container completely**:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type: "Dev Containers: Rebuild Container"
   - Select it and wait for the rebuild

3. **Verify the new environment**:
   ```bash
   # Check that build tools are now available
   cmake --version
   rustc --version
   poetry --version
   pnpm --version
   ```

4. **Install dependencies**:
   ```bash
   make install
   ```

## What Was Fixed

### Updated Dockerfile
- ✅ Added `build-essential` (gcc, g++, make)
- ✅ Added `cmake` (required for primp and other packages)
- ✅ Added `pkg-config` (build configuration)
- ✅ Added development headers (libssl-dev, libffi-dev, etc.)
- ✅ Added Rust toolchain (required for primp)
- ✅ Added image processing libraries

### Cleaned Up Caches
- ✅ Removed Poetry virtual environments
- ✅ Removed Node.js modules and caches
- ✅ Removed Rust/Cargo caches
- ✅ Removed Python bytecode caches
- ✅ Removed build artifacts

## If Problems Persist

### Check Container Rebuild
```bash
# Verify you're in the new container
cmake --version  # Should show cmake version
rustc --version  # Should show rust version
```

### Manual Installation
If the rebuild doesn't work, try manually installing missing tools:
```bash
# Install build tools
sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config libssl-dev

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### Alternative: Use Different Python Package
If primp continues to cause issues, we could replace it in the dependencies:
```bash
# Edit backend/pyproject.toml to replace primp with requests
# This is a last resort option
```

## Expected Timeline
- **Container rebuild**: 10-15 minutes
- **Package installation**: 5-10 minutes after rebuild
- **Total**: 15-25 minutes for complete fix

## Success Indicators
- ✅ `cmake --version` shows version number
- ✅ `rustc --version` shows version number  
- ✅ `make install` completes without errors
- ✅ Backend Poetry dependencies install successfully
- ✅ Frontend pnpm dependencies install successfully

## Container Features Now Included
- Python 3.11 + Poetry
- Node.js 20 + pnpm
- Docker-in-Docker
- Google Cloud SDK
- **Build tools (cmake, gcc, etc.)**
- **Rust toolchain**
- **Development headers**
- **Image processing libraries**
