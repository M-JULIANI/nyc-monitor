FROM mcr.microsoft.com/devcontainers/python:3.11

# Install system packages, build tools, and Node.js
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    # Basic utilities
    coreutils \
    vim \
    curl \
    wget \
    jq \
    git \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    # Build tools for native Python packages
    build-essential \
    cmake \
    pkg-config \
    # Development headers for common libraries
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    # Image processing libraries
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    # Add Node.js repository and install
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get -y install --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (needed for Python packages like primp)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable \
    && /root/.cargo/bin/rustup component add rustfmt

# Install pipx and ensure it's in PATH
RUN pip install --user pipx \
    && python -m pipx ensurepath

# Install Agent Starter Pack  
RUN pipx install agent-starter-pack

# Install pnpm globally
RUN npm install -g pnpm

# Install Google Cloud SDK
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
    && apt-get update && apt-get install -y google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

# Switch to vscode user and configure environment
USER vscode

# Copy Rust installation to vscode user and set up environment
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable \
    && /home/vscode/.cargo/bin/rustup component add rustfmt

# Add helpful aliases and ensure PATH includes necessary directories
RUN echo 'export PATH="/home/vscode/.local/bin:/home/vscode/.cargo/bin:$PATH"' >> /home/vscode/.bashrc \
    && echo 'alias ll="ls -la"' >> /home/vscode/.bashrc \
    && echo 'alias pn="pnpm"' >> /home/vscode/.bashrc \
    && echo 'source /home/vscode/.cargo/env' >> /home/vscode/.bashrc

# Ensure cargo environment is available
ENV PATH="/home/vscode/.local/bin:/home/vscode/.cargo/bin:$PATH"
ENV CARGO_HOME="/home/vscode/.cargo"
ENV RUSTUP_HOME="/home/vscode/.rustup"