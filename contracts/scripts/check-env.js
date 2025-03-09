console.log('Starting environment check...\n');

try {
    require('dotenv').config();
    
    console.log('Environment variables:');
    console.log('PRIVATE_KEY:', process.env.PRIVATE_KEY ? 'Set' : 'Not set');
    console.log('WALLET_ADDRESS:', process.env.WALLET_ADDRESS);
    console.log('BASE_RPC_URL:', process.env.BASE_RPC_URL ? 'Set' : 'Not set');
    console.log('ETHERSCAN_API_KEY:', process.env.ETHERSCAN_API_KEY ? 'Set' : 'Not set');

    const { ethers } = require('ethers');
    
    if (process.env.PRIVATE_KEY) {
        const wallet = new ethers.Wallet(process.env.PRIVATE_KEY);
        console.log('\nWallet check:');
        console.log('Derived address:', wallet.address);
        console.log('Matches expected:', wallet.address.toLowerCase() === process.env.WALLET_ADDRESS.toLowerCase());
    }

    console.log('\nCheck complete!');
} catch (error) {
    console.error('Error during check:', error);
}