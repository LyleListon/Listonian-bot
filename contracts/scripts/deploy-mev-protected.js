const hre = require("hardhat");
const fs = require("fs");

async function main() {
    console.log("\nStarting deployment process...");
    console.log("Current directory:", process.cwd());

    try {
        // Get deployer account
        const [deployer] = await hre.ethers.getSigners();
        console.log(`\nDeploying with account: ${deployer.address}`);
        
        // Get current nonce
        const nonce = await deployer.getNonce();
        console.log(`Current nonce: ${nonce}`);

        const balance = await deployer.provider.getBalance(deployer.address);
        console.log(`Account balance: ${hre.ethers.formatEther(balance)} ETH`);

        if (balance === 0n) {
            throw new Error("Deployer account has no ETH");
        }

        // Get current gas price and add 20%
        const feeData = await deployer.provider.getFeeData();
        const gasPrice = (feeData.gasPrice * 120n) / 100n;
        console.log(`Current network gas price: ${hre.ethers.formatUnits(feeData.gasPrice, "gwei")} gwei`);
        console.log(`Using gas price: ${hre.ethers.formatUnits(gasPrice, "gwei")} gwei`);

        // Contract deployment parameters
        const POOL_ADDRESS_PROVIDER = "0xe20fCBdBfFC4Dd138cE8b2E6FBb6CB49777ad64D";
        const FLASHBOTS_RELAY = "0x0000000000000000000000000000000000000000"; // No Flashbots on Base yet
        const MAX_GAS_PRICE = hre.ethers.parseUnits("50", "gwei");
        const MIN_PROFIT_BASIS_POINTS = 50; // 0.5%
        const MAX_TRADE_SIZE = hre.ethers.parseEther("1.0");
        const PROFIT_RECIPIENT = "0x257a30645bF0C91BC155bd9C01BD722322050F7b";

        console.log("\nDeployment parameters:");
        console.log(`- Pool Address Provider: ${POOL_ADDRESS_PROVIDER}`);
        console.log(`- Flashbots Relay: ${FLASHBOTS_RELAY}`);
        console.log(`- Max Gas Price: ${hre.ethers.formatUnits(MAX_GAS_PRICE, "gwei")} gwei`);
        console.log(`- Min Profit Basis Points: ${MIN_PROFIT_BASIS_POINTS}`);
        console.log(`- Max Trade Size: ${hre.ethers.formatEther(MAX_TRADE_SIZE)} ETH`);
        console.log(`- Profit Recipient: ${PROFIT_RECIPIENT}`);

        // Cancel any pending transactions
        console.log("\nCancelling any pending transactions...");
        const cancelTx = await deployer.sendTransaction({
            to: deployer.address,
            value: 0,
            nonce: nonce,
            gasPrice: gasPrice,
            gasLimit: 21000
        });
        await cancelTx.wait();
        console.log("Pending transactions cancelled");

        // Deploy MEVProtectedArbitrage
        console.log("\nCreating contract factory...");
        const MEVProtectedArbitrage = await hre.ethers.getContractFactory("MEVProtectedArbitrage");

        console.log("Deploying contract...");
        const deploymentOptions = {
            gasLimit: 5000000,
            gasPrice: gasPrice,
            nonce: nonce + 1
        };
        console.log("Deployment options:", deploymentOptions);

        const mevProtectedArbitrage = await MEVProtectedArbitrage.deploy(
            POOL_ADDRESS_PROVIDER,
            FLASHBOTS_RELAY,
            MAX_GAS_PRICE,
            MIN_PROFIT_BASIS_POINTS,
            MAX_TRADE_SIZE,
            deploymentOptions
        );

        console.log(`Deployment transaction hash: ${mevProtectedArbitrage.deploymentTransaction().hash}`);
        console.log("Waiting for deployment to be mined...");

        await mevProtectedArbitrage.waitForDeployment();
        const receipt = await mevProtectedArbitrage.deploymentTransaction().wait();
        
        console.log(`Contract deployed to: ${await mevProtectedArbitrage.getAddress()}`);
        console.log(`Deployment confirmed in block ${receipt.blockNumber}`);
        console.log(`Gas used: ${receipt.gasUsed.toString()}`);

        // Set token addresses
        const WETH = "0x4200000000000000000000000000000000000006"; // Base WETH
        const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // Base USDC

        console.log("\nSetting token addresses...");
        const setTokensTx = await mevProtectedArbitrage.setTokenAddresses(
            WETH, 
            USDC,
            {
                gasLimit: 200000,
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
            PROFIT_RECIPIENT,
            {
                gasLimit: 200000,
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
            address: await mevProtectedArbitrage.getAddress(),
            deploymentTx: mevProtectedArbitrage.deploymentTransaction().hash,
            deploymentBlock: receipt.blockNumber,
            parameters: {
                poolAddressProvider: POOL_ADDRESS_PROVIDER,
                flashbotsRelay: FLASHBOTS_RELAY,
                maxGasPrice: hre.ethers.formatUnits(MAX_GAS_PRICE, "gwei"),
                minProfitBasisPoints: MIN_PROFIT_BASIS_POINTS,
                maxTradeSize: hre.ethers.formatEther(MAX_TRADE_SIZE),
                weth: WETH,
                usdc: USDC,
                profitRecipient: PROFIT_RECIPIENT
            },
            costs: {
                deploymentGasUsed: receipt.gasUsed.toString(),
                tokenSettingGasUsed: setTokensReceipt.gasUsed.toString(),
                profitRecipientGasUsed: setProfitRecipientReceipt.gasUsed.toString(),
                effectiveGasPrice: hre.ethers.formatUnits(gasPrice, "gwei"),
                totalCost: hre.ethers.formatEther(
                    (receipt.gasUsed * receipt.gasPrice) + 
                    (setTokensReceipt.gasUsed * setTokensReceipt.gasPrice) +
                    (setProfitRecipientReceipt.gasUsed * setProfitRecipientReceipt.gasPrice)
                )
            },
            timestamp: new Date().toISOString()
        };

        fs.writeFileSync(
            "deployment-details.json",
            JSON.stringify(deploymentDetails, null, 2)
        );

        console.log("\nDeployment details saved to deployment-details.json");
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