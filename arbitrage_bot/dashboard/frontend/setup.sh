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
    @tanstack/react-query \
    @uniswap/sdk \
    @uniswap/v2-sdk \
    @uniswap/v3-sdk \
    @pancakeswap/sdk \
    @pancakeswap/v3-sdk \
    axios \
    chart.js \
    date-fns \
    ethers@5.7.2 \
    notistack \
    react \
    react-chartjs-2 \
    react-dom \
    react-query \
    react-router-dom \
    typescript \
    web-vitals \
    web3@1.10.0

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

# Create environment file
cat > .env << EOL
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_API_URL=http://localhost:8000/api

# Blockchain Network Settings
REACT_APP_NETWORK_RPC_URL=https://base-mainnet.g.alchemy.com/v2/your-api-key
REACT_APP_CHAIN_ID=8453  # Base Mainnet

# Contract Addresses
REACT_APP_UNISWAP_V2_ROUTER=0x...
REACT_APP_UNISWAP_V3_ROUTER=0x...
REACT_APP_PANCAKESWAP_V2_ROUTER=0x...
REACT_APP_PANCAKESWAP_V3_ROUTER=0x...
EOL

# Create environment file for production
cat > .env.production << EOL
REACT_APP_WS_URL=wss://your-production-domain.com/ws
REACT_APP_API_URL=https://your-production-domain.com/api

# Blockchain Network Settings
REACT_APP_NETWORK_RPC_URL=https://base-mainnet.g.alchemy.com/v2/your-api-key
REACT_APP_CHAIN_ID=8453  # Base Mainnet

# Contract Addresses
REACT_APP_UNISWAP_V2_ROUTER=0x...
REACT_APP_UNISWAP_V3_ROUTER=0x...
REACT_APP_PANCAKESWAP_V2_ROUTER=0x...
REACT_APP_PANCAKESWAP_V3_ROUTER=0x...
EOL

# Make the script executable
chmod +x setup.sh

echo "Setup complete! Run 'npm start' to start the development server."
echo "Don't forget to:"
echo "1. Update the RPC URL with your Alchemy API key"
echo "2. Update the router contract addresses"
echo "3. Configure your production environment variables"