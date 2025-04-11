# Listonian-Bot: Next Steps Plan (Post Startup Fixes)

The bot is now successfully starting up after resolving numerous import, name, initialization, and configuration errors. Logging verbosity has also been reduced.

Based on the original fix plan (`listonian_bot_fix_plan.md`) and runtime observations, here are the recommended next steps, prioritized:

## 1. Address Trade Execution Problems (Highest Priority)

This remains the most critical area as it directly impacts the bot's core functionality. The focus should be on the `EnhancedFlashLoanManager` and related components.

**Tasks:**

*   **1.1 Refactor `EnhancedFlashLoanManager`:**
    *   Correct the usage of `web3` vs `web3_manager`. Ensure the correct object (`web3_manager.w3`) is used for blockchain interactions.
    *   Define or replace missing data models (`TokenPair`, `LiquidityData`). Determine the intended structure or refactor the code to use existing models (like `TokenAmount` and dictionaries).
    *   Investigate the `dex.create_swap_transaction` method called within the manager. Confirm if this method exists in `BaseDEX` or its implementations, or refactor the manager to use `dex.build_swap_transaction` instead.
    *   Review the flash loan provider integration (`BalancerFlashLoanProvider`) to ensure correct transaction building and interaction.
*   **1.2 Verify Flash Loan Logic:**
    *   Test the flash loan borrowing and repayment flow (`_create_flash_loan_tx`, `_create_repayment_tx`).
    *   Ensure error handling for flash loan failures is robust.
*   **1.3 Add Testing:**
    *   Implement unit and integration tests for the `EnhancedFlashLoanManager` and related finance components.

## 2. Re-enable `CrossDexDetector`

The detector is currently bypassed due to errors fetching token pairs.

**Tasks:**

*   Refactor `CrossDexDetector` (and potentially `TriangularDetector`) to obtain token pair and price information from the `EnhancedMarketDataProvider`'s `market_condition` data or another reliable source, instead of relying on a non-existent `dex.get_token_pairs` method.

## 3. Investigate Persistent DEX Validator Error

Despite code corrections, logs still show `AttributeError: 'Web3Manager' object has no attribute 'contract'` during validation.

**Tasks:**

*   Deep dive into the `DEXDiscoveryManager`'s initialization process.
*   Verify the exact `web3_manager` object instance being passed to the `DEXValidator`.
*   Trace the execution flow during validation to pinpoint where the incorrect attribute access occurs.

## 4. Fix DEX Discovery Source Errors

The DeFiLlama and DexScreener sources are failing with 404 errors.

**Tasks:**

*   Investigate the API endpoints used in `defillama.py` and `dexscreener.py`.
*   Update URLs or parsing logic as needed based on current API documentation for these services.

## 5. Address Shutdown Errors

`aiohttp` session/connector errors indicate resource leaks.

**Tasks:**

*   Review code sections using `aiohttp` (likely in discovery sources or market data provider).
*   Ensure client sessions and connectors are properly closed during the `cleanup` phase of relevant classes.

## 6. Address Remaining Original Plan Items

Once the above critical runtime issues and core execution logic are stable, revisit the remaining items from `listonian_bot_fix_plan.md`:

*   Flashbots Integration (Plan item 1.2)
*   Gas Price Calculations (Plan item 1.3)
*   `execute_opportunity` Method (Plan item 1.4)
*   Dashboard Display Issues (Plan item 4)