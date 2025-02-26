"""Path finding for multi-DEX arbitrage opportunities."""

import logging
import asyncio
from typing import Dict, List, Tuple, Set, Optional, Any, Union
from decimal import Decimal
import heapq
import time
from web3 import Web3

logger = logging.getLogger(__name__)

class ArbitragePath:
    """Represents a path through multiple DEXs for arbitrage."""
    
    def __init__(
        self,
        input_token: str,
        output_token: str,
        amount_in: int,
        route: List[Dict[str, Any]] = None
    ):
        """
        Initialize an arbitrage path.
        
        Args:
            input_token: Starting token address
            output_token: Ending token address
            amount_in: Input amount in wei
            route: List of DEX steps in the route
        """
        self.input_token = Web3.to_checksum_address(input_token)
        self.output_token = Web3.to_checksum_address(output_token)
        self.amount_in = amount_in
        self.route = route or []
        self.estimated_output = 0
        self.estimated_gas_cost = 0
        self.estimated_profit = 0
        self.success_probability = 0.0
        self.error = None
    
    def add_step(
        self,
        dex_name: str,
        token_in: str,
        token_out: str,
        amount_in: int,
        amount_out: int,
        gas_estimate: int = 0,
        path: List[str] = None
    ):
        """
        Add a step to the arbitrage path.
        
        Args:
            dex_name: Name of the DEX for this step
            token_in: Input token address for this step
            token_out: Output token address for this step
            amount_in: Input amount for this step in wei
            amount_out: Estimated output amount in wei
            gas_estimate: Estimated gas cost for this step
            path: Token path for this step (for multi-hop DEX swaps)
        """
        self.route.append({
            "dex": dex_name,
            "token_in": Web3.to_checksum_address(token_in),
            "token_out": Web3.to_checksum_address(token_out),
            "amount_in": amount_in,
            "amount_out": amount_out,
            "gas_estimate": gas_estimate,
            "path": [Web3.to_checksum_address(t) for t in (path or [token_in, token_out])]
        })
        
        # Update estimated output to the output of the last step
        if self.route:
            self.estimated_output = self.route[-1]["amount_out"]
            self.estimated_gas_cost += gas_estimate
        
    def calculate_profit(self, gas_price: int = 0):
        """
        Calculate the estimated profit for this path.
        
        Args:
            gas_price: Current gas price in wei
            
        Returns:
            Estimated profit in wei
        """
        if not self.route:
            return 0
            
        # Calculate total gas cost
        total_gas_cost = self.estimated_gas_cost * gas_price
        
        # Calculate profit (output amount - input amount - gas cost)
        profit = self.estimated_output - self.amount_in - total_gas_cost
        self.estimated_profit = profit
        
        return profit
    
    def is_profitable(self, min_profit: int = 0, gas_price: int = 0):
        """
        Check if the path is profitable.
        
        Args:
            min_profit: Minimum required profit in wei
            gas_price: Current gas price in wei
            
        Returns:
            True if profit exceeds minimum threshold
        """
        profit = self.calculate_profit(gas_price)
        return profit > min_profit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert path to dictionary representation."""
        return {
            "input_token": self.input_token,
            "output_token": self.output_token,
            "amount_in": self.amount_in,
            "estimated_output": self.estimated_output,
            "estimated_gas_cost": self.estimated_gas_cost,
            "estimated_profit": self.estimated_profit,
            "success_probability": self.success_probability,
            "route": self.route,
            "error": str(self.error) if self.error else None
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        dexes = " -> ".join([step["dex"] for step in self.route])
        return f"Path({self.input_token[:8]}...{self.input_token[-6:]} -> {self.output_token[:8]}...{self.output_token[-6:]}, {dexes}, profit: {self.estimated_profit})"


class PathFinder:
    """Finds optimal arbitrage paths across multiple DEXs."""
    
    def __init__(self, dex_manager, web3_manager = None, config = None):
        """
        Initialize path finder.
        
        Args:
            dex_manager: DexManager instance for accessing DEXs
            web3_manager: Web3Manager instance
            config: Configuration dictionary
        """
        self.dex_manager = dex_manager
        self.web3_manager = web3_manager or dex_manager.web3_manager
        self.config = config or {}
        
        # Path finding settings
        self.max_path_length = self.config.get("max_path_length", 3)
        self.max_hops_per_dex = self.config.get("max_hops_per_dex", 2)
        self.max_paths_to_check = self.config.get("max_paths_to_check", 10)
        self.enable_multi_hop_paths = self.config.get("enable_multi_hop_paths", True)
        self.min_profit_threshold = self.config.get("min_profit_threshold", 0)
        
        # Token whitelist/blacklist
        self.token_whitelist = set(self.config.get("token_whitelist", []))
        self.token_blacklist = set(self.config.get("token_blacklist", []))
        
        # DEX preferences
        self.preferred_dexes = self.config.get("preferred_dexes", [])
        
        # Common tokens like WETH, USDC, etc. that often form good paths
        self.common_tokens = set(self.config.get("common_tokens", []))
        
        # Lock for preventing concurrent path finding
        self._find_lock = asyncio.Lock()
        
        logger.info("Initialized PathFinder with max path length %d", self.max_path_length)
    
    async def find_arbitrage_opportunities(
        self,
        input_token: str,
        output_token: str = None,
        amount_in: int = None,
        min_profit: int = None,
        max_gas_price: int = None,
        max_paths: int = 3
    ) -> List[ArbitragePath]:
        """
        Find arbitrage opportunities for the given input.
        
        Args:
            input_token: Starting token address
            output_token: Ending token address (defaults to same as input for circular arbitrage)
            amount_in: Input amount in wei
            min_profit: Minimum profit threshold
            max_gas_price: Maximum gas price to consider
            max_paths: Maximum number of paths to return
            
        Returns:
            List of ArbitragePath objects sorted by profit
        """
        async with self._find_lock:
            # Set defaults
            input_token = Web3.to_checksum_address(input_token)
            output_token = Web3.to_checksum_address(output_token) if output_token else input_token
            
            if not amount_in:
                # Default amount from config
                amount_in = self.config.get("default_amount", 10**18)  # 1 ETH
                
            min_profit = min_profit or self.min_profit_threshold
            
            # Get current gas price
            if not max_gas_price:
                # Get current gas price with 50% buffer
                block = await self.web3_manager.get_block("latest")
                base_fee = block.get("baseFeePerGas", 0)
                max_gas_price = int(base_fee * 1.5)
            
            logger.info(
                "Finding arbitrage opportunities: %s -> %s, amount: %d, min profit: %d, max gas: %d",
                input_token, output_token, amount_in, min_profit, max_gas_price
            )
            
            # Get available DEXs
            dexes = self.dex_manager.get_enabled_dexes()
            if not dexes:
                logger.error("No enabled DEXs available")
                return []
                
            # Find multi-DEX paths
            paths = await self._find_multi_dex_paths(
                input_token=input_token,
                output_token=output_token,
                amount_in=amount_in,
                enable_multi_hop=self.enable_multi_hop_paths,
                max_hops_per_dex=self.max_hops_per_dex,
                min_profit=min_profit,
                gas_price=max_gas_price,
            )
            
            # Sort paths by estimated profit
            sorted_paths = sorted(
                paths, 
                key=lambda p: p.estimated_profit, 
                reverse=True
            )
            
            # Return top paths
            return sorted_paths[:max_paths]
    
    async def _find_multi_dex_paths(
        self,
        input_token: str,
        output_token: str,
        amount_in: int,
        enable_multi_hop: bool = True,
        max_hops_per_dex: int = 2,
        min_profit: int = 0,
        gas_price: int
 = 0
    ) -> List[ArbitragePath]:
        """
        Find multi-DEX arbitrage paths.
        
        Args:
            input_token: Input token address
            output_token: Output token address
            amount_in: Input amount in wei
            enable_multi_hop: Whether to enable multi-hop paths within a single DEX
            max_hops_per_dex: Maximum number of hops to allow within a single DEX
            min_profit: Minimum profit threshold
            gas_price: Current gas price
            
        Returns:
            List of ArbitragePath objects
        """
        # Initialize results
        paths = []
        
        # Start timing
        start_time = time.time()
        
        # Get available DEXs
        dexes = self.dex_manager.get_enabled_dexes()
        
        # Initialize the base path
        base_path = ArbitragePath(
            input_token=input_token,
            output_token=output_token,
            amount_in=amount_in
        )
        
        # Explore paths with single DEX (direct arbitrage)
        for dex_name, dex in dexes.items():
            try:
                # Multi-hop paths within a single DEX (if enabled)
                if enable_multi_hop and max_hops_per_dex > 1:
                    try:
                        # Check if DEX supports multi-hop
                        supports_multi_hop = False
                        if hasattr(dex, 'supports_multi_hop'):
                            supports_multi_hop = await dex.supports_multi_hop()
                        
                        if supports_multi_hop:
                            self.logger.info("Checking multi-hop paths on %s", dex_name)
                            
                            # Try to find the best path using DEX's internal path finder
                            if hasattr(dex, 'find_best_path'):
                                best_path_info = await dex.find_best_path(
                                    token_in=input_token,
                                    token_out=output_token,
                                    amount_in=amount_in,
                                    max_hops=max_hops_per_dex
                                )
                                
                                if best_path_info and 'path' in best_path_info and 'amount_out' in best_path_info:
                                    # Create a new path for this multi-hop route
                                    path = ArbitragePath(
                                        input_token=input_token,
                                        output_token=output_token,
                                        amount_in=amount_in
                                    )
                                    
                                    # Get gas estimate for the multi-hop path
                                    gas_estimate = best_path_info.get('gas_estimate', 250000)
                                    
                                    # Add step to path
                                    path.add_step(
                                        dex_name=dex_name,
                                        token_in=input_token,
                                        token_out=output_token,
                                        amount_in=amount_in,
                                        amount_out=best_path_info['amount_out'],
                                        gas_estimate=gas_estimate,
                                        path=best_path_info['path']
                                    )
                                    
                                    # Calculate profit and check if profitable
                                    if path.is_profitable(min_profit, gas_price):
                                        paths.append(path)
                                        self.logger.info("Found profitable multi-hop path on %s with %d hops", 
                                                        dex_name, len(best_path_info['path'])-1)
                        
                    except Exception as e:
                        self.logger.warning("Error checking multi-hop paths on %s: %s", dex_name, str(e))
                
                # Check if this DEX supports both tokens
                if not await dex.supports_token(input_token) or not await dex.supports_token(output_token):
                    continue
                
                # Create a new path for this DEX
                path = ArbitragePath(
                    input_token=input_token,
                    output_token=output_token,
                    amount_in=amount_in
                )
                
                # Get route and amount out
                output_amount = await dex.get_amount_out(
                    token_in=input_token,
                    token_out=output_token,
                    amount_in=amount_in
                )
                
                if output_amount > 0:
                    # Estimate gas cost
                    gas_estimate = await dex.estimate_swap_gas(
                        token_in=input_token,
                        token_out=output_token,
                        amount_in=amount_in
                    )
                    
                    # Add step to path
                    path.add_step(
                        dex_name=dex_name,
                        token_in=input_token,
                        token_out=output_token,
                        amount_in=amount_in,
                        amount_out=output_amount,
                        gas_estimate=gas_estimate
                    )
                    
                    # Calculate profit and check if profitable
                    if path.is_profitable(min_profit, gas_price):
                        paths.append(path)
            except Exception as e:
                logger.warning("Error checking direct arbitrage on %s: %s", dex_name, str(e))
        
        # Explore multi-step paths across multiple DEXs
        await self._explore_multi_dex_paths(
            base_path=base_path,
            dexes=dexes,
            paths=paths,
            current_depth=0,
            min_profit=min_profit,
            gas_price=gas_price,
            visited_tokens=set(),
            visited_dexes=set()
        )
        
        # Log results
        elapsed = time.time() - start_time
        logger.info(
            "Found %d profitable paths in %.2f seconds, min profit: %d",
            len(paths), elapsed, min_profit
        )
        
        return paths
    
    async def _explore_multi_dex_paths(
        self,
        base_path: ArbitragePath,
        dexes: Dict[str, Any],
        paths: List[ArbitragePath],
        current_depth: int,
        min_profit: int,
        gas_price: int,
        visited_tokens: Set[str],
        visited_dexes: Set[str]
    ):
        """
        Recursively explore multi-DEX paths.
        
        Args:
            base_path: Current base path to extend
            dexes: Dictionary of available DEXs
            paths: List to collect profitable paths
            current_depth: Current recursion depth
            min_profit: Minimum profit threshold
            gas_price: Current gas price
            visited_tokens: Set of already visited tokens in this path
            visited_dexes: Set of already visited DEXs in this path
        """
        # Stop if we've reached max depth
        if current_depth >= self.max_path_length:
            return
            
        # Get current token from path
        current_token = base_path.output_token if base_path.route else base_path.input_token
        current_amount = base_path.estimated_output if base_path.route else base_path.amount_in
        
        # Skip if we've already visited this token and it's not the final token
        if current_token in visited_tokens and current_token != base_path.output_token:
            return
            
        # Add current token to visited set
        visited_tokens = visited_tokens.copy()
        visited_tokens.add(current_token)
        
        # Explore next DEX steps
        for dex_name, dex in dexes.items():
            # Skip if we've already used this DEX (to avoid loops)
            if dex_name in visited_dexes and len(visited_dexes) > 1:
                continue
                
            # Keep track of visited DEXs
            visited_dexes_updated = visited_dexes.copy()
            visited_dexes_updated.add(dex_name)
            
            # Check if current token is supported by this DEX
            if not await dex.supports_token(current_token):
                continue
                
            # Get pairs involving the current token on this DEX
            supported_pairs = await dex.get_pairs_for_token(current_token)
            if not supported_pairs:
                continue
                
            # Explore each token pair
            for pair in supported_pairs:
                token_out = pair[1] if pair[0].lower() == current_token.lower() else pair[0]
                
                # Skip if token is blacklisted
                if token_out.lower() in self.token_blacklist:
                    continue
                    
                # Only use whitelisted tokens if whitelist is defined
                if self.token_whitelist and token_out.lower() not in self.token_whitelist:
                    continue
                
                # Skip if we've already visited this token (avoid cycles)
                if token_out.lower() in visited_tokens and token_out.lower() != base_path.output_token.lower():
                    continue
                
                try:
                    # Get amount out for this step
                    amount_out = await dex.get_amount_out(
                        token_in=current_token,
                        token_out=token_out,
                        amount_in=current_amount
                    )
                    
                    if amount_out <= 0:
                        continue
                        
                    # Estimate gas for this step
                    gas_estimate = await dex.estimate_swap_gas(
                        token_in=current_token,
                        token_out=token_out,
                        amount_in=current_amount
                    )
                    
                    # Create a new path by extending the base path
                    new_path = ArbitragePath(
                        input_token=base_path.input_token,
                        output_token=base_path.output_token,
                        amount_in=base_path.amount_in,
                        route=base_path.route.copy()
                    )
                    
                    # Add this step to the path
                    new_path.add_step(
                        dex_name=dex_name,
                        token_in=current_token,
                        token_out=token_out,
                        amount_in=current_amount,
                        amount_out=amount_out,
                        gas_estimate=gas_estimate
                    )
                    
                    # If this completes the path and it's profitable, add it to results
                    if token_out.lower() == base_path.output_token.lower():
                        if new_path.is_profitable(min_profit, gas_price):
                            paths.append(new_path)
                    
                    # Otherwise, explore further if not at max depth
                    else:
                        await self._explore_multi_dex_paths(
                            base_path=new_path,
                            dexes=dexes,
                            paths=paths,
                            current_depth=current_depth + 1,
                            min_profit=min_profit,
                            gas_price=gas_price,
                            visited_tokens=visited_tokens,
                            visited_dexes=visited_dexes_updated
                        )
                        
                except Exception as e:
                    # Handle cases where the error is related to missing liquidity
                    if "INSUFFICIENT_LIQUIDITY" in str(e) or "INSUFFICIENT_INPUT_AMOUNT" in str(e):
                        # Skip this path silently, it's an expected condition
                        continue
                    elif "execution reverted" in str(e):
                        # Skip silently, common error with non-existent pools
                        continue
                    elif "did not converge" in str(e) or "price impact too high" in str(e):
                        # Skip silently, price impact issues
                        continue
                    elif "k" in str(e) and "underflow" in str(e):
                        # Skip silently, math underflow in pool calculation
                        continue
                    logger.warning(
                        "Error exploring path %s -> %s on %s: %s", 
                        current_token, token_out, dex_name, str(e)
                    )
    
    async def simulate_arbitrage_path(
        self,
        path: ArbitragePath,
        use_flashbots: bool = True
    ) -> Dict[str, Any]:
        """
        Simulate an arbitrage path without executing it.
        
        Args:
            path: ArbitragePath to simulate
            use_flashbots: Whether to use Flashbots for simulation
            
        Returns:
            Simulation results dictionary
        """
        if not path.route:
            return {"success": False, "error": "Empty path"}
            
        try:
            # Prepare transactions for each step
            transactions = []
            
            # Extract full paths for multi-hop swaps
            has_multi_hop = any(len(step.get('path', [])) > 2 for step in path.route)
            self.logger.info("Simulating %s path with %d steps", "multi-hop" if has_multi_hop else "standard", len(path.route))
            
            for step in path.route:
                dex_name = step["dex"]
                dex = self.dex_manager.get_dex(dex_name)
                if not dex:
                    return {"success": False, "error": f"DEX not found: {dex_name}"}
                
                # Build swap transaction
                # Check if this is a multi-hop swap (has a path with > 2 tokens)
                if 'path' in step and len(step['path']) > 2:
                    self.logger.info("Building multi-hop swap transaction with %d hops", len(step['path'])-1)
                    
                    # Use the DEX's special multi-hop transaction builder if available
                    if hasattr(dex, 'build_swap_transaction') and callable(dex.build_swap_transaction):
                        tx = await dex.build_swap_transaction(
                            token_in=step["token_in"],
                            token_out=step["token_out"],
                            amount_in=step["amount_in"],
                            min_amount_out=int(step["amount_out"] * 0.95),  # 5% slippage
                            to=self.web3_manager.wallet_address,
                            deadline=int(time.time() + 300)  # 5 minutes
                        )
                    else:
                        return {"success": False, "error": f"DEX {dex_name} does not support multi-hop swaps"}
                else:
                    # Standard single-hop swap
                    tx = await dex.build_swap_transaction(
                        token_in=step["token_in"],
                        token_out=step["token_out"],
                        amount_in=step["amount_in"],
                        min_amount_out=int(step["amount_out"] * 0.95),  # 5% slippage
                    to=self.web3_manager.wallet_address,
                    deadline=int(time.time() + 300)  # 5 minutes
                )
                
                transactions.append(tx)
            
            # Simulate bundle using Flashbots if available
            if use_flashbots and hasattr(self.web3_manager, 'flashbots_manager'):
                # Create a bundle
                target_block = await self.web3_manager.w3.eth.block_number + 1
                bundle_id = await self.web3_manager.flashbots_manager.create_bundle(
                    target_block=target_block,
                    transactions=transactions,
                    revert_on_fail=True
                )
                
                # Simulate the bundle
                simulation = await self.web3_manager.flashbots_manager.simulate_bundle(bundle_id)
                
                # Calculate profit
                profit_result = await self.web3_manager.flashbots_manager.calculate_bundle_profit(
                    bundle_id=bundle_id,
                    token_addresses=[path.input_token, path.output_token]
                )
                
                return {
                    "success": True,
                    "simulation": simulation,
                    "profit": profit_result,
                    "bundle_id": bundle_id
                }
            else:
                # Without Flashbots, just return the transactions
                return {
                    "success": True,
                    "transactions": transactions
                }
                
        except Exception as e:
            logger.error("Error simulating arbitrage path: %s", str(e))
            return {"success": False, "error": str(e)}
    
    async def execute_arbitrage_path(
        self,
        path: ArbitragePath,
        use_flashbots: bool = True,
        min_profit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute an arbitrage path.
        
        Args:
            path: ArbitragePath to execute
            use_flashbots: Whether to use Flashbots for execution
            min_profit: Minimum profit required (overrides path's profit calculation)
            
        Returns:
            Execution results dictionary
        """
        if not path.route:
            return {"success": False, "error": "Empty path"}
            
        try:
            # First simulate the path
            simulation = await self.simulate_arbitrage_path(path, use_flashbots)
            if not simulation["success"]:
                return simulation
                
            if use_flashbots and hasattr(self.web3_manager, 'flashbots_manager'):
                # Verify profit meets minimum threshold
                bundle_id = simulation["bundle_id"]
                profit_result = simulation["profit"]
                
                min_profit_wei = min_profit if min_profit is not None else self.min_profit_threshold
                
                if profit_result["net_profit_wei"] < min_profit_wei:
                    return {
                        "success": False,
                        "status": "unprofitable",
                        "error": f"Expected profit {profit_result['net_profit_wei']} below threshold {min_profit_wei}",
                        "profit": profit_result
                    }
                
                # Submit the bundle
                if hasattr(self.web3_manager.flashbots_manager, 'validate_and_submit_bundle'):
                    # Use advanced submission with validation
                    result = await self.web3_manager.flashbots_manager.validate_and_submit_bundle(
                        bundle_id=bundle_id,
                        token_addresses=[path.input_token, path.output_token],
                        min_profit=min_profit_wei
                    )
                else:
                    # Use regular submission
                    result = await self.web3_manager.flashbots_manager.submit_bundle(bundle_id)
                
                return {
                    "success": True,
                    "status": "submitted",
                    "result": result,
                    "profit": profit_result,
                    "bundle_id": bundle_id
                }
            else:
                # Execute transactions one by one without Flashbots
                # This is risky for arbitrage as it can get front-run
                transactions = simulation["transactions"]
                tx_hashes = []
                
                for tx in transactions:
                    tx_hash = await self.web3_manager.w3.eth.send_transaction(tx)
                    tx_hashes.append(tx_hash.hex())
                    
                return {
                    "success": True,
                    "status": "submitted",
                    "tx_hashes": tx_hashes
                }
                
        except Exception as e:
            logger.error("Error executing arbitrage path: %s", str(e))
            return {"success": False, "error": str(e)}


