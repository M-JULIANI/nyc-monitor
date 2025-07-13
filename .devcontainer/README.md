# DevContainer Setup


## Current Setup

### Tools Installed
- Python 3.11 with Poetry
- Node.js 20.x with npm and pnpm
- Docker-in-Docker
- Google Cloud SDK
- Agent Starter Pack

### Setup Process
1. **Docker permissions**: Configures Docker socket permissions
2. **Poetry installation**: Installs Poetry if not present
3. **pnpm verification**: Ensures pnpm is available
4. **Backend setup**: Installs Python dependencies via Poetry
5. **Frontend setup**: Installs Node.js dependencies via pnpm workspace

## Usage

### Building the DevContainer
1. Open the project in VS Code
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
3. Select "Dev Containers: Rebuild Container"

### Verification
Run the verification script to check if everything is working:
```bash
./.devcontainer/verify-setup.sh
```

### Development Commands
- `make dev` - Start both backend and frontend
- `make dev-api` - Start backend only
- `make dev-web` - Start frontend only
- `make test` - Run all tests
- `make help` - Show all available commands

## Troubleshooting

### If the container hangs
- Check that Docker is running on your host machine
- Try rebuilding the container completely
- Check the devcontainer logs for specific error messages

### If pnpm isn't working
- The script will install pnpm if it's not found
- PATH is configured in both the Dockerfile and devcontainer.json
- Try running `pnpm install` manually from the project root

### If Poetry isn't working
- The script will install Poetry if it's not found
- Poetry is installed to `~/.local/bin` which is in the PATH
- Try running `poetry install` manually from the backend directory

## Files
- `devcontainer.json` - Main devcontainer configuration
- `Dockerfile` - Container image definition
- `setup.sh` - Post-creation setup script
- `verify-setup.sh` - Verification script