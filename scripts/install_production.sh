#!/bin/bash
# Listonian Arbitrage Bot Production Installation Script
# This script installs and configures the Listonian Arbitrage Bot for production use.

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'  # No Color

# Log function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Warning function
warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Error function
error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    error "This script must be run as root. Please use sudo."
fi

# Get the installation directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"

log "Installing Listonian Arbitrage Bot to $INSTALL_DIR"

# Step 1: Update system packages
log "Updating system packages..."
apt-get update || error "Failed to update system packages"
apt-get upgrade -y || warn "Failed to upgrade system packages"

# Step 2: Install system dependencies
log "Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    supervisor \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    || error "Failed to install system dependencies"

# Step 3: Create a Python virtual environment
log "Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv" || error "Failed to create Python virtual environment"
source "$INSTALL_DIR/venv/bin/activate" || error "Failed to activate Python virtual environment"

# Step 4: Install Python dependencies
log "Installing Python dependencies..."
pip install --upgrade pip || warn "Failed to upgrade pip"
pip install -r "$INSTALL_DIR/requirements.txt" || error "Failed to install Python dependencies"
pip install psycopg2-binary || warn "Failed to install psycopg2-binary"

# Step 5: Set up PostgreSQL database
log "Setting up PostgreSQL database..."
# Check if PostgreSQL is running
systemctl is-active --quiet postgresql || systemctl start postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE dex_scanner;" || warn "Database may already exist"
sudo -u postgres psql -c "CREATE USER arbitrage_user WITH PASSWORD 'change_this_password';" || warn "User may already exist"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dex_scanner TO arbitrage_user;" || warn "Failed to grant privileges"

# Update the .env.production file with the database URI
sed -i "s|postgresql://username:password@localhost:5432/dex_scanner|postgresql://arbitrage_user:change_this_password@localhost:5432/dex_scanner|g" "$INSTALL_DIR/.env.production" || warn "Failed to update database URI in .env.production"

# Step 6: Configure the systemd service
log "Configuring systemd service..."
# Update the service file with the correct paths
sed -i "s|/path/to/Listonian-bot|$INSTALL_DIR|g" "$INSTALL_DIR/scripts/listonian-bot.service" || warn "Failed to update path in service file"
sed -i "s|/usr/bin/python3|$INSTALL_DIR/venv/bin/python3|g" "$INSTALL_DIR/scripts/listonian-bot.service" || warn "Failed to update Python path in service file"

# Copy the service file to the systemd directory
cp "$INSTALL_DIR/scripts/listonian-bot.service" /etc/systemd/system/ || error "Failed to copy service file"

# Reload systemd
systemctl daemon-reload || error "Failed to reload systemd"

# Enable the service to start on boot
systemctl enable listonian-bot.service || error "Failed to enable service"

# Step 7: Set up Nginx as a reverse proxy (optional)
log "Setting up Nginx as a reverse proxy..."
cat > /etc/nginx/sites-available/listonian-bot << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:9050;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Create a symbolic link to enable the site
ln -sf /etc/nginx/sites-available/listonian-bot /etc/nginx/sites-enabled/ || warn "Failed to create symbolic link"

# Test Nginx configuration
nginx -t || warn "Nginx configuration test failed"

# Reload Nginx
systemctl reload nginx || warn "Failed to reload Nginx"

# Step 8: Create necessary directories
log "Creating necessary directories..."
mkdir -p "$INSTALL_DIR/logs" || warn "Failed to create logs directory"
mkdir -p "$INSTALL_DIR/data" || warn "Failed to create data directory"
chmod -R 755 "$INSTALL_DIR/logs" "$INSTALL_DIR/data" || warn "Failed to set permissions"

# Step 9: Generate a secure API key
log "Generating a secure API key..."
API_KEY=$(openssl rand -hex 32)
sed -i "s|generate_a_secure_api_key_here|$API_KEY|g" "$INSTALL_DIR/.env.production" || warn "Failed to update API key in .env.production"

# Step 10: Start the service
log "Starting the service..."
systemctl start listonian-bot.service || error "Failed to start service"

# Step 11: Check the service status
log "Checking service status..."
systemctl status listonian-bot.service || warn "Service may not be running properly"

log "Installation complete!"
log "The Listonian Arbitrage Bot is now running in production mode."
log "You can access the API at http://localhost:9050/"
log "Check the logs at $INSTALL_DIR/logs/"
log ""
log "IMPORTANT: Please update the following in .env.production:"
log "1. BASE_RPC_URL with your premium RPC endpoint"
log "2. BASESCAN_API_KEY with your Basescan API key"
log "3. Review and adjust other configuration parameters as needed"
log ""
log "After updating the configuration, restart the service with:"
log "sudo systemctl restart listonian-bot.service"