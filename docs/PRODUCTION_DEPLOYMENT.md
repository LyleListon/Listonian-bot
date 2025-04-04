# Listonian Arbitrage Bot Production Deployment Guide

This guide provides step-by-step instructions for deploying the Listonian Arbitrage Bot in a production environment.

## Prerequisites

- A Linux server (Ubuntu 20.04 LTS or later recommended)
- Root or sudo access
- Python 3.8 or later
- PostgreSQL 12 or later
- Nginx (optional, for API access)

## Quick Start

For a quick automated installation, you can use the provided installation script:

```bash
# Clone the repository
git clone https://github.com/your-org/Listonian-bot.git
cd Listonian-bot

# Make the installation script executable
chmod +x scripts/install_production.sh

# Run the installation script as root
sudo ./scripts/install_production.sh
```

The installation script will:
1. Install system dependencies
2. Set up a PostgreSQL database
3. Install Python dependencies
4. Configure the systemd service
5. Start the service

After installation, you'll need to update the `.env.production` file with your specific configuration.

## Manual Installation

If you prefer to install manually or need more control over the installation process, follow these steps:

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/Listonian-bot.git
cd Listonian-bot
```

### 2. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
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
    python3-dev
```

### 3. Create a Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install psycopg2-binary
```

### 5. Set Up PostgreSQL Database

```bash
# Start PostgreSQL if it's not running
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE dex_scanner;"
sudo -u postgres psql -c "CREATE USER arbitrage_user WITH PASSWORD 'change_this_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dex_scanner TO arbitrage_user;"
```

### 6. Configure Environment Variables

Edit the `.env.production` file with your specific configuration:

```bash
# Edit the .env.production file
nano .env.production
```

Make sure to update:
- `BASE_RPC_URL` with your premium RPC endpoint
- `BASESCAN_API_KEY` with your Basescan API key
- `DATABASE_URI` with your database connection string
- `BASE_DEX_SCANNER_API_KEY` with a secure API key

### 7. Configure the Systemd Service

```bash
# Edit the service file with the correct paths
sed -i "s|/path/to/Listonian-bot|$(pwd)|g" scripts/listonian-bot.service
sed -i "s|/usr/bin/python3|$(pwd)/venv/bin/python3|g" scripts/listonian-bot.service

# Copy the service file to the systemd directory
sudo cp scripts/listonian-bot.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable listonian-bot.service
```

### 8. Set Up Nginx as a Reverse Proxy (Optional)

```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/listonian-bot << EOF
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
sudo ln -sf /etc/nginx/sites-available/listonian-bot /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 9. Create Necessary Directories

```bash
mkdir -p logs data
chmod -R 755 logs data
```

### 10. Start the Service

```bash
sudo systemctl start listonian-bot.service
```

### 11. Check the Service Status

```bash
sudo systemctl status listonian-bot.service
```

## Configuration Options

The `.env.production` file contains all the configuration options for the bot. Here's an explanation of each option:

### Environment Settings

- `ENVIRONMENT`: Set to `production` for production environments
- `USE_MOCK_DATA`: Set to `false` for production environments

### Blockchain Connectivity

- `BASE_RPC_URL`: URL of the Base blockchain RPC endpoint
- `BASESCAN_API_KEY`: API key for Basescan

### Database Configuration

- `DATABASE_URI`: URI for the PostgreSQL database

### Scanning Configuration

- `SCAN_INTERVAL_MINUTES`: Interval in minutes between DEX scans

### API Configuration

- `MCP_SERVER_HOST`: Host to bind the API server to
- `MCP_SERVER_PORT`: Port to bind the API server to
- `BASE_DEX_SCANNER_API_KEY`: API key for accessing the API

### Trading Configuration

- `MIN_PROFIT_THRESHOLD_USD`: Minimum profit threshold in USD
- `MAX_POSITION_SIZE_ETH`: Maximum position size in ETH
- `SLIPPAGE_TOLERANCE`: Slippage tolerance in basis points (1/100 of a percent)

