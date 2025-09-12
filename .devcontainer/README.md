# Dev Container Setup

This development container provides a complete environment for the Atlas NYC Monitor project, supporting both Mac and Windows host machines.

## What's Included

### System Tools & Languages
- **Python 3.11** with Poetry for dependency management
- **Node.js 20** with pnpm package manager
- **Rust** toolchain (needed for some Python packages)
- **Docker** (via host machine socket)
- **Google Cloud SDK** for cloud deployment

### Build Dependencies
- **cmake** - Required for compiling native Python extensions
- **build-essential** - C/C++ compiler toolchain
- **OpenSSL, libffi, libxml2** - Common library dependencies
- **Image processing libraries** (libjpeg, libpng, zlib)

### VS Code Extensions
- Python development tools (Pylance, Black formatter)
- TypeScript/React development tools
- Docker and Tailwind CSS support
- Mermaid diagram preview

## Quick Start

1. **Open in Dev Container**
   - Install the "Dev Containers" extension in VS Code
   - Open the project folder
   - Click "Reopen in Container" when prompted
   - Or use Command Palette: "Dev Containers: Reopen in Container"

2. **Wait for Setup**
   - The container will automatically run `.devcontainer/setup.sh`
   - This installs all dependencies and configures the environment
   - Initial setup takes 5-10 minutes

3. **Configure Environment**
   ```bash
   # Copy the environment template
   cp .env.example .env
   
   # Edit .env with your actual values
   code .env
   ```

4. **Verify Installation**
   ```bash
   # Check that everything is working
   ./health-check.sh
   
   # Install project dependencies
   make install
   ```

5. **Start Development**
   ```bash
   # Start both backend and frontend
   make dev
   
   # Or start individually
   make dev-api    # Backend only (port 8000)
   make dev-web    # Frontend only (port 5173)
   ```

## Port Forwarding

The container automatically forwards these ports:
- **8000** - Backend API server
- **5173** - Frontend development server
- **3000** - Alternative frontend port

## Troubleshooting

### Container Rebuild Issues
If you encounter dependency issues, try rebuilding the container:
1. Command Palette → "Dev Containers: Rebuild Container"
2. Wait for complete rebuild (may take 10-15 minutes)

### Python Package Installation Failures
The setup includes Rust and cmake specifically to handle packages like `primp` that require compilation:
```bash
# If packages fail to install, try:
cd backend
poetry install --no-cache
```

### Docker Permission Issues
Docker permissions are automatically configured, but if you have issues:
```bash
# Check Docker access
docker ps

# If permission denied, restart the container
```

### Google Cloud Authentication
```bash
# Initialize gcloud (one-time setup)
gcloud init

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

## File Mounts

- **Google Cloud config**: Your host `~/.config/gcloud` is mounted for authentication
- **Docker socket**: Host Docker daemon is accessible via `/var/run/docker.sock`

## Development Commands

See the main project Makefile for all available commands:
```bash
make help
```

Common commands:
- `make install` - Install all dependencies
- `make dev` - Start development servers
- `make test` - Run tests
- `make lint` - Run linters
- `make format` - Format code
- `make build` - Build production images
- `make deploy` - Deploy to Google Cloud

## Environment Variables

Key variables to set in your `.env` file:
- `GOOGLE_CLOUD_PROJECT` - Your GCP project ID
- `GOOGLE_CLIENT_ID` - For authentication
- `RAG_CORPUS` - For AI features
- API keys for external services (optional)

See `.env.example` for the complete list.