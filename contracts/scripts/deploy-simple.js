const { ethers } = require('ethers');
const fs = require('fs');

async function main() {
    try {
        // Read and parse .env file manually
        const envContent = fs.readFileSync('.env', 'utf8');
        const env = {};
        envContent.split('\n').forEach(line => {
            const [key, value] = line.split('=');
            if (key && value) {
                env[key.trim()] = value.trim();
            }
        });

        console.log('\n=== Starting Deployment ===\n');

        // Create provider and wallet
        const provider = new ethers.providers.JsonRpcProvider(env.BASE_RPC_URL);
        const wallet = new ethers.Wallet(env.PRIVATE_KEY, provider);
        
        console.log('Deploying with wallet:', wallet.address);
        console.log('Expected wallet:', env.WALLET_ADDRESS);
        
        if (wallet.address.toLowerCase() !== env.WALLET_ADDRESS.toLowerCase()) {
            throw new Error('Wallet address mismatch!');
        }

        const balance = await wallet.getBalance();
        console.log('Balance:', ethers.utils.formatEther(balance), 'ETH');

        // Deploy contract
        const POOL_ADDRESS_PROVIDER = "0xe20fCBdBfFC4Dd138cE8b2E6FBb6CB49777ad64D";
        console.log('\nPool Address Provider:', POOL_ADDRESS_PROVIDER);

        // Get contract factory
        const artifactPath = './artifacts/contracts/MultiPathArbitrage.sol/MultiPathArbitrage.json';
        const contractArtifact = require(artifactPath);
        
        const factory = new ethers.ContractFactory(
            contractArtifact.abi,
            contractArtifact.bytecode,
            wallet
        );

        // Get gas price and add 20% buffer
        const gasPrice = await provider.getGasPrice();
        const adjustedGasPrice = gasPrice.mul(120).div(100);
        console.log('Gas Price:', ethers.utils.formatUnits(adjustedGasPrice, 'gwei'), 'gwei');

        // Deploy with explicit parameters
        console.log('\nDeploying contract...');
        const contract = await factory.deploy(POOL_ADDRESS_PROVIDER, {
            gasPrice: adjustedGasPrice,
            gasLimit: 3000000
        });

        console.log('Deployment transaction:', contract.deployTransaction.hash);
        console.log('Waiting for confirmation...');

        await contract.deployed();
        console.log('\nContract deployed to:', contract.address);

        // Save deployment details
        const details = {
            contract: 'MultiPathArbitrage',
            address: contract.address,
            deployer: wallet.address,
            transactionHash: contract.deployTransaction.hash,
            poolAddressProvider: POOL_ADDRESS_PROVIDER,
            timestamp: new Date().toISOString()
        };

        fs.writeFileSync(
            'deployment-result.json',
            JSON.stringify(details, null, 2)
        );

        console.log('\nDeployment details saved to deployment-result.json');
        console.log('\n=== Deployment Complete ===\n');

    } catch (error) {
        console.error('\nDeployment failed!');
        console.error('Error:', error.message);
        if (error.error) {
            console.error('Provider error:', error.error);
        }
        throw error;
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        process.exit(1);
    });