FROM mcr.microsoft.com/devcontainers/python:3.11

# Install system packages
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
    && apt-get update \
    && apt-get -y install --no-install-recommends google-cloud-sdk \
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