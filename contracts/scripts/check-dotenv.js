const fs = require('fs');
const path = require('path');

console.log('Starting environment check...');

// Check if .env exists
const envPath = path.join(process.cwd(), '.env');
console.log('Looking for .env at:', envPath);

if (fs.existsSync(envPath)) {
    console.log('\n.env file found!');
    const content = fs.readFileSync(envPath, 'utf8');
    const lines = content.split('\n');
    
    console.log('\nEnvironment variables:');
    lines.forEach(line => {
        const [key] = line.split('=');
        if (key) {
            console.log(`- ${key.trim()}: ${line.includes('=') ? 'Set' : 'Not set'}`);
        }
    });
} else {
    console.log('\n.env file not found!');
}

// Check if we can load with dotenv
try {
    require('dotenv').config();
    console.log('\nLoaded with dotenv:');
    console.log('- PRIVATE_KEY:', process.env.PRIVATE_KEY ? 'Set' : 'Not set');
    console.log('- WALLET_ADDRESS:', process.env.WALLET_ADDRESS || 'Not set');
    console.log('- BASE_RPC_URL:', process.env.BASE_RPC_URL ? 'Set' : 'Not set');
} catch (error) {
    console.log('\nError loading with dotenv:', error.message);
}