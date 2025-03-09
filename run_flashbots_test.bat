@echo off
echo Running Flashbots Integration Tests...
echo.

REM Set environment variables for testing
set FLASHBOTS_PRIVATE_KEY=0000000000000000000000000000000000000000000000000000000000000001
set FLASHBOTS_RELAY_URL=https://relay-goerli.flashbots.net

REM Run the flashbots simulator test
python -c "import asyncio; from arbitrage_bot.core.web3.flashbots.simulator import BundleSimulator; from arbitrage_bot.core.web3.interfaces import Web3Client; from arbitrage_bot.core.web3.providers.eth_client import EthClient; async def test_simulator(): client = EthClient(provider_url='https://goerli.infura.io/v3/YOUR_INFURA_KEY'); await client.connect(); simulator = BundleSimulator(client); await simulator.initialize(); print('Simulator initialized successfully'); await client.close(); asyncio.run(test_simulator())"

REM Run the flashbots provider test
python -c "import asyncio; from arbitrage_bot.core.web3.flashbots.provider import FlashbotsProvider; from arbitrage_bot.core.web3.interfaces import Web3Client; from arbitrage_bot.core.web3.providers.eth_client import EthClient; async def test_provider(): client = EthClient(provider_url='https://goerli.infura.io/v3/YOUR_INFURA_KEY'); await client.connect(); provider = FlashbotsProvider(client, signing_key=os.environ.get('FLASHBOTS_PRIVATE_KEY'), config={'network': 'goerli', 'relay_url': os.environ.get('FLASHBOTS_RELAY_URL')}); result = await provider.initialize(); print(f'Provider initialized: {result}'); await client.close(); asyncio.run(test_provider())"

echo.
echo Flashbots Tests completed.
pause