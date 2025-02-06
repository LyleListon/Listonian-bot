#!/bin/bash

# Create React app with TypeScript template if not already created
if [ ! -f "package.json" ]; then
    npx create-react-app . --template typescript
fi

# Install dependencies
npm install \
    @emotion/react \
    @emotion/styled \
    @mui/material \
    @mui/icons-material \
    @types/node \
    @types/react \
    @types/react-dom \
    axios \
    chart.js \
    date-fns \
    notistack \
    react \
    react-chartjs-2 \
    react-dom \
    react-query \
    react-router-dom \
    typescript \
    web-vitals

# Install dev dependencies
npm install --save-dev \
    @testing-library/jest-dom \
    @testing-library/react \
    @testing-library/user-event \
    @types/jest

# Create necessary directories
mkdir -p src/components
mkdir -p src/providers
mkdir -p src/hooks
mkdir -p src/utils
mkdir -p src/types

# Install additional type definitions
npm install --save-dev \
    @types/chart.js \
    @types/date-fns

# Create environment file
cat > .env << EOL
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_API_URL=http://localhost:8000/api
EOL

# Create environment file for production
cat > .env.production << EOL
REACT_APP_WS_URL=wss://your-production-domain.com/ws
REACT_APP_API_URL=https://your-production-domain.com/api
EOL

# Update index.html with required fonts and meta tags
cat > public/index.html << EOL
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta name="description" content="Arbitrage Trading Dashboard" />
    <link rel="apple-touch-icon" href="%PUBLIC_URL%/logo192.png" />
    <link rel="manifest" href="%PUBLIC_URL%/manifest.json" />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto:300,400,500,700&display=swap" />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;500;700&display=swap" />
    <title>Arbitrage Dashboard</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>
EOL

# Update package.json scripts
cat > package.json << EOL
{
  "name": "arbitrage-dashboard",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0",
    "@mui/icons-material": "^5.11.16",
    "@mui/material": "^5.13.0",
    "@types/node": "^16.18.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "axios": "^1.4.0",
    "chart.js": "^4.3.0",
    "date-fns": "^2.30.0",
    "notistack": "^3.0.1",
    "react": "^18.2.0",
    "react-chartjs-2": "^5.2.0",
    "react-dom": "^18.2.0",
    "react-query": "^3.39.0",
    "react-router-dom": "^6.11.0",
    "typescript": "^4.9.5",
    "web-vitals": "^2.1.4"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject",
    "lint": "eslint src --ext .ts,.tsx",
    "format": "prettier --write \"src/**/*.{ts,tsx}\"",
    "type-check": "tsc --noEmit"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^5.16.5",
    "@testing-library/react": "^13.4.0",
    "@testing-library/user-event": "^13.5.0",
    "@types/jest": "^27.5.2",
    "@types/chart.js": "^2.9.37",
    "@types/date-fns": "^2.6.0"
  }
}
EOL

# Make the script executable
chmod +x setup.sh

echo "Setup complete! Run 'npm start' to start the development server."