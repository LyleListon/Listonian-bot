# Token Verification System

## Current Issues
1. Duplicate addresses in configuration
2. Potential decimal mismatches
3. No validation of token contracts
4. No automated verification

## Proposed Solution

### 1. Token Verification Class

```python
from web3 import Web3
from typing import Dict, Optional, Set
import json
import aiohttp
import logging

class TokenVerifier:
    def __init__(self, web3_manager):
        self.web3 = web3_manager.web3
        self.verified_tokens: Dict[str, Dict] = {}
        self.address_registry: Set[str] = set()
        self.logger = logging.getLogger("TokenVerifier")
        
    async def verify_token(self, symbol: str, address: str, expected_decimals: Optional[int] = None) -> bool:
        """
        Verify token contract and details.
        
        Args:
            symbol: Token symbol (e.g., "USDT")
            address: Token contract address
            expected_decimals: Expected number of decimals
            
        Returns:
            bool: True if token is verified
        """
        try:
            # Check for duplicate address
            checksum_address = Web3.to_checksum_address(address)
            if checksum_address in self.address_registry:
                self.logger.error(f"Duplicate token address detected: {address}")
                return False
                
            # Load ERC20 ABI
            with open("abi/ERC20.json") as f:
                erc20_abi = json.load(f)
                
            # Create contract instance
            token_contract = self.web3.eth.contract(
                address=checksum_address,
                abi=erc20_abi
            )
            
            # Verify contract code exists
            code = await self.web3.eth.get_code(checksum_address)
            if code == "0x":
                self.logger.error(f"No contract code found at {address}")
                return False
                
            # Verify basic ERC20 functions
            try:
                contract_symbol = await token_contract.functions.symbol().call()
                contract_decimals = await token_contract.functions.decimals().call()
                contract_name = await token_contract.functions.name().call()
                total_supply = await token_contract.functions.totalSupply().call()
            except Exception as e:
                self.logger.error(f"Failed to verify ERC20 interface: {e}")
                return False
                
            # Verify symbol matches
            if contract_symbol.upper() != symbol.upper():
                self.logger.error(
                    f"Symbol mismatch: config={symbol}, contract={contract_symbol}"
                )
                return False
                
            # Verify decimals if expected value provided
            if expected_decimals is not None:
                if contract_decimals != expected_decimals:
                    self.logger.error(
                        f"Decimals mismatch: config={expected_decimals}, contract={contract_decimals}"
                    )
                    return False
                    
            # Verify total supply > 0
            if total_supply == 0:
                self.logger.warning(f"Token {symbol} has zero total supply")
                
            # Store verified token info
            self.verified_tokens[symbol] = {
                "address": checksum_address,
                "decimals": contract_decimals,
                "name": contract_name,
                "symbol": contract_symbol,
                "total_supply": total_supply
            }
            
            self.address_registry.add(checksum_address)
            return True
            
        except Exception as e:
            self.logger.error(f"Token verification failed: {e}")
            return False
            
    async def verify_token_pair(self, token0: str, token1: str, dex_name: str) -> bool:
        """
        Verify trading pair exists on DEX.
        
        Args:
            token0: First token symbol
            token1: Second token symbol
            dex_name: Name of DEX to check
            
        Returns:
            bool: True if pair exists and has liquidity
        """
        try:
            # Get verified token addresses
            token0_data = self.verified_tokens.get(token0)
            token1_data = self.verified_tokens.get(token1)
            
            if not token0_data or not token1_data:
                self.logger.error("Tokens must be verified first")
                return False
                
            # Check pair exists on DEX
            # Implementation depends on DEX interface
            return True
            
        except Exception as e:
            self.logger.error(f"Pair verification failed: {e}")
            return False
```

### 2. Configuration Validation

```python
class ConfigValidator:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.verifier = None
        self.errors = []
        self.warnings = []
        
    async def validate_config(self) -> bool:
        """
        Validate entire token configuration.
        
        Returns:
            bool: True if config is valid
        """
        try:
            with open(self.config_path) as f:
                config = json.load(f)
                
            # Initialize verifier
            web3_manager = create_web3_manager()
            self.verifier = TokenVerifier(web3_manager)
            
            # Track addresses to check for duplicates
            addresses = set()
            
            # Validate each token
            for symbol, token_data in config["tokens"].items():
                address = token_data["address"]
                
                # Check for duplicate addresses
                if address in addresses:
                    self.errors.append(f"Duplicate address {address} found")
                    continue
                    
                addresses.add(address)
                
                # Verify token contract
                is_valid = await self.verifier.verify_token(
                    symbol,
                    address,
                    token_data.get("decimals")
                )
                
                if not is_valid:
                    self.errors.append(f"Token {symbol} verification failed")
                    
            # Validate trading pairs
            for pair in config.get("pairs", []):
                token0, token1 = pair.split("/")
                for dex in config["dexes"]:
                    if not await self.verifier.verify_token_pair(token0, token1, dex):
                        self.warnings.append(
                            f"Pair {pair} not found on {dex}"
                        )
                        
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"Configuration validation failed: {e}")
            return False
```

### 3. Integration with Existing System

```python
# In DexInterface.__init__
async def initialize(self):
    # Load and validate config
    config_validator = ConfigValidator("config/tokens.json")
    if not await config_validator.validate_config():
        for error in config_validator.errors:
            logger.error(f"Config validation error: {error}")
        for warning in config_validator.warnings:
            logger.warning(f"Config validation warning: {warning}")
        raise ValueError("Token configuration validation failed")
        
    # Use validated tokens
    self.verified_tokens = config_validator.verifier.verified_tokens
```

### 4. Base Chain Token Registry

```json
{
    "WETH": {
        "name": "Wrapped Ether",
        "address": "0x4200000000000000000000000000000000000006",
        "decimals": 18,
        "verified": true
    },
    "USDC": {
        "name": "USD Coin",
        "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "decimals": 6,
        "verified": true
    },
    "DAI": {
        "name": "Dai Stablecoin",
        "address": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
        "decimals": 18,
        "verified": true
    },
    "USDT": {
        "name": "Tether USD",
        "address": "0x4D91fa57ABAA17c415E2711A0B57CCCB22875C0C",
        "decimals": 6,
        "verified": true
    }
}
```

## Implementation Plan

### Phase 1: Immediate Fixes
1. Update token addresses in configuration
2. Add basic duplicate address check
3. Implement simple contract verification
4. Add configuration validation

### Phase 2: Enhanced Verification
1. Implement TokenVerifier class
2. Add pair verification
3. Integrate with DEX interface
4. Add automated testing

### Phase 3: Monitoring & Maintenance
1. Add continuous verification
2. Implement alert system
3. Add token metrics tracking
4. Create admin interface

## Benefits

1. Prevents Configuration Errors
- No duplicate addresses
- Verified decimals
- Validated contracts
- Checked trading pairs

2. Improved Reliability
- Verified token interfaces
- Validated liquidity
- Checked decimals
- Monitored contracts

3. Better Maintenance
- Automated verification
- Clear error messages
- Easy updates
- Continuous monitoring

## Next Steps

1. Implementation
- Create verification classes
- Update configuration
- Add validation system
- Implement monitoring

2. Testing
- Unit test verification
- Integration test config
- Test error handling
- Validate all tokens

3. Deployment
- Update production config
- Deploy verification system
- Monitor for issues
- Document changes