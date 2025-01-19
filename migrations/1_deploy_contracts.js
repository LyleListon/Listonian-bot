/**
 * Initial Migration Script
 * @LAST_POINT: 2024-01-31 - Initial contract deployment setup
 */

const ArbitrageBot = artifacts.require("ArbitrageBot");
const MockPriceFeed = artifacts.require("MockPriceFeed");

module.exports = async function(deployer, network, accounts) {
  // Deploy ArbitrageBot with initial parameters
  const DEFAULT_MIN_PROFIT_BASIS_POINTS = 100; // 1% minimum profit
  const DEFAULT_MAX_TRADE_SIZE = web3.utils.toWei('10', 'ether'); // 10 tokens max trade size
  const EMERGENCY_WITHDRAWAL_DELAY = 86400; // 24 hours in seconds
  
  await deployer.deploy(
    ArbitrageBot,
    DEFAULT_MIN_PROFIT_BASIS_POINTS,
    DEFAULT_MAX_TRADE_SIZE,
    EMERGENCY_WITHDRAWAL_DELAY
  );
  
  // Log deployment info
  const arbitrageBot = await ArbitrageBot.deployed();
  console.log(`ArbitrageBot deployed at: ${arbitrageBot.address}`);
  
  // Deploy MockPriceFeed if we're in development/test
  if (network === 'development' || network === 'test') {
    await deployer.deploy(MockPriceFeed);
    const mockPriceFeed = await MockPriceFeed.deployed();
    console.log(`MockPriceFeed deployed at: ${mockPriceFeed.address}`);
  }
};
