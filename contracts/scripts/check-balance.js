console.log("Script starting...");

const hre = require("hardhat");
console.log("Hardhat loaded");

require('dotenv').config();
console.log("dotenv loaded");

async function main() {
    try {
        console.log("\n=== Balance Check Starting ===");
        
        // Log environment variables
        console.log("\nEnvironment Check:");
        console.log("WALLET_ADDRESS:", process.env.WALLET_ADDRESS || "Not Set");
        console.log("BASE_RPC_URL:", process.env.BASE_RPC_URL ? "Set" : "Not Set");
        console.log("INFURA_RPC_URL:", process.env.INFURA_RPC_URL ? "Set" : "Not Set");
        console.log("PRIVATE_KEY:", process.env.PRIVATE_KEY ? "Set" : "Not Set");

        // Get wallet address
        const WALLET_ADDRESS = process.env.WALLET_ADDRESS;
        if (!WALLET_ADDRESS) {
            throw new Error("WALLET_ADDRESS not found in .env");
        }

        console.log("\nChecking Hardhat Network:");
        const config = hre.network.config;
        console.log("Current network:", hre.network.name);
        console.log("Network config:", JSON.stringify(config, null, 2));

        console.log("\nChecking Signer:");
        const [signer] = await hre.ethers.getSigners();
        console.log("Signer address:", signer.address);
        
        console.log("\nChecking Balances:");
        
        // Check balance using Hardhat provider
        const hardhatBalance = await signer.getBalance();
        console.log("\nHardhat Provider Balance:");
        console.log("Address:", signer.address);
        console.log("Balance (ETH):", hre.ethers.utils.formatEther(hardhatBalance));
        
        // Check balance using direct RPC calls
        console.log("\nDirect RPC Balance Checks:");
        
        // Alchemy
        try {
            const alchemyProvider = new hre.ethers.providers.JsonRpcProvider(process.env.BASE_RPC_URL);
            const alchemyBalance = await alchemyProvider.getBalance(WALLET_ADDRESS);
            console.log("\nAlchemy Balance:");
            console.log("Address:", WALLET_ADDRESS);
            console.log("Balance (ETH):", hre.ethers.utils.formatEther(alchemyBalance));
        } catch (error) {
            console.error("Alchemy balance check failed:", error.message);
        }

        // Infura
        try {
            const infuraProvider = new hre.ethers.providers.JsonRpcProvider(process.env.INFURA_RPC_URL);
            const infuraBalance = await infuraProvider.getBalance(WALLET_ADDRESS);
            console.log("\nInfura Balance:");
            console.log("Address:", WALLET_ADDRESS);
            console.log("Balance (ETH):", hre.ethers.utils.formatEther(infuraBalance));
        } catch (error) {
            console.error("Infura balance check failed:", error.message);
        }

        console.log("\n=== Balance Check Complete ===");

    } catch (error) {
        console.error("\nError in main function:", error);
        throw error;
    }
}

console.log("Calling main function...");

main()
    .then(() => {
        console.log("Script completed successfully");
        process.exit(0);
    })
    .catch((error) => {
        console.error("Script failed:", error);
        process.exit(1);
    });