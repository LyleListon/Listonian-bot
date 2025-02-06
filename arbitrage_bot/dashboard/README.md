# Arbitrage Dashboard with OAuth2 Authentication

Real-time monitoring dashboard for ML-powered arbitrage trading with secure OAuth2 authentication.

## Features

### Authentication
- OAuth2 integration with Google and GitHub
- Role-based access control
- Secure session management
- JWT token authentication
- Real-time WebSocket authentication

### Dashboard
- Real-time opportunity monitoring
- ML prediction visualization
- Performance metrics
- Risk management indicators
- Interactive charts

## Setup

### 1. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
./setup.sh  # This will install all required npm packages
```

### 2. Configure OAuth2 Authentication

The easiest way to set up OAuth2 is using our setup wizard:

```bash
# Make the script executable
chmod +x scripts/setup_oauth.py

# Run the setup wizard
./scripts/setup_oauth.py
```

Alternatively, you can configure manually:

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```

2. Set up OAuth2 providers:

   **Google OAuth2**
   1. Go to [Google Cloud Console](https://console.cloud.google.com)
   2. Create a new project or select existing one
   3. Enable OAuth2 API
   4. Create OAuth2 credentials
   5. Add authorized redirect URIs:
      - `http://localhost:3000/auth/google/callback` (development)
      - `https://your-domain.com/auth/google/callback` (production)

   **GitHub OAuth2**
   1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
   2. Create new OAuth App
   3. Add Homepage URL and Authorization callback URL:
      - Homepage: `http://localhost:3000`
      - Callback: `http://localhost:3000/auth/github/callback`

3. Update `.env` with your credentials:
   ```
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GITHUB_CLIENT_ID=your-github-client-id
   GITHUB_CLIENT_SECRET=your-github-client-secret
   ```

### 3. Start Development Servers

```bash
# Terminal 1: Start backend
cd backend
uvicorn api:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
npm start
```

Visit `http://localhost:3000` to access the dashboard.

## Authentication Flow

1. User clicks "Sign in with Google/GitHub"
2. OAuth2 provider handles authentication
3. Backend validates user and creates session
4. JWT token issued for API authentication
5. WebSocket connection established with token
6. Real-time updates begin flowing

## Security Features

### Backend
- JWT token authentication
- Secure session management
- CORS protection
- Rate limiting
- Input validation
- Error handling
- Audit logging

### Frontend
- Protected routes
- Token management
- Session monitoring
- Automatic token refresh
- Secure WebSocket
- Error boundaries

## Role-Based Access

Three user roles are available:

1. Admin
   - Full system access
   - User management
   - Configuration changes

2. Trader
   - View dashboard
   - Execute trades
   - View analytics

3. Viewer
   - View dashboard
   - View analytics

## Development

### Backend Testing
```bash
cd backend
pytest
```

### Frontend Testing
```bash
cd frontend
npm test
```

### Code Style
```bash
# Frontend
npm run lint
npm run format

# Backend
flake8
black .
```

## Production Deployment

### 1. Build Frontend
```bash
cd frontend
npm run build
```

### 2. Configure Production Settings
1. Update `.env`:
   ```
   NODE_ENV=production
   FRONTEND_URL=https://your-domain.com
   ```

2. Update OAuth2 redirect URIs in provider dashboards

### 3. SSL/TLS Setup
1. Obtain SSL certificate
2. Update `auth_config.yaml`:
   ```yaml
   production:
     ssl_required: true
     secure_headers:
       enabled: true
   ```

### 4. Start Production Server
```bash
uvicorn api:app --host 0.0.0.0 --port 443 --ssl-keyfile=/path/to/key.pem --ssl-certfile=/path/to/cert.pem
```

## Monitoring

### Authentication Monitoring
- Failed login attempts
- Token usage
- Session duration
- Active users
- Role changes

### Security Monitoring
- Rate limit hits
- Invalid tokens
- Suspicious patterns
- Error rates
- System health

## Troubleshooting

### Common Issues

1. OAuth2 Callback Error
   - Check redirect URIs
   - Verify credentials
   - Check SSL settings

2. WebSocket Connection Failed
   - Verify token
   - Check CORS settings
   - Check network connectivity

3. Authentication Failed
   - Check provider status
   - Verify user permissions
   - Check token expiration

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests
4. Submit pull request

## License

MIT License - see LICENSE file for details