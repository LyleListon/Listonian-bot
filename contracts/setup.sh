#!/bin/bash

# Install dependencies
npm install

# Install specific OpenZeppelin version
npm install @openzeppelin/contracts@4.9.3

# Install Hardhat and plugins
npm install --save-dev hardhat @nomiclabs/hardhat-ethers @nomiclabs/hardhat-waffle ethereum-waffle chai ethers@^5.7.2 @nomiclabs/hardhat-etherscan dotenv

# Create contracts directory if it doesn't exist
mkdir -p contracts

# Create scripts directory if it doesn't exist
mkdir -p scripts

# Initialize Git ignore
echo "node_modules
.env
coverage
coverage.json
typechain
typechain-types
deployments
cache
artifacts" > .gitignore

# Create sample .env file
echo "PRIVATE_KEY=your_private_key_here
ALCHEMY_API_KEY=your_alchemy_api_key_here
FLASHBOTS_RELAY=your_flashbots_relay_here
ETHERSCAN_API_KEY=your_etherscan_api_key_here" > .env.example

echo "Setup complete! Please:"
echo "1. Copy .env.example to .env"
echo "2. Fill in your private key and API keys in .env"
echo "3. Run 'npx hardhat compile' to compile contracts"
echo "4. Run 'npx hardhat run scripts/deploy.js --network base' to deploy"