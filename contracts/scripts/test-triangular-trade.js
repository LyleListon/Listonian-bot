const hre = require("hardhat");
const fs = require("fs");

// Token addresses on Base network
const TOKENS = {
    WETH: "0x4200000000000000000000000000000000000006",
    USDC: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    USDT: "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
};

// DEX router addresses
const ROUTERS = {
    baseswap: {
        address: "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
        isV3: false,
        fee: 0
    },
    aerodrome: {
        address: "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
        isV3: false,
        fee: 0
    },
    swapbased: {
        address: "0xeaf1ac8E89EA0aE13E0f03634A4FF23502527024",
        isV3: true,
        fee: 500 // 0.05%
    }
};

async function main() {
    try {
        // Load contract details
        let deploymentDetails;
        try {
            deploymentDetails = JSON.parse(fs.readFileSync('multi-path-deployment-details.json'));
            console.log("Found existing deployment:", deploymentDetails.address);
        } catch (e) {
            console.log("No existing deployment found, deploying new contract...");
            
            // Deploy new contract
            const POOL_ADDRESS_PROVIDER = "0xe20fCBdBfFC4Dd138cE8b2E6FBb6CB49777ad64D";
            const Factory = await hre.ethers.getContractFactory("MultiPathArbitrage");
            const contract = await Factory.deploy(POOL_ADDRESS_PROVIDER);
            await contract.deployed();
            console.log("Deployed new contract to:", contract.address);
            
            deploymentDetails = {
                address: contract.address
            };
        }

        // Connect to contract
        const contract = await hre.ethers.getContractAt(
            "MultiPathArbitrage",
            deploymentDetails.address
        );
        
        // Set up trade steps
        const tradeSteps = [
            {
                router: ROUTERS.baseswap.address,
                path: [TOKENS.WETH, TOKENS.USDC],
                isV3: ROUTERS.baseswap.isV3,
                amount: hre.ethers.utils.parseEther("0.1"), // Start with 0.1 WETH
                fee: ROUTERS.baseswap.fee
            },
            {
                router: ROUTERS.aerodrome.address,
                path: [TOKENS.USDC, TOKENS.USDT],
                isV3: ROUTERS.aerodrome.isV3,
                amount: 0, // Will be set by previous trade
                fee: ROUTERS.aerodrome.fee
            },
            {
                router: ROUTERS.swapbased.address,
                path: [TOKENS.USDT, TOKENS.WETH],
                isV3: ROUTERS.swapbased.isV3,
                amount: 0, // Will be set by previous trade
                fee: ROUTERS.swapbased.fee
            }
        ];

        // Get current gas price and add 20% buffer
        const gasPrice = await hre.ethers.provider.getGasPrice();
        const adjustedGasPrice = gasPrice.mul(120).div(100);
        console.log(`Using gas price: ${hre.ethers.utils.formatUnits(adjustedGasPrice, "gwei")} gwei`);

        // Execute flash loan with trade steps
        console.log("Executing triangular arbitrage...");
        console.log("Trade path: WETH → USDC → USDT → WETH");
        console.log("Initial amount:", hre.ethers.utils.formatEther(tradeSteps[0].amount), "WETH");
        
        const tx = await contract.executeFlashLoan(
            TOKENS.WETH,
            tradeSteps[0].amount,
            tradeSteps,
            {
                gasLimit: 3000000,
                gasPrice: adjustedGasPrice
            }
        );

        console.log("Transaction sent:", tx.hash);
        console.log("Waiting for confirmation...");
        
        // Wait for transaction and get receipt
        const receipt = await tx.wait();
        
        // Parse events
        const profitEvent = receipt.events.find(e => e.event === "ProfitTransferred");
        if (profitEvent) {
            const profit = hre.ethers.utils.formatEther(profitEvent.args.amount);
            console.log("Trade successful!");
            console.log("Profit:", profit, "WETH");
        } else {
            console.log("Trade completed but no profit generated");
        }

        // Log gas used
        const gasUsed = receipt.gasUsed;
        const gasCost = gasUsed.mul(adjustedGasPrice);
        console.log("Gas used:", gasUsed.toString());
        console.log("Gas cost:", hre.ethers.utils.formatEther(gasCost), "ETH");

    } catch (error) {
        console.error("Error executing trade:", error);
        process.exit(1);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });