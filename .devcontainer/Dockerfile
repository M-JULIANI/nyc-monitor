FROM mcr.microsoft.com/devcontainers/python:3.11

# Install system packages
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    coreutils \
    vim \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install pipx and ensure it's in PATH
RUN pip install --user pipx \
    && python -m pipx ensurepath \
    && echo 'export PATH="$PATH:/home/vscode/.local/bin"' >> /home/vscode/.bashrc

# Install Agent Starter Pack
RUN pipx install agent-starter-pack

# Add some helpful aliases
RUN echo 'alias ll="ls -la"' >> /home/vscode/.bashrc

# Set the default user
USER vscode