const hre = require("hardhat");

async function main() {
    // Contract deployment parameters
    const POOL_ADDRESS_PROVIDER = "0x0000000000000000000000000000000000000000"; // Replace with actual address
    const FLASHBOTS_RELAY = "0x0000000000000000000000000000000000000000"; // Replace with actual address
    const MAX_GAS_PRICE = ethers.utils.parseUnits("50", "gwei"); // 50 gwei max
    const MIN_PROFIT_BASIS_POINTS = 50; // 0.5%
    const MAX_TRADE_SIZE = ethers.utils.parseEther("1.0"); // 1 ETH max trade size

    console.log("Deploying MEVProtectedArbitrage...");

    // Deploy MEVProtectedArbitrage
    const MEVProtectedArbitrage = await hre.ethers.getContractFactory("MEVProtectedArbitrage");
    const mevProtectedArbitrage = await MEVProtectedArbitrage.deploy(
        POOL_ADDRESS_PROVIDER,
        FLASHBOTS_RELAY,
        MAX_GAS_PRICE,
        MIN_PROFIT_BASIS_POINTS,
        MAX_TRADE_SIZE
    );

    await mevProtectedArbitrage.deployed();

    console.log("MEVProtectedArbitrage deployed to:", mevProtectedArbitrage.address);

    // Set token addresses
    const WETH = "0x4200000000000000000000000000000000000006"; // Base WETH
    const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // Base USDC

    console.log("Setting token addresses...");
    await mevProtectedArbitrage.setTokenAddresses(WETH, USDC);

    // Verify contract on Etherscan
    console.log("Verifying contract on Etherscan...");
    await hre.run("verify:verify", {
        address: mevProtectedArbitrage.address,
        constructorArguments: [
            POOL_ADDRESS_PROVIDER,
            FLASHBOTS_RELAY,
            MAX_GAS_PRICE,
            MIN_PROFIT_BASIS_POINTS,
            MAX_TRADE_SIZE
        ],
    });

    console.log("Deployment and verification complete!");

    // Log deployment details
    const deploymentDetails = {
        contract: "MEVProtectedArbitrage",
        address: mevProtectedArbitrage.address,
        network: hre.network.name,
        parameters: {
            poolAddressProvider: POOL_ADDRESS_PROVIDER,
            flashbotsRelay: FLASHBOTS_RELAY,
            maxGasPrice: MAX_GAS_PRICE.toString(),
            minProfitBasisPoints: MIN_PROFIT_BASIS_POINTS,
            maxTradeSize: MAX_TRADE_SIZE.toString(),
            weth: WETH,
            usdc: USDC
        }
    };

    // Save deployment details to file
    const fs = require("fs");
    fs.writeFileSync(
        "deployment-details.json",
        JSON.stringify(deploymentDetails, null, 2)
    );

    console.log("Deployment details saved to deployment-details.json");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });