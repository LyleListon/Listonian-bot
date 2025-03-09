const { ethers } = require('ethers');
const fs = require('fs');
require('dotenv').config();

async function main() {
    const results = {
        timestamp: new Date().toISOString(),
        steps: []
    };

    try {
        // Load and verify environment variables
        const { PRIVATE_KEY, WALLET_ADDRESS, BASE_RPC_URL } = process.env;
        
        if (!PRIVATE_KEY || !WALLET_ADDRESS || !BASE_RPC_URL) {
            throw new Error('Missing required environment variables');
        }

        // Create wallet
        const wallet = new ethers.Wallet(PRIVATE_KEY);
        results.steps.push({
            step: 'Wallet Creation',
            derived: wallet.address,
            expected: WALLET_ADDRESS,
            matches: wallet.address.toLowerCase() === WALLET_ADDRESS.toLowerCase()
        });

        // Connect to network
        const provider = new ethers.providers.JsonRpcProvider(BASE_RPC_URL);
        const connectedWallet = wallet.connect(provider);
        
        // Get network info
        const network = await provider.getNetwork();
        results.steps.push({
            step: 'Network Connection',
            name: network.name,
            chainId: network.chainId
        });
        
        // Check balance
        const balance = await connectedWallet.getBalance();
        results.steps.push({
            step: 'Balance Check',
            balance: ethers.utils.formatEther(balance),
            balanceWei: balance.toString()
        });

        // Get gas estimates
        const gasPrice = await provider.getGasPrice();
        const estimatedGas = 3000000; // Conservative estimate
        const estimatedCost = gasPrice.mul(estimatedGas);
        
        results.steps.push({
            step: 'Deployment Estimates',
            gasPrice: ethers.utils.formatUnits(gasPrice, 'gwei'),
            estimatedGas,
            estimatedCost: ethers.utils.formatEther(estimatedCost),
            hasSufficientFunds: balance.gt(estimatedCost)
        });

        results.success = true;
    } catch (error) {
        results.success = false;
        results.error = {
            message: error.message,
            details: error.error ? error.error.toString() : undefined
        };
    }

    // Write results to file
    fs.writeFileSync('wallet-verification-results.json', JSON.stringify(results, null, 2));
}

main()
    .then(() => {
        const results = JSON.parse(fs.readFileSync('wallet-verification-results.json', 'utf8'));
        if (results.success) {
            console.log('Verification completed successfully. Check wallet-verification-results.json for details.');
            process.exit(0);
        } else {
            console.error('Verification failed. Check wallet-verification-results.json for details.');
            process.exit(1);
        }
    })
    .catch((error) => {
        console.error('Fatal error:', error);
        process.exit(1);
    });