async def create_path_finder(dex_manager=None, web3_manager=None, config=None) -> PathFinder:
    """
    Create and initialize a PathFinder instance.
    
    Args:
        dex_manager: Optional DexManager instance
 
        web3_manager: Optional Web3Manager instance
        web3_manager: Optional Web3Manager instance
        config: Optional configuration dictionary
        
    Returns:
        Initialized PathFinder instance
    """
    try:
        # Import dependencies here to avoid circular imports
        if dex_manager is None:
            from arbitrage_bot.core.dex.dex_manager import DexManager
            from arbitrage_bot.core.web3.web3_manager import Web3Manager
            from arbitrage_bot.utils.config_loader import load_config
            
            # Load config if not provided
            if config is None:
                config = load_config()
                
            # Create web3 manager if not provided
            if web3_manager is None:
                web3_manager = Web3Manager(
                    provider_url=config.get("provider_url"),
                    chain_id=config.get("chain_id"),
                    private_key=config.get("private_key"),
                    wallet_address=config.get("wallet_address")
                )
                await web3_manager.connect()
                
            # Create dex manager if not provided
            dex_manager = DexManager(web3_manager, config)
            await dex_manager.initialize()
        
        # Get path finding config
        path_config = config.get("path_finding", {}) if config else {}
        
        # Create PathFinder instance
        path_finder = PathFinder(dex_manager, web3_manager, path_config)
        
        logger.info("Path finder created")
        return path_finder
        
    except Exception as e:
        logger.error("Failed to create path finder: %s", str(e))
        raise