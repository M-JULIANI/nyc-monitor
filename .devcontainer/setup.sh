#!/bin/bash

# Atlas NYC Monitor Development Container Setup Script
set -e  # Exit on any error

echo "🚀 Setting up Atlas NYC Monitor development environment..."

# Ensure we're in the workspace directory
cd /workspaces/atlas-bootstrapped

# Update system packages first
echo "📦 Updating system packages..."
sudo apt-get update -y

# Install essential build tools and dependencies
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    curl \
    wget \
    git \
    ca-certificates \
    gnupg \
    lsb-release

# Docker permissions setup (only if socket exists)
echo "🐳 Setting up Docker permissions..."
if [ -S "/var/run/docker.sock" ]; then
    sudo groupadd -f docker || true
    sudo usermod -aG docker vscode || true
    sudo chown root:docker /var/run/docker.sock || true
    sudo chmod 666 /var/run/docker.sock || true
    echo "Docker permissions configured"
else
    echo "⚠️  Docker socket not found, skipping Docker setup"
fi

# Install Google Cloud SDK if not present
echo "☁️ Setting up Google Cloud SDK..."
if ! command -v gcloud &> /dev/null; then
    echo "Installing Google Cloud SDK..."
    curl https://sdk.cloud.google.com | bash
    exec -l $SHELL
    gcloud init --console-only
else
    echo "Google Cloud SDK already installed"
fi

# Ensure PATH includes user's local bin
export PATH="/home/vscode/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
echo 'export PATH="/home/vscode/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"' >> ~/.bashrc

# Install Poetry
echo "📦 Installing Poetry..."
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="/home/vscode/.local/bin:$PATH"
    # Configure Poetry
    poetry config virtualenvs.create true
    poetry config virtualenvs.in-project false
    poetry config virtualenvs.path ~/.local/share/pypoetry/venv
else
    echo "Poetry already installed"
fi

# Install pnpm (preferred over npm for this project)
echo "📦 Installing pnpm..."
if ! command -v pnpm &> /dev/null; then
    curl -fsSL https://get.pnpm.io/install.sh | sh -
    export PATH="/home/vscode/.local/share/pnpm:$PATH"
    echo 'export PATH="/home/vscode/.local/share/pnpm:$PATH"' >> ~/.bashrc
else
    echo "pnpm already installed"
fi

# Install Rust (needed for some Python packages like primp)
echo "🦀 Installing Rust..."
if ! command -v rustc &> /dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source ~/.cargo/env
    echo 'source ~/.cargo/env' >> ~/.bashrc
else
    echo "Rust already installed"
fi

# Reload environment
source ~/.bashrc || true
source ~/.cargo/env || true

# Install backend dependencies
echo "🐍 Installing backend Python dependencies..."
if [ -f "backend/pyproject.toml" ]; then
    cd backend
    
    # Ensure we have the latest pip and setuptools
    python3 -m pip install --upgrade pip setuptools wheel
    
    # Set environment variables for building packages that need compilation
    export CARGO_NET_GIT_FETCH_WITH_CLI=true
    export RUSTFLAGS="-C target-cpu=native"
    
    # Install dependencies with poetry
    poetry install --no-interaction --no-ansi
    
    echo "✅ Backend dependencies installed"
    cd ..
else
    echo "⚠️ backend/pyproject.toml not found, skipping backend setup"
fi

# Install frontend dependencies
echo "🌐 Installing frontend dependencies..."
if [ -f "frontend/package.json" ]; then
    cd frontend
    
    # Ensure pnpm is in PATH
    export PATH="/home/vscode/.local/share/pnpm:$PATH"
    
    # Install frontend dependencies
    pnpm install --frozen-lockfile || pnpm install
    
    echo "✅ Frontend dependencies installed"
    cd ..
else
    echo "⚠️ frontend/package.json not found, skipping frontend setup"
fi

# Set up environment file template if it doesn't exist
echo "📝 Setting up environment template..."
if [ ! -f ".env" ]; then
    cat > .env.example << 'EOF'
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
STAGING_BUCKET=gs://your-project-id-vertex-deploy
DOCKER_REGISTRY=gcr.io/your-project-id

# Authentication
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
RAG_CORPUS=your-rag-corpus-id

# Email Configuration
ADMIN_EMAILS=admin@example.com
JUDGE_EMAILS=judge@example.com

# API Keys (Optional - for enhanced functionality)
GOOGLE_CUSTOM_SEARCH_API_KEY=your-search-api-key
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your-search-engine-id
GOOGLE_MAPS_API_KEY=your-maps-api-key
NYC_311_APP_TOKEN=your-nyc-311-token

# Social Media APIs (Optional - for monitoring)
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
REDDIT_REFRESH_TOKEN=your-reddit-refresh-token
TWITTER_API_KEY=your-twitter-api-key
TWITTER_API_KEY_SECRET=your-twitter-api-secret
TWITTER_BEARER_TOKEN=your-twitter-bearer-token

# Google Slides Integration (Optional)
GOOGLE_DRIVE_FOLDER_ID=your-drive-folder-id
STATUS_TRACKER_TEMPLATE_ID=your-template-id
GOOGLE_SLIDES_SERVICE_ACCOUNT_KEY_BASE64=your-base64-encoded-key

# Custom Domain (Optional)
CUSTOM_DOMAIN=your-domain.com
EOF
    echo "Created .env.example - copy this to .env and fill in your values"
else
    echo ".env file already exists"
fi

# Create a simple health check script
echo "🏥 Creating health check script..."
cat > health-check.sh << 'EOF'
#!/bin/bash
echo "🏥 Running development environment health check..."

echo "✅ Checking Python/Poetry..."
poetry --version || echo "❌ Poetry not found"

echo "✅ Checking Node.js/pnpm..."
node --version || echo "❌ Node.js not found"
pnpm --version || echo "❌ pnpm not found"

echo "✅ Checking Docker..."
docker --version || echo "❌ Docker not found"

echo "✅ Checking Google Cloud SDK..."
gcloud --version || echo "❌ gcloud not found"

echo "✅ Checking Rust..."
rustc --version || echo "❌ Rust not found"

echo "🎉 Health check complete!"
EOF

chmod +x health-check.sh

# Run health check
echo "🏥 Running health check..."
./health-check.sh

echo ""
echo "🎉 Atlas NYC Monitor development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Copy .env.example to .env and fill in your configuration"
echo "2. Run 'make install' to verify all dependencies"
echo "3. Run 'make dev' to start the development servers"
echo ""
echo "🔧 Available commands:"
echo "  make help          - Show all available commands"
echo "  make install       - Install all dependencies"
echo "  make dev           - Start development environment"
echo "  make test          - Run tests"
echo "  ./health-check.sh  - Check environment health"
echo ""
echo "Happy coding! 🚀"