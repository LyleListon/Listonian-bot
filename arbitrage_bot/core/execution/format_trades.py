"""Format trade steps for MultiPathArbitrage contract."""

from typing import List, Dict, Any, Tuple
from decimal import Decimal
from ..models.opportunity import Opportunity

def format_trade_steps(opportunity: Opportunity) -> Tuple[str, int, List[Dict[str, Any]]]:
    """
    Format an opportunity into trade steps for the MultiPathArbitrage contract.
    
    Args:
        opportunity: The arbitrage opportunity to format
        
    Returns:
        Tuple containing:
        - Flash loan token address
        - Flash loan amount
        - List of trade steps formatted for the contract
    """
    
    if opportunity.route_type == "direct":
        # Direct arbitrage between two DEXs
        return format_direct_trade(opportunity)
    elif opportunity.route_type == "triangular":
        # Triangular arbitrage across three tokens
        return format_triangular_trade(opportunity)
    else:
        raise ValueError(f"Unsupported route type: {opportunity.route_type}")

def format_direct_trade(opportunity: Opportunity) -> Tuple[str, int, List[Dict[str, Any]]]:
    """Format a direct arbitrage trade."""
    
    # Parse token addresses from pair
    token0, token1 = opportunity.token_pair.split('/')
    
    # Get DEX info
    buy_dex = opportunity.buy_dex
    sell_dex = opportunity.sell_dex
    
    # Format trade steps
    steps = [
        {
            "router": buy_dex.router_address,
            "path": [token0, token1],
            "isV3": buy_dex.is_v3,
            "amount": opportunity.buy_amount,
            "fee": buy_dex.fee if buy_dex.is_v3 else 0
        },
        {
            "router": sell_dex.router_address,
            "path": [token1, token0],
            "isV3": sell_dex.is_v3,
            "amount": 0,  # Will be output from previous step
            "fee": sell_dex.fee if sell_dex.is_v3 else 0
        }
    ]
    
    return token0, opportunity.buy_amount, steps

def format_triangular_trade(opportunity: Opportunity) -> Tuple[str, int, List[Dict[str, Any]]]:
    """Format a triangular arbitrage trade."""
    
    # Parse tokens from opportunity
    tokens = opportunity.path.split('->')
    if len(tokens) != 3:
        raise ValueError("Triangular trade must have exactly 3 tokens")
        
    # Get DEX info for each step
    dexes = opportunity.dex_path
    if len(dexes) != 3:
        raise ValueError("Triangular trade must have exactly 3 DEXes")
    
    # Format trade steps
    steps = [
        {
            "router": dexes[0].router_address,
            "path": [tokens[0], tokens[1]],
            "isV3": dexes[0].is_v3,
            "amount": opportunity.buy_amount,
            "fee": dexes[0].fee if dexes[0].is_v3 else 0
        },
        {
            "router": dexes[1].router_address,
            "path": [tokens[1], tokens[2]],
            "isV3": dexes[1].is_v3,
            "amount": 0,  # Will be output from previous step
            "fee": dexes[1].fee if dexes[1].is_v3 else 0
        },
        {
            "router": dexes[2].router_address,
            "path": [tokens[2], tokens[0]],
            "isV3": dexes[2].is_v3,
            "amount": 0,  # Will be output from previous step
            "fee": dexes[2].fee if dexes[2].is_v3 else 0
        }
    ]
    
    # Flash loan uses the first token
    return tokens[0], opportunity.buy_amount, steps

def validate_trade_steps(steps: List[Dict[str, Any]]) -> bool:
    """
    Validate trade steps for correctness.
    
    Args:
        steps: List of trade steps to validate
        
    Returns:
        True if steps are valid, False otherwise
        
    Checks:
    1. All required fields present
    2. Token paths connect properly
    3. Router addresses are valid
    4. Amounts and fees are valid
    """
    try:
        # Check all required fields
        required_fields = {'router', 'path', 'isV3', 'amount', 'fee'}
        for step in steps:
            if not all(field in step for field in required_fields):
                return False
                
            # Validate router address
            if not step['router'].startswith('0x'):
                return False
                
            # Validate path
            if len(step['path']) != 2:
                return False
            if not all(addr.startswith('0x') for addr in step['path']):
                return False
                
            # Validate amounts and fees
            if not isinstance(step['amount'], (int, float, Decimal)):
                return False
            if not isinstance(step['fee'], (int)):
                return False
                
        # Check path connections
        for i in range(len(steps) - 1):
            if steps[i]['path'][1] != steps[i + 1]['path'][0]:
                return False
                
        # Check cycle completion
        if steps[0]['path'][0] != steps[-1]['path'][1]:
            return False
            
        return True
        
    except Exception:
        return False