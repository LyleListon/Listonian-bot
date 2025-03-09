const hre = require("hardhat");

async function main() {
    try {
        console.log("\n=== Starting Simple Deployment ===\n");

        // Create wallet from private key
        const provider = new hre.ethers.providers.JsonRpcProvider(process.env.BASE_RPC_URL);
        const wallet = new hre.ethers.Wallet(process.env.PRIVATE_KEY, provider);
        
        console.log("Network:", await provider.getNetwork().then(n => `${n.name} (${n.chainId})`));
        console.log("Deploying with account:", wallet.address);
        
        // Verify it matches our expected wallet
        if (wallet.address.toLowerCase() !== process.env.WALLET_ADDRESS.toLowerCase()) {
            throw new Error(`Wrong wallet address! Expected ${process.env.WALLET_ADDRESS} but got ${wallet.address}`);
        }

        const balance = await wallet.getBalance();
        console.log("Balance:", hre.ethers.utils.formatEther(balance), "ETH");

        // Pool address provider for Base mainnet
        const POOL_ADDRESS_PROVIDER = "0xe20fCBdBfFC4Dd138cE8b2E6FBb6CB49777ad64D";
        console.log("\nPool Address Provider:", POOL_ADDRESS_PROVIDER);

        // Get contract factory connected to our wallet
        console.log("\nDeploying MultiPathArbitrage...");
        const Factory = await hre.ethers.getContractFactory("MultiPathArbitrage", wallet);
        
        // Get current gas price and add 20% buffer
        const gasPrice = await provider.getGasPrice();
        const adjustedGasPrice = gasPrice.mul(120).div(100);
        console.log("Using gas price:", hre.ethers.utils.formatUnits(adjustedGasPrice, "gwei"), "gwei");

        // Deploy with explicit transaction parameters
        const contract = await Factory.deploy(POOL_ADDRESS_PROVIDER, {
            gasPrice: adjustedGasPrice,
            gasLimit: 3000000, // Fixed gas limit
            nonce: await wallet.getTransactionCount()
        });
        
        console.log("Deployment transaction sent:", contract.deployTransaction.hash);
        console.log("Waiting for confirmation...");
        
        await contract.deployed();
        console.log("\nContract deployed to:", contract.address);

        // Save deployment details
        const deploymentDetails = {
            contract: "MultiPathArbitrage",
            address: contract.address,
            network: await provider.getNetwork().then(n => n.name),
            chainId: await provider.getNetwork().then(n => n.chainId),
            deployer: wallet.address,
            deployerBalance: hre.ethers.utils.formatEther(balance),
            poolAddressProvider: POOL_ADDRESS_PROVIDER,
            deploymentTx: contract.deployTransaction.hash,
            timestamp: new Date().toISOString()
        };

        require('fs').writeFileSync(
            "multi-path-deployment-details.json",
            JSON.stringify(deploymentDetails, null, 2)
        );

        console.log("\nDeployment details saved to multi-path-deployment-details.json");
        console.log("\n=== Deployment Complete ===\n");
    } catch (error) {
        console.error("\nDeployment failed!");
        console.error("Error:", error.message);
        if (error.error) {
            console.error("Provider error:", error.error);
        }
        if (error.transaction) {
            console.error("Transaction:", error.transaction);
        }
        throw error;
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });