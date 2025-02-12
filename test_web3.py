from web3 import AsyncWeb3
from web3 import middleware
import inspect

# Print all available middleware
print("Available middleware in web3.middleware:")
for name, obj in inspect.getmembers(middleware):
    if not name.startswith('_'):
        print(f"- {name}")

# Create a Web3 instance and check its middleware
w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider('http://localhost:8545'))
print("\nDefault middleware in Web3 instance:")
for mw in w3.middleware_onion:
    print(f"- {mw}")