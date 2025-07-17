FROM mcr.microsoft.com/devcontainers/python:3.11

# Install system packages and Node.js
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    coreutils \
    vim \
    curl \
    jq \
    apt-transport-https \
    ca-certificates \
    gnupg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get -y install --no-install-recommends google-cloud-sdk nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install pipx and ensure it's in PATH
RUN pip install --user pipx \
    && python -m pipx ensurepath

# Install Agent Starter Pack  
RUN pipx install agent-starter-pack

# Install pnpm globally
RUN npm install -g pnpm

# Switch to vscode user and configure environment
USER vscode

# Add helpful aliases and ensure PATH includes necessary directories
RUN echo 'export PATH="/home/vscode/.local/bin:$PATH"' >> /home/vscode/.bashrc \
    && echo 'alias ll="ls -la"' >> /home/vscode/.bashrc \
    && echo 'alias pn="pnpm"' >> /home/vscode/.bashrc