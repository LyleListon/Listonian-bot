const hre = require("hardhat");

async function main() {
    // Use the same pool address provider from the previous deployment
    const POOL_ADDRESS_PROVIDER = "0xe20fCBdBfFC4Dd138cE8b2E6FBb6CB49777ad64D";
    const PROFIT_RECIPIENT = "0x257a30645bF0C91BC155bd9C01BD722322050F7b";

    console.log("Deploying FlashLoanArbitrage...");

    // Deploy FlashLoanArbitrage
    const [deployer] = await hre.ethers.getSigners();
    console.log("Deploying with account:", deployer.address);

    const txCount = await deployer.getTransactionCount();
    console.log("Current nonce:", txCount);
    
    const balance = await deployer.getBalance();
    console.log("Deployer balance:", hre.ethers.utils.formatEther(balance), "ETH");

    // Get current gas price and add 20% buffer
    const gasPrice = await deployer.provider.getGasPrice();
    const adjustedGasPrice = gasPrice.mul(120).div(100);
    console.log(`Using gas price: ${hre.ethers.utils.formatUnits(adjustedGasPrice, "gwei")} gwei`);
    
    const Factory = await hre.ethers.getContractFactory("FlashLoanArbitrage");
    
    console.log("Deploying contract...");
    const FlashLoanArbitrage = await Factory.deploy(
        POOL_ADDRESS_PROVIDER,
        {
            nonce: txCount,
            gasLimit: 3000000,
            gasPrice: adjustedGasPrice
        }
    );
    
    console.log("Waiting for deployment transaction...");
    await FlashLoanArbitrage.deployed();
    console.log("FlashLoanArbitrage deployed to:", FlashLoanArbitrage.address);

    // Set token addresses (same as previous deployment)
    const WETH = "0x4200000000000000000000000000000000000006"; // Base WETH
    const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // Base USDC

    console.log("Setting token addresses...");
    const setTokensTx = await FlashLoanArbitrage.setTokenAddresses(
        WETH,
        USDC,
        {
            gasLimit: 200000,
            gasPrice: adjustedGasPrice,
            nonce: txCount + 1
        }
    );
    console.log("Waiting for token addresses transaction...");
    await setTokensTx.wait();
    console.log("Token addresses set");

    // Set profit recipient
    console.log("Setting profit recipient...");
    const setProfitRecipientTx = await FlashLoanArbitrage.setProfitRecipient(
        PROFIT_RECIPIENT,
        {
            gasLimit: 200000,
            gasPrice: adjustedGasPrice,
            nonce: txCount + 2
        }
    );
    console.log("Waiting for profit recipient transaction...");
    await setProfitRecipientTx.wait();
    console.log("Profit recipient set to:", PROFIT_RECIPIENT);

    // Verify contract on Etherscan
    console.log("Verifying contract on Etherscan...");
    await hre.run("verify:verify", {
        address: FlashLoanArbitrage.address,
        constructorArguments: [POOL_ADDRESS_PROVIDER],
    });

    console.log("Deployment and verification complete!");

    // Log deployment details
    const deploymentDetails = {
        contract: "FlashLoanArbitrage",
        address: FlashLoanArbitrage.address,
        network: hre.network.name,
        parameters: {
            poolAddressProvider: POOL_ADDRESS_PROVIDER,
            weth: WETH,
            usdc: USDC,
            profitRecipient: PROFIT_RECIPIENT
        },
        transactions: {
            deployment: FlashLoanArbitrage.deployTransaction.hash,
            setTokens: setTokensTx.hash,
            setProfitRecipient: setProfitRecipientTx.hash
        },
        timestamp: new Date().toISOString()
    };

    // Save deployment details to file
    const fs = require("fs");
    fs.writeFileSync(
        "flash-loan-deployment-details.json",
        JSON.stringify(deploymentDetails, null, 2)
    );

    console.log("Deployment details saved to flash-loan-deployment-details.json");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
