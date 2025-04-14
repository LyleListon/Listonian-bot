# Listonian Bot Deployment Guide

This guide provides detailed instructions for deploying the Listonian Bot in a production environment. Follow these steps to ensure a secure, reliable, and high-performance deployment.

## Deployment Architectures

### Single Server Deployment

A single server deployment is suitable for testing or small-scale operations.

**Requirements:**
- VPS or dedicated server with at least 4 CPU cores, 8GB RAM, 100GB SSD
- Ubuntu 20.04 LTS or later
- Python 3.9+
- Node.js 14+
- Nginx (for reverse proxy)
- SSL certificate

**Architecture Diagram:**
```
                   ┌─────────────┐
                   │    Nginx    │
                   │ Reverse Proxy│
                   └──────┬──────┘
                          │
                          ▼
┌─────────────────────────────────────────────┐
│                  Server                      │
│                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ Bot Core │    │   API   │    │Dashboard│  │
│  └─────────┘    └─────────┘    └─────────┘  │
│                                             │
└─────────────────────────────────────────────┘
```

### Distributed Deployment

A distributed deployment is recommended for production environments with high availability requirements.

**Requirements:**
- Multiple VPS or dedicated servers (at least 3)
- Load balancer
- Redis for caching and message queue
- PostgreSQL database
- Docker and Docker Compose
- Kubernetes (optional)

**Architecture Diagram:**
```
                   ┌─────────────┐
                   │    Load     │
                   │  Balancer   │
                   └──────┬──────┘
                          │
                          ▼
┌─────────────┬─────────────┬─────────────┐
│  Server 1   │  Server 2   │  Server 3   │
│             │             │             │
│ ┌─────────┐ │ ┌─────────┐ │ ┌─────────┐ │
│ │ Bot Core │ │ │   API   │ │ │Dashboard│ │
│ └─────────┘ │ └─────────┘ │ └─────────┘ │
└──────┬──────┴──────┬──────┴──────┬──────┘
       │              │             │
       ▼              ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│    Redis    │ │  PostgreSQL │ │  Monitoring │
└─────────────┘ └─────────────┘ └─────────────┘
```

## Deployment Steps

### 1. Server Preparation

#### Update System
```bash
sudo apt update
sudo apt upgrade -y
```

#### Install Dependencies
```bash
sudo apt install -y python3.9 python3.9-venv python3.9-dev build-essential git nginx
```

#### Install Node.js
```bash
curl -fsSL https://deb.nodesource.com/setup_14.x | sudo -E bash -
sudo apt install -y nodejs
```

#### Install Redis (for distributed deployment)
```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
```

#### Install PostgreSQL (for distributed deployment)
```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
```

### 2. Clone Repository

```bash
git clone https://github.com/your-organization/Listonian-bot.git /opt/Listonian-bot
cd /opt/Listonian-bot
```

### 3. Set Up Python Environment

```bash
python3.9 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Node.js Dependencies

```bash
npm install
```

### 5. Configure Environment

Create a production environment file:

```bash
cp .env.production.template .env.production
```

Edit the `.env.production` file with your production settings:

```bash
nano .env.production
```

### 6. Set Up Database (for distributed deployment)

```bash
sudo -u postgres psql
```

In the PostgreSQL prompt:
```sql
CREATE DATABASE listonian;
CREATE USER listonian_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE listonian TO listonian_user;
\q
```

Update the database configuration in `.env.production`:
```
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=listonian
DB_USER=listonian_user
DB_PASSWORD=your_secure_password
```

### 7. Configure Nginx

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/listonian-bot
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;

    # Dashboard
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable the configuration:

```bash
sudo ln -s /etc/nginx/sites-available/listonian-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Set Up SSL Certificate

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 9. Create Systemd Services

#### Bot Service

```bash
sudo nano /etc/systemd/system/listonian-bot.service
```

Add the following:

```ini
[Unit]
Description=Listonian Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/Listonian-bot
ExecStart=/opt/Listonian-bot/venv/bin/python run_bot.py --env production
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=listonian-bot
Environment="PATH=/opt/Listonian-bot/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
```

