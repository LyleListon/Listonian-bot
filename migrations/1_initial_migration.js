const ArbitrageBot = artifacts.require("ArbitrageBot");
const PriceFeedRegistry = artifacts.require("PriceFeedRegistry");
const DEXRegistry = artifacts.require("DEXRegistry");

module.exports = async function (deployer, network, accounts) {
  // Deploy registries first
  await deployer.deploy(PriceFeedRegistry);
  await deployer.deploy(DEXRegistry);

  // Deploy ArbitrageBot with initial parameters
  const DEFAULT_MIN_PROFIT_BASIS_POINTS = 100; // 1%
  const DEFAULT_MAX_TRADE_SIZE = web3.utils.toWei("10", "ether");
  const EMERGENCY_WITHDRAWAL_DELAY = 86400; // 24 hours

  await deployer.deploy(
    ArbitrageBot,
    DEFAULT_MIN_PROFIT_BASIS_POINTS,
    DEFAULT_MAX_TRADE_SIZE,
    EMERGENCY_WITHDRAWAL_DELAY
  );

  // Get deployed instances
  const bot = await ArbitrageBot.deployed();
  const priceFeedRegistry = await PriceFeedRegistry.deployed();
  const dexRegistry = await DEXRegistry.deployed();

  // Set registries in ArbitrageBot
  await bot.setRegistries(
    priceFeedRegistry.address,
    dexRegistry.address
  );

  console.log("Deployed ArbitrageBot at:", bot.address);
  console.log("Deployed PriceFeedRegistry at:", priceFeedRegistry.address);
  console.log("Deployed DEXRegistry at:", dexRegistry.address);
};
