require("@nomiclabs/hardhat-ethers");
require("@nomiclabs/hardhat-etherscan");
require('dotenv').config();

// Load environment variables
const PRIVATE_KEY = process.env.PRIVATE_KEY;
const WALLET_ADDRESS = process.env.WALLET_ADDRESS;
const BASE_RPC_URL = process.env.BASE_RPC_URL;
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY;

// Validate required environment variables
if (!PRIVATE_KEY || !WALLET_ADDRESS || !BASE_RPC_URL) {
    console.error("Missing required environment variables:");
    console.error("- PRIVATE_KEY:", PRIVATE_KEY ? "Set" : "Missing");
    console.error("- WALLET_ADDRESS:", WALLET_ADDRESS ? "Set" : "Missing");
    console.error("- BASE_RPC_URL:", BASE_RPC_URL ? "Set" : "Missing");
    process.exit(1);
}

// Log configuration
console.log("Config loaded with:");
console.log("- Network: Base");
console.log(`- RPC URL: ${BASE_RPC_URL}`);
console.log(`- Wallet Address: ${WALLET_ADDRESS}`);

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
    solidity: {
        version: "0.8.28",
        settings: {
            optimizer: {
                enabled: true,
                runs: 200
            }
        }
    },
    networks: {
        hardhat: {
            chainId: 31337
        },
        base: {
            url: BASE_RPC_URL,
            accounts: [PRIVATE_KEY], // Use private key directly without 0x prefix
            chainId: 8453,
            gasPrice: "auto",
            verify: {
                etherscan: {
                    apiKey: ETHERSCAN_API_KEY
                }
            }
        }
    },
    etherscan: {
        apiKey: {
            base: ETHERSCAN_API_KEY
        },
        customChains: [
            {
                network: "base",
                chainId: 8453,
                urls: {
                    apiURL: "https://api.basescan.org/api",
                    browserURL: "https://basescan.org"
                }
            }
        ]
    },
    paths: {
        sources: "./contracts",
        tests: "./test",
        cache: "./cache",
        artifacts: "./artifacts"
    },
    mocha: {
        timeout: 60000
    }
};
