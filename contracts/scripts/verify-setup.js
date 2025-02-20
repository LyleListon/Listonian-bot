const { ethers } = require('ethers');
require('dotenv').config();

function log(...args) {
    console.log(...args);
    process.stdout.write(args.join(' ') + '\n');
}

async function main() {
    try {
        log("\n=== Verifying Setup ===\n");

        // 1. Check environment variables
        log("Environment Variables:");
        const PRIVATE_KEY = process.env.PRIVATE_KEY;
        const WALLET_ADDRESS = process.env.WALLET_ADDRESS;
        const BASE_RPC_URL = process.env.BASE_RPC_URL;
        
        log("- PRIVATE_KEY:", PRIVATE_KEY ? `Set (${PRIVATE_KEY.slice(0, 6)}...)` : "Missing");
        log("- WALLET_ADDRESS:", WALLET_ADDRESS || "Missing");
        log("- BASE_RPC_URL:", BASE_RPC_URL ? "Set" : "Missing");

        if (!PRIVATE_KEY || !WALLET_ADDRESS || !BASE_RPC_URL) {
            throw new Error("Missing required environment variables");
        }

        // 2. Test RPC Connection
        log("\nTesting RPC Connection:");
        const provider = new ethers.providers.JsonRpcProvider(BASE_RPC_URL);
        const network = await provider.getNetwork();
        log("- Network Name:", network.name);
        log("- Chain ID:", network.chainId);
        const blockNumber = await provider.getBlockNumber();
        log("- Latest Block:", blockNumber);

        // 3. Verify Wallet
        log("\nVerifying Wallet:");
        const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
        log("- Derived Address:", wallet.address);
        const addressMatch = wallet.address.toLowerCase() === WALLET_ADDRESS.toLowerCase();
        log("- Matches Expected:", addressMatch);
        
        if (!addressMatch) {
            throw new Error(`Wallet address mismatch! Expected ${WALLET_ADDRESS} but got ${wallet.address}`);
        }
        
        const balance = await wallet.getBalance();
        log("- Balance:", ethers.utils.formatEther(balance), "ETH");

        // 4. Check Gas Prices
        log("\nChecking Gas Prices:");
        const gasPrice = await provider.getGasPrice();
        log("- Current Gas Price:", ethers.utils.formatUnits(gasPrice, "gwei"), "gwei");
        
        // 5. Estimate Deployment Costs
        log("\nEstimating Deployment Costs:");
        const estimatedGas = 3000000; // Conservative estimate
        const estimatedCost = gasPrice.mul(estimatedGas);
        log("- Estimated Gas:", estimatedGas);
        log("- Estimated Cost:", ethers.utils.formatEther(estimatedCost), "ETH");
        const hasSufficientFunds = balance.gt(estimatedCost);
        log("- Has Sufficient Funds:", hasSufficientFunds ? "Yes" : "No");

        if (!hasSufficientFunds) {
            throw new Error(`Insufficient funds. Need ${ethers.utils.formatEther(estimatedCost)} ETH but have ${ethers.utils.formatEther(balance)} ETH`);
        }

        log("\n=== Setup Verification Complete ===\n");

        return {
            success: true,
            wallet,
            provider,
            gasPrice,
            balance
        };
    } catch (error) {
        log("\nVerification Failed!");
        log("Error:", error.message);
        throw error;
    }
}

if (require.main === module) {
    main()
        .then(() => process.exit(0))
        .catch((error) => {
            console.error("\nFatal Error:", error);
            process.exit(1);
        });
}

module.exports = main;