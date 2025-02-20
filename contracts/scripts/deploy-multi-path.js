const hre = require("hardhat");
require('dotenv').config();

async function main() {
    console.log("\n=== Starting Deployment ===\n");

    // Use the same pool address provider from the previous deployment
    const POOL_ADDRESS_PROVIDER = "0xe20fCBdBfFC4Dd138cE8b2E6FBb6CB49777ad64D";
    const PROFIT_RECIPIENT = "0x257a30645bF0C91BC155bd9C01BD722322050F7b";

    console.log("Deploying MultiPathArbitrage...");

    // Get signer from Hardhat's network configuration
    const [deployer] = await hre.ethers.getSigners();
    
    console.log("Deployment Configuration:");
    console.log("- Network:", hre.network.name);
    console.log("- Chain ID:", hre.network.config.chainId);
    console.log("- Deployer Address:", deployer.address);
    
    // Verify we're using the correct account
    if (deployer.address.toLowerCase() !== process.env.WALLET_ADDRESS.toLowerCase()) {
        throw new Error(`Wrong deployer address! Expected ${process.env.WALLET_ADDRESS} but got ${deployer.address}`);
    }
    
    // Get and log balance
    const balance = await deployer.getBalance();
    console.log("- Wallet Balance:", hre.ethers.utils.formatEther(balance), "ETH");

    // Get current gas price and add 20% buffer
    const gasPrice = await hre.ethers.provider.getGasPrice();
    const adjustedGasPrice = gasPrice.mul(120).div(100);
    console.log("- Current Gas Price:", hre.ethers.utils.formatUnits(gasPrice, "gwei"), "gwei");
    console.log("- Adjusted Gas Price:", hre.ethers.utils.formatUnits(adjustedGasPrice, "gwei"), "gwei");

    // Estimate deployment cost
    const Factory = await hre.ethers.getContractFactory("MultiPathArbitrage");
    const deploymentData = Factory.getDeployTransaction(POOL_ADDRESS_PROVIDER);
    const estimatedGas = await hre.ethers.provider.estimateGas({
        data: deploymentData.data,
        from: deployer.address
    });
    
    const estimatedCost = estimatedGas.mul(adjustedGasPrice);
    console.log("- Estimated Gas:", estimatedGas.toString());
    console.log("- Estimated Cost:", hre.ethers.utils.formatEther(estimatedCost), "ETH");

    // Check if we have enough balance
    if (balance.lt(estimatedCost)) {
        throw new Error(`Insufficient balance for deployment. Need ${hre.ethers.utils.formatEther(estimatedCost)} ETH but have ${hre.ethers.utils.formatEther(balance)} ETH`);
    }

    console.log("\nDeploying contract...");
    const MultiPathArbitrage = await Factory.deploy(POOL_ADDRESS_PROVIDER, {
        gasLimit: estimatedGas,
        gasPrice: adjustedGasPrice
    });
    
    console.log("Deployment transaction sent:", MultiPathArbitrage.deployTransaction.hash);
    console.log("Waiting for confirmation...");
    
    await MultiPathArbitrage.deployed();
    console.log("Contract deployed to:", MultiPathArbitrage.address);

    // Set profit recipient
    console.log("\nSetting profit recipient...");
    const setProfitRecipientTx = await MultiPathArbitrage.setProfitRecipient(
        PROFIT_RECIPIENT,
        {
            gasLimit: 200000,
            gasPrice: adjustedGasPrice
        }
    );
    console.log("Setting profit recipient tx:", setProfitRecipientTx.hash);
    await setProfitRecipientTx.wait();
    console.log("Profit recipient set to:", PROFIT_RECIPIENT);

    // Verify contract on Etherscan
    console.log("\nVerifying contract on Etherscan...");
    try {
        await hre.run("verify:verify", {
            address: MultiPathArbitrage.address,
            constructorArguments: [POOL_ADDRESS_PROVIDER],
        });
        console.log("Contract verified successfully");
    } catch (error) {
        console.error("Contract verification failed:", error.message);
    }

    // Log deployment details
    const deploymentDetails = {
        contract: "MultiPathArbitrage",
        address: MultiPathArbitrage.address,
        network: hre.network.name,
        chainId: hre.network.config.chainId,
        deployer: deployer.address,
        deployerBalance: hre.ethers.utils.formatEther(balance),
        parameters: {
            poolAddressProvider: POOL_ADDRESS_PROVIDER,
            profitRecipient: PROFIT_RECIPIENT
        },
        transactions: {
            deployment: MultiPathArbitrage.deployTransaction.hash,
            setProfitRecipient: setProfitRecipientTx.hash
        },
        gasUsed: {
            deployment: estimatedGas.toString(),
            gasPrice: hre.ethers.utils.formatUnits(adjustedGasPrice, "gwei")
        },
        timestamp: new Date().toISOString()
    };

    // Save deployment details to file
    const fs = require("fs");
    fs.writeFileSync(
        "multi-path-deployment-details.json",
        JSON.stringify(deploymentDetails, null, 2)
    );

    console.log("\nDeployment details saved to multi-path-deployment-details.json");
    console.log("\n=== Deployment Complete ===\n");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("\nDeployment failed:", error);
        process.exit(1);
    });