#### API Service

```bash
sudo nano /etc/systemd/system/listonian-api.service
```

Add the following:

```ini
[Unit]
Description=Listonian Bot API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/Listonian-bot
ExecStart=/opt/Listonian-bot/venv/bin/python bot_api_server.py --env production
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=listonian-api
Environment="PATH=/opt/Listonian-bot/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
```

#### Dashboard Service

```bash
sudo nano /etc/systemd/system/listonian-dashboard.service
```

Add the following:

```ini
[Unit]
Description=Listonian Bot Dashboard
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/Listonian-bot
ExecStart=/opt/Listonian-bot/venv/bin/python run_dashboard.py --env production
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=listonian-dashboard
Environment="PATH=/opt/Listonian-bot/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
```

### 10. Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable listonian-bot.service
sudo systemctl enable listonian-api.service
sudo systemctl enable listonian-dashboard.service
sudo systemctl start listonian-bot.service
sudo systemctl start listonian-api.service
sudo systemctl start listonian-dashboard.service
```

### 11. Set Up Monitoring

#### Install Prometheus and Grafana

```bash
sudo apt install -y prometheus grafana
sudo systemctl enable prometheus
sudo systemctl enable grafana-server
sudo systemctl start prometheus
sudo systemctl start grafana-server
```

Configure Prometheus to scrape metrics from the bot:

```bash
sudo nano /etc/prometheus/prometheus.yml
```

Add the following to the `scrape_configs` section:

```yaml
  - job_name: 'listonian-bot'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
```

Restart Prometheus:

```bash
sudo systemctl restart prometheus
```

Access Grafana at `https://your-domain.com:3000` and set up dashboards.

### 12. Set Up Log Rotation

```bash
sudo nano /etc/logrotate.d/listonian-bot
```

Add the following:

```
/opt/Listonian-bot/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
    postrotate
        systemctl reload listonian-bot.service >/dev/null 2>&1 || true
        systemctl reload listonian-api.service >/dev/null 2>&1 || true
        systemctl reload listonian-dashboard.service >/dev/null 2>&1 || true
    endscript
}
```

### 13. Set Up Backup

Create a backup script:

```bash
nano /opt/Listonian-bot/scripts/backup.sh
```

Add the following:

```bash
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/listonian-bot_$TIMESTAMP"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration files
cp -r /opt/Listonian-bot/configs $BACKUP_DIR/
cp /opt/Listonian-bot/.env.production $BACKUP_DIR/

# Backup database (for distributed deployment)
pg_dump -U listonian_user -h localhost listonian > $BACKUP_DIR/database.sql

# Backup logs
cp -r /opt/Listonian-bot/logs $BACKUP_DIR/

# Compress backup
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# Remove backups older than 30 days
find /opt/backups -name "listonian-bot_*.tar.gz" -type f -mtime +30 -delete
```

Make the script executable:

```bash
chmod +x /opt/Listonian-bot/scripts/backup.sh
```

Set up a cron job to run the backup script daily:

```bash
sudo crontab -e
```

Add the following:

```
0 2 * * * /opt/Listonian-bot/scripts/backup.sh
```

## Docker Deployment (Alternative)

### 1. Create Dockerfile

```bash
nano Dockerfile
```

Add the following:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package.json and install Node.js dependencies
COPY package.json .
RUN npm install

# Copy the rest of the application
COPY . .

# Expose ports
EXPOSE 8000 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run
CMD ["python", "run_bot.py", "--env", "production"]
```

### 2. Create Docker Compose File

```bash
nano docker-compose.yml
```

Add the following:

```yaml
version: '3'

