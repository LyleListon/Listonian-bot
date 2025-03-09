const PriceFeedRegistry = artifacts.require("PriceFeedRegistry");

module.exports = async function(deployer, network, accounts) {
  console.log('Deploying to network:', network);
  console.log('Using account:', accounts[0]);

  try {
    // Deploy PriceFeedRegistry
    console.log('Deploying PriceFeedRegistry...');
    await deployer.deploy(PriceFeedRegistry);
    const registry = await PriceFeedRegistry.deployed();
    console.log('PriceFeedRegistry deployed at:', registry.address);
  } catch (error) {
    console.error('Deployment failed:', error);
    throw error;
  }
};
