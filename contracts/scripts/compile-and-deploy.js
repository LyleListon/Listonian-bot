const { ethers } = require('ethers');
const fs = require('fs');

async function main() {
    try {
        console.log('\n=== Step 1: Loading Environment ===\n');
        const envContent = fs.readFileSync('.env', 'utf8');
        const env = {};
        envContent.split('\n').forEach(line => {
            const [key, value] = line.split('=');
            if (key && value) {
                env[key.trim()] = value.trim();
            }
        });

        console.log('Environment loaded:');
        console.log(`WALLET_ADDRESS: ${env.WALLET_ADDRESS}`);
        console.log(`PRIVATE_KEY: ${env.PRIVATE_KEY ? 'Set' : 'Not Set'}`);
        console.log(`BASE_RPC_URL: ${env.BASE_RPC_URL ? 'Set' : 'Not Set'}`);

        console.log('\n=== Step 2: Setting Up Provider ===\n');
        const provider = new ethers.providers.JsonRpcProvider(env.BASE_RPC_URL);
        const network = await provider.getNetwork();
        console.log(`Network Name: ${network.name}`);
        console.log(`Network ID: ${network.chainId}`);

        console.log('\n=== Step 3: Setting Up Wallet ===\n');
        const wallet = new ethers.Wallet(env.PRIVATE_KEY, provider);
        console.log(`Wallet Address: ${wallet.address}`);
        
        if (wallet.address.toLowerCase() !== env.WALLET_ADDRESS.toLowerCase()) {
            throw new Error(`Wallet address mismatch! Expected ${env.WALLET_ADDRESS} but got ${wallet.address}`);
        }

        const balance = await wallet.getBalance();
        console.log(`Wallet Balance: ${ethers.utils.formatEther(balance)} ETH`);

        // Get current nonce
        const nonce = await provider.getTransactionCount(wallet.address);
        console.log(`Current nonce: ${nonce}`);

        console.log('\n=== Step 4: Loading Contract ===\n');
        const artifactPath = './artifacts/contracts/MultiPathArbitrage.sol/MultiPathArbitrage.json';
        if (!fs.existsSync(artifactPath)) {
            throw new Error(`Contract artifact not found at ${artifactPath}. Make sure the contract is compiled.`);
        }
        const contractArtifact = JSON.parse(fs.readFileSync(artifactPath));
        console.log('Contract artifact loaded successfully');

        console.log('\n=== Step 5: Preparing Deployment ===\n');
        const POOL_ADDRESS_PROVIDER = "0xe20fCBdBfFC4Dd138cE8b2E6FBb6CB49777ad64D";
        console.log(`Pool Address Provider: ${POOL_ADDRESS_PROVIDER}`);

        const factory = new ethers.ContractFactory(
            contractArtifact.abi,
            contractArtifact.bytecode,
            wallet
        );

        const gasPrice = await provider.getGasPrice();
        const adjustedGasPrice = gasPrice.mul(120).div(100);
        console.log(`Gas Price: ${ethers.utils.formatUnits(adjustedGasPrice, 'gwei')} gwei`);

        const estimatedGas = 3000000; // Conservative estimate
        const estimatedCost = adjustedGasPrice.mul(estimatedGas);
        console.log(`Estimated Gas: ${estimatedGas}`);
        console.log(`Estimated Cost: ${ethers.utils.formatEther(estimatedCost)} ETH`);

        if (balance.lt(estimatedCost)) {
            throw new Error(`Insufficient funds. Need ${ethers.utils.formatEther(estimatedCost)} ETH but have ${ethers.utils.formatEther(balance)} ETH`);
        }

        const deploymentParams = {
            gasPrice: adjustedGasPrice,
            gasLimit: estimatedGas,
            nonce: nonce // Use current nonce
        };
        console.log('Deployment parameters:', deploymentParams);

        console.log('\n=== Step 6: Deploying Contract ===\n');
        const contract = await factory.deploy(POOL_ADDRESS_PROVIDER, deploymentParams);
        console.log(`Deployment transaction sent: ${contract.deployTransaction.hash}`);
        console.log('Waiting for confirmation...');

        await contract.deployed();
        console.log(`Contract deployed successfully to: ${contract.address}`);

        const details = {
            contract: 'MultiPathArbitrage',
            address: contract.address,
            deployer: wallet.address,
            transactionHash: contract.deployTransaction.hash,
            poolAddressProvider: POOL_ADDRESS_PROVIDER,
            timestamp: new Date().toISOString()
        };

        fs.writeFileSync('deployment-result.json', JSON.stringify(details, null, 2));
        console.log('\nDeployment details saved to deployment-result.json');
        console.log('\n=== Deployment Complete ===\n');

    } catch (error) {
        console.log('\n=== Deployment Failed ===\n');
        console.log(`Error: ${error.message}`);
        if (error.error) {
            console.log(`Provider Error: ${error.error}`);
        }
        throw error;
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        process.exit(1);
    });