services:
  bot:
    build: .
    restart: always
    volumes:
      - ./configs:/app/configs
      - ./logs:/app/logs
      - ./.env.production:/app/.env.production
    command: python run_bot.py --env production
    depends_on:
      - redis
      - postgres
    networks:
      - listonian-network

  api:
    build: .
    restart: always
    volumes:
      - ./configs:/app/configs
      - ./logs:/app/logs
      - ./.env.production:/app/.env.production
    command: python bot_api_server.py --env production
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - postgres
      - bot
    networks:
      - listonian-network

  dashboard:
    build: .
    restart: always
    volumes:
      - ./configs:/app/configs
      - ./logs:/app/logs
      - ./.env.production:/app/.env.production
    command: python run_dashboard.py --env production
    ports:
      - "8080:8080"
    depends_on:
      - api
    networks:
      - listonian-network

  redis:
    image: redis:6-alpine
    restart: always
    volumes:
      - redis-data:/data
    networks:
      - listonian-network

  postgres:
    image: postgres:13-alpine
    restart: always
    environment:
      POSTGRES_DB: listonian
      POSTGRES_USER: listonian_user
      POSTGRES_PASSWORD: your_secure_password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - listonian-network

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
      - dashboard
    networks:
      - listonian-network

networks:
  listonian-network:

volumes:
  redis-data:
  postgres-data:
```

### 3. Create Nginx Configuration

```bash
nano nginx.conf
```

Add the following:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;

    # Dashboard
    location / {
        proxy_pass http://dashboard:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://api:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 4. Build and Run with Docker Compose

```bash
docker-compose build
docker-compose up -d
```

## Deployment Checklist

Before going live, ensure you've completed the following:

- [ ] All environment variables are properly set
- [ ] SSL certificates are installed and valid
- [ ] Firewall is configured to allow only necessary ports
- [ ] Database backups are scheduled
- [ ] Monitoring is set up and alerts are configured
- [ ] Log rotation is configured
- [ ] Services are set to start automatically on system boot
- [ ] Test environment is separate from production
- [ ] Rollback procedures are documented
- [ ] Security hardening is complete

## Scaling Considerations

As your trading volume grows, consider the following scaling strategies:

1. **Vertical Scaling**: Increase resources (CPU, RAM) on existing servers
2. **Horizontal Scaling**: Add more servers and distribute the load
3. **Database Optimization**: Implement sharding or read replicas
4. **Caching**: Use Redis for caching frequently accessed data
5. **Load Balancing**: Implement load balancing for API and dashboard services
6. **Microservices**: Split the application into smaller, specialized services

## Troubleshooting

### Common Deployment Issues

#### Services Won't Start
- Check logs: `sudo journalctl -u listonian-bot.service`
- Verify permissions: `sudo chown -R ubuntu:ubuntu /opt/Listonian-bot`
- Check environment variables: `cat /opt/Listonian-bot/.env.production`

#### Nginx Configuration Issues
- Test configuration: `sudo nginx -t`
- Check logs: `sudo tail -f /var/log/nginx/error.log`

#### Database Connection Issues
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check connection parameters in `.env.production`
- Test connection: `psql -U listonian_user -h localhost -d listonian`

#### Docker Issues
- Check container status: `docker-compose ps`
- View logs: `docker-compose logs -f`
- Restart services: `docker-compose restart`

## Maintenance Procedures

### Updates and Upgrades

1. Create a backup before updating:
   ```bash
   /opt/Listonian-bot/scripts/backup.sh
   ```

2. Pull the latest code:
   ```bash
   cd /opt/Listonian-bot
   git pull
   ```

3. Update dependencies:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   npm install
   ```

4. Restart services:
   ```bash
   sudo systemctl restart listonian-bot.service
   sudo systemctl restart listonian-api.service
   sudo systemctl restart listonian-dashboard.service
   ```

### Monitoring and Maintenance

1. Check service status:
   ```bash
   sudo systemctl status listonian-bot.service
   sudo systemctl status listonian-api.service
   sudo systemctl status listonian-dashboard.service
   ```

2. View logs:
   ```bash
   sudo journalctl -u listonian-bot.service -f
   sudo journalctl -u listonian-api.service -f
   sudo journalctl -u listonian-dashboard.service -f
   ```

3. Check disk usage:
   ```bash
   df -h
   du -sh /opt/Listonian-bot/logs/
   ```

4. Monitor system resources:
   ```bash
   htop
   ```

5. Check database size (for distributed deployment):
   ```bash
   sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('listonian'));"
   ```
