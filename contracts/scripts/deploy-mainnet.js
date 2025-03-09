const hre = require("hardhat");
const { ethers } = require("ethers");

async function main() {
    console.log("\nStarting mainnet deployment process...");
    console.log("Current directory:", process.cwd());

    try {
        // Get deployer account
        const [deployer] = await hre.ethers.getSigners();
        console.log(`\nDeploying with account: ${deployer.address}`);
        
        // Get current nonce and balance
        const provider = await hre.ethers.provider;
        const nonce = await provider.getTransactionCount(deployer.address);
        console.log(`Current nonce: ${nonce}`);

        const balance = await provider.getBalance(deployer.address);
        const balanceEth = ethers.formatEther(balance);
        console.log(`Account balance: ${balanceEth} ETH`);

        if (balance === 0n) {
            throw new Error("Deployer account has no ETH");
        }

        // Get current gas price and add 20%
        const feeData = await provider.getFeeData();
        const gasPrice = (feeData.gasPrice * 120n) / 100n;
        console.log(`Current network gas price: ${ethers.formatUnits(feeData.gasPrice, "gwei")} gwei`);
        console.log(`Using gas price: ${ethers.formatUnits(gasPrice, "gwei")} gwei`);

        // Contract deployment parameters
        const AAVE_POOL_ADDRESS_PROVIDER = "0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e"; // Mainnet Aave v3
        const FLASHBOTS_RELAY = "0xDAFEA492D9c6733ae3d56b7Ed1ADB60692c98Bc5"; // Mainnet Flashbots Relay
        const MAX_GAS_PRICE = ethers.parseUnits("150", "gwei"); // Higher for mainnet
        const MIN_PROFIT_BASIS_POINTS = 50; // 0.5%
        const MAX_TRADE_SIZE = ethers.parseEther("5.0"); // 5 ETH max per trade

        console.log("\nDeployment parameters:");
        console.log(`- Aave Pool Address Provider: ${AAVE_POOL_ADDRESS_PROVIDER}`);
        console.log(`- Flashbots Relay: ${FLASHBOTS_RELAY}`);
        console.log(`- Max Gas Price: ${ethers.formatUnits(MAX_GAS_PRICE, "gwei")} gwei`);
        console.log(`- Min Profit Basis Points: ${MIN_PROFIT_BASIS_POINTS}`);
        console.log(`- Max Trade Size: ${ethers.formatEther(MAX_TRADE_SIZE)} ETH`);

        // Cancel any pending transactions
        console.log("\nCancelling any pending transactions...");
        const cancelTx = await deployer.sendTransaction({
            to: deployer.address,
            value: 0n,
            nonce: nonce,
            gasPrice: gasPrice,
            gasLimit: 21000n
        });
        await cancelTx.wait();
        console.log("Pending transactions cancelled");

        // Deploy MEVProtectedArbitrage
        console.log("\nCreating contract factory...");
        const MEVProtectedArbitrage = await hre.ethers.getContractFactory("MEVProtectedArbitrage");

        console.log("Deploying contract...");
        const deploymentOptions = {
            gasLimit: 5000000n,
            gasPrice: gasPrice,
            nonce: nonce + 1
        };
        console.log("Deployment options:", deploymentOptions);

        const mevProtectedArbitrage = await MEVProtectedArbitrage.deploy(
            AAVE_POOL_ADDRESS_PROVIDER,
            FLASHBOTS_RELAY,
            MAX_GAS_PRICE,
            MIN_PROFIT_BASIS_POINTS,
            MAX_TRADE_SIZE,
            deploymentOptions
        );

        console.log(`Deployment transaction hash: ${mevProtectedArbitrage.deployTransaction.hash}`);
        console.log("Waiting for deployment to be mined...");

        await mevProtectedArbitrage.waitForDeployment();
        const receipt = await provider.getTransactionReceipt(mevProtectedArbitrage.deployTransaction.hash);
        
        console.log(`Contract deployed to: ${await mevProtectedArbitrage.getAddress()}`);
        console.log(`Deployment confirmed in block ${receipt.blockNumber}`);
        console.log(`Gas used: ${receipt.gasUsed.toString()}`);

        // Set token addresses
        const WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"; // Mainnet WETH
        const USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"; // Mainnet USDC

        console.log("\nSetting token addresses...");
        const setTokensTx = await mevProtectedArbitrage.setTokenAddresses(
            WETH, 
            USDC,
            {
                gasLimit: 200000n,
                gasPrice: gasPrice,
                nonce: nonce + 2
            }
        );
        console.log(`Token addresses transaction hash: ${setTokensTx.hash}`);
        
        const setTokensReceipt = await setTokensTx.wait();
        console.log(`Token addresses set in block ${setTokensReceipt.blockNumber}`);
        console.log(`Gas used for token setting: ${setTokensReceipt.gasUsed.toString()}`);

        // Set profit recipient
        console.log("\nSetting profit recipient...");
        const setProfitRecipientTx = await mevProtectedArbitrage.setProfitRecipient(
            deployer.address, // Set deployer as profit recipient
            {
                gasLimit: 200000n,
                gasPrice: gasPrice,
                nonce: nonce + 3
            }
        );
        console.log(`Profit recipient transaction hash: ${setProfitRecipientTx.hash}`);
        
        const setProfitRecipientReceipt = await setProfitRecipientTx.wait();
        console.log(`Profit recipient set in block ${setProfitRecipientReceipt.blockNumber}`);
        console.log(`Gas used for profit recipient setting: ${setProfitRecipientReceipt.gasUsed.toString()}`);

        // Save deployment details
        const deploymentDetails = {
            contract: "MEVProtectedArbitrage",
            network: "mainnet",
            address: await mevProtectedArbitrage.getAddress(),
            deploymentTx: mevProtectedArbitrage.deployTransaction.hash,
            deploymentBlock: receipt.blockNumber,
            parameters: {
                poolAddressProvider: AAVE_POOL_ADDRESS_PROVIDER,
                flashbotsRelay: FLASHBOTS_RELAY,
                maxGasPrice: ethers.formatUnits(MAX_GAS_PRICE, "gwei"),
                minProfitBasisPoints: MIN_PROFIT_BASIS_POINTS,
                maxTradeSize: ethers.formatEther(MAX_TRADE_SIZE),
                weth: WETH,
                usdc: USDC,
                profitRecipient: deployer.address
            },
            costs: {
                deploymentGasUsed: receipt.gasUsed.toString(),
                tokenSettingGasUsed: setTokensReceipt.gasUsed.toString(),
                profitRecipientGasUsed: setProfitRecipientReceipt.gasUsed.toString(),
                effectiveGasPrice: ethers.formatUnits(gasPrice, "gwei"),
                totalCost: ethers.formatEther(
                    (receipt.gasUsed * receipt.gasPrice) + 
                    (setTokensReceipt.gasUsed * setTokensReceipt.gasPrice) +
                    (setProfitRecipientReceipt.gasUsed * setProfitRecipientReceipt.gasPrice)
                )
            },
            timestamp: new Date().toISOString()
        };

        const fs = require('fs');
        fs.writeFileSync(
            "mainnet-deployment-details.json",
            JSON.stringify(deploymentDetails, null, 2)
        );

        console.log("\nDeployment details saved to mainnet-deployment-details.json");
        console.log("Deployment complete!");

    } catch (error) {
        console.error("\nDeployment failed with error:", error);
        if (error.code) console.error("Error code:", error.code);
        if (error.reason) console.error("Error reason:", error.reason);
        if (error.transaction) console.error("Error transaction:", error.transaction);
        if (error.receipt) console.error("Error receipt:", error.receipt);
        if (error.data) console.error("Error data:", error.data);
        process.exit(1);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("\nUnhandled error:", error);
        process.exit(1);
    });