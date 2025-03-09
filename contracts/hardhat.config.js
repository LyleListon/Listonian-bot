require("@nomiclabs/hardhat-ethers");
require("@nomiclabs/hardhat-etherscan");
require('dotenv').config();

// Load environment variables
const PRIVATE_KEY = process.env.WALLET_PRIVATE_KEY;
const WALLET_ADDRESS = process.env.WALLET_ADDRESS;
const MAINNET_RPC_URL = process.env.ALCHEMY_API_URL;
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY;

// Validate required environment variables
if (!PRIVATE_KEY || !WALLET_ADDRESS || !MAINNET_RPC_URL) {
    console.error("Missing required environment variables:");
    console.error("- WALLET_PRIVATE_KEY:", PRIVATE_KEY ? "Set" : "Missing");
    console.error("- WALLET_ADDRESS:", WALLET_ADDRESS ? "Set" : "Missing");
    console.error("- ALCHEMY_API_URL:", MAINNET_RPC_URL ? "Set" : "Missing");
    process.exit(1);
}

// Log configuration
console.log("Config loaded with:");
console.log("- Network: Ethereum Mainnet");
console.log(`- RPC URL: ${MAINNET_RPC_URL}`);
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
            chainId: 1,
            forking: {
                url: MAINNET_RPC_URL,
                blockNumber: 19500000 // Recent mainnet block
            }
        },
        mainnet: {
            url: MAINNET_RPC_URL,
            accounts: [PRIVATE_KEY],
            chainId: 1,
            gasPrice: "auto",
            verify: {
                etherscan: {
                    apiKey: ETHERSCAN_API_KEY
                }
            }
        }
    },
    etherscan: {
        apiKey: ETHERSCAN_API_KEY
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
