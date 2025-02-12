FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DASHBOARD_PORT=5000 \
    DASHBOARD_WEBSOCKET_PORT=8771 \
    SHELL=/usr/bin/pwsh \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    wget \
    apt-transport-https \
    gnupg \
    default-jdk \
    ca-certificates \
    --no-install-recommends \
    && wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg \
    && mv microsoft.gpg /etc/apt/trusted.gpg.d/ \
    && sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-debian-bullseye-prod bullseye main" > /etc/apt/sources.list.d/microsoft.list' \
    && apt-get update \
    && apt-get install -y openjdk-17-jdk \
    && java -version \
    && update-alternatives --set java /usr/lib/jvm/java-17-openjdk-amd64/bin/java \
    && apt-get install -y powershell \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /root/.config/powershell \
    && mkdir -p /root/.vscode-remote/data \
    && chmod -R 755 /root/.config/powershell /root/.vscode-remote/data

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Set working directory
WORKDIR /workspaces/Listonian-bot

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf ~/.cache/pip/*

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pwsh -NoProfile -Command \
        "try { \
            if (!(Get-Process -Name 'python' -ErrorAction Stop)) { exit 1 }; \
            $response = Invoke-WebRequest -Uri http://localhost:$env:DASHBOARD_PORT/health -UseBasicParsing; \
            if ($response.StatusCode -ne 200) { exit 1 }; \
            exit 0 \
        } catch { exit 1 }"

# Create required directories with proper permissions
RUN mkdir -p /workspaces/Listonian-bot && \
    chown -R root:root /workspaces/Listonian-bot && \
    chmod -R 755 /workspaces/Listonian-bot