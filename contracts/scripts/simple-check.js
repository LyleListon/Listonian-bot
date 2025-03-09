console.log("Starting simple check...");

try {
    require('dotenv').config();
    console.log("\nEnvironment variables:");
    console.log("WALLET_ADDRESS exists:", !!process.env.WALLET_ADDRESS);
    console.log("PRIVATE_KEY exists:", !!process.env.PRIVATE_KEY);
    console.log("BASE_RPC_URL exists:", !!process.env.BASE_RPC_URL);
    
    if (process.env.WALLET_ADDRESS) {
        console.log("\nWallet address:", process.env.WALLET_ADDRESS);
    }
    
    console.log("\nCheck complete!");
} catch (error) {
    console.error("Error during check:", error);
}