## Monitoring and Maintenance

### Health Monitoring

The bot includes a health monitoring script that can be run as a cron job to periodically check the system:

```bash
# Edit the crontab
crontab -e

# Add a cron job to run the health check every 5 minutes
*/5 * * * * cd /path/to/Listonian-bot && ./venv/bin/python scripts/monitor_health.py
```

The health check script will:
1. Check if the process is running
2. Check if the systemd service is active
3. Check if the API is healthy
4. Check if the logs are fresh
5. Send an alert email if any of the checks fail

### Log Rotation

To prevent logs from growing too large, you can set up log rotation:

```bash
sudo tee /etc/logrotate.d/listonian-bot << EOF
/path/to/Listonian-bot/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
    postrotate
        systemctl reload listonian-bot.service
    endscript
}
EOF
```

### Backup Strategy

It's important to regularly back up your database and configuration:

```bash
# Create a backup script
tee scripts/backup.sh << EOF
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=\$(date +%Y%m%d_%H%M%S)
mkdir -p \$BACKUP_DIR

# Backup the database
pg_dump -U arbitrage_user -h localhost dex_scanner > \$BACKUP_DIR/dex_scanner_\$DATE.sql

# Backup the configuration
cp .env.production \$BACKUP_DIR/env_production_\$DATE.backup

# Compress the backups
tar -czf \$BACKUP_DIR/listonian_bot_backup_\$DATE.tar.gz \$BACKUP_DIR/dex_scanner_\$DATE.sql \$BACKUP_DIR/env_production_\$DATE.backup

# Remove old backups (keep last 30 days)
find \$BACKUP_DIR -name "listonian_bot_backup_*.tar.gz" -type f -mtime +30 -delete
EOF

# Make the backup script executable
chmod +x scripts/backup.sh

# Add a cron job to run the backup daily
crontab -e
# Add the following line
0 0 * * * /path/to/Listonian-bot/scripts/backup.sh
```

## Upgrading

To upgrade the bot to a new version:

```bash
# Stop the service
sudo systemctl stop listonian-bot.service

# Pull the latest changes
git pull

# Install any new dependencies
source venv/bin/activate
pip install -r requirements.txt

# Start the service
sudo systemctl start listonian-bot.service
```

## Troubleshooting

### Service Won't Start

If the service won't start, check the logs:

```bash
sudo journalctl -u listonian-bot.service -n 100
```

Common issues include:
- Incorrect paths in the service file
- Missing dependencies
- Configuration errors in `.env.production`

### Database Connection Issues

If the bot can't connect to the database:

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check if the database exists
sudo -u postgres psql -c "\l" | grep dex_scanner

# Check if the user has access
sudo -u postgres psql -c "\du" | grep arbitrage_user
```

### API Not Responding

If the API is not responding:

```bash
# Check if the process is running
ps aux | grep run_base_dex_scanner_mcp

# Check the logs
tail -n 100 logs/base_dex_scanner_mcp.log

# Check if the port is in use
netstat -tuln | grep 9050
```

## Security Considerations

### API Security

The API is protected by an API key. Make sure to:
- Generate a strong API key
- Keep the API key secret
- Use HTTPS if exposing the API to the internet

### Private Key Management

If you're using the bot to execute trades, you'll need to manage private keys securely:

- Store private keys in a secure location
- Consider using a hardware security module (HSM)
- Never hardcode private keys in the code

### Firewall Configuration

If you're exposing the API to the internet, make sure to configure your firewall:

```bash
# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS if using Nginx
sudo ufw allow 80
sudo ufw allow 443

# Deny direct access to the API port
sudo ufw deny 9050

# Enable the firewall
sudo ufw enable
```

## Conclusion

By following this guide, you should have a fully functional Listonian Arbitrage Bot running in a production environment. Remember to:

1. Regularly check the logs for any issues
2. Monitor the system for any performance problems
3. Keep the bot updated with the latest changes
4. Regularly back up your database and configuration

For any questions or issues, please refer to the project documentation or contact the project maintainers.