# Setup Guide

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Node.js 16 or higher
- Git
- Operating System: Linux/macOS/Windows

### Network Requirements
- Reliable internet connection
- Access to Base network RPC
- Sufficient Base network tokens for gas

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for development
```

### 3. Configuration Setup

#### Environment Variables
Create a `.env` file:
```env
BASE_RPC_URL=your-rpc-url
CHAIN_ID=8453
PRIVATE_KEY=your-private-key
DASHBOARD_PORT=5001
DASHBOARD_WEBSOCKET_PORT=8772
```

#### Configuration Files
```bash
# Copy default configuration
cp configs/default.json configs/local.json

# Edit local configuration
nano configs/local.json
```

## Development Setup

### 1. Install Development Tools
```bash
# Install pre-commit hooks
pre-commit install

# Install development dependencies
pip install -r requirements-dev.txt
```

### 2. Configure IDE
For VSCode:
- Install Python extension
- Set Python interpreter to virtual environment
- Enable linting and formatting

### 3. Setup Dashboard
```bash
# Install frontend dependencies
cd dashboard/frontend
npm install

# Build frontend
npm run build
```

## Running the System

### 1. Start Dashboard
```bash
# Terminal 1
python src/scripts/start_dashboard.py
```

### 2. Start Bot
```bash
# Terminal 2
python src/scripts/start_bot.py
```

### 3. Start Monitoring
```bash
# Terminal 3
python src/scripts/start_monitoring.py
```

## Verification

### 1. System Health Check
```bash
python src/scripts/health_check.py
```

### 2. Access Dashboard
- Open browser: http://localhost:5001
- Verify WebSocket connection
- Check real-time updates

### 3. Verify Monitoring
- Check logs in logs/
- Verify metrics collection
- Test alert system

## Troubleshooting

### Common Issues

#### RPC Connection
- Verify RPC URL is correct
- Check network connectivity
- Ensure sufficient rate limits

#### Configuration
- Validate JSON syntax
- Check environment variables
- Verify file permissions

#### Dashboard
- Check port availability
- Verify WebSocket connection
- Clear browser cache

## Security Notes

### Private Keys
- Never commit private keys
- Use environment variables
- Rotate keys regularly

### API Keys
- Secure storage
- Regular rotation
- Monitor usage

### Access Control
- Use strong passwords
- Enable authentication
- Monitor access logs

## Next Steps

### 1. Development
- Read [Development Guide](./development.md)
- Setup test environment
- Review coding standards

### 2. Production
- Review [Deployment Guide](./deployment.md)
- Setup monitoring
- Configure alerts

### 3. Maintenance
- Regular updates
- Security patches
- Performance monitoring

Last Updated: 2025-02-10