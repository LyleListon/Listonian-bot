import { ethers } from 'ethers';
import { writeFileSync } from 'fs';

async function generateFlashbotsKey() {
    console.log('Generating new Flashbots auth key...');

    // Create a new random wallet
    const wallet = ethers.Wallet.createRandom();

    // Extract the private key
    const privateKey = wallet.privateKey;
    const address = wallet.address;

    console.log('\nFlashbots Auth Key Generated:');
    console.log('===============================');
    console.log(`Address: ${address}`);
    console.log(`Private Key: ${privateKey}`);

    // Save to a secure file
    const keyDetails = {
        address: address,
        privateKey: privateKey,
        timestamp: new Date().toISOString(),
        purpose: 'Flashbots Authentication'
    };

    writeFileSync(
        'flashbots-auth.json',
        JSON.stringify(keyDetails, null, 2)
    );

    console.log('\nKey details saved to flashbots-auth.json');
    console.log('\nIMPORTANT: Keep this key secure and never share it.');
    console.log('This key should only be used for Flashbots authentication.');
}

generateFlashbotsKey()
    .then(() => process.exit(0))
    .catch(error => {
        console.error('Error generating Flashbots key:', error);
        process.exit(1);
    });