"""MCP Server interaction utilities."""

import logging
from typing import Dict, Any, List, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)

async def _use_mcp_tool(server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Direct MCP tool call implementation.
    
    Args:
        server_name (str): Name of the MCP server
        tool_name (str): Name of the tool to use
        arguments (Dict[str, Any]): Tool arguments
        
    Returns:
        Any: Tool response
    """
    try:
        if server_name == "crypto-price" and tool_name == "get_prices":
            # Mock response for testing
            return {
                "ethereum": {"price_usd": 3370.0, "change_24h": 4.58},
                "usd-coin": {"price_usd": 1.0, "change_24h": 0.0},
                "dai": {"price_usd": 1.0, "change_24h": 0.0}
            }
        elif server_name == "market-analysis":
            # Mock response for testing
            return {
                "trend": "sideways",
                "trend_strength": 0.5,
                "trend_duration": 3600,
                "volatility": 0.1,
                "volume_24h": 1000000,
                "liquidity": 1000000,
                "volatility_24h": 0.1,
                "price_impact": 0.001,
                "confidence": 0.8
            }
        else:
            logger.warning(f"Unknown MCP tool: {server_name}/{tool_name}")
            return None
    except Exception as e:
        logger.error(f"Error in MCP tool {tool_name} on {server_name}: {e}")
        return None

async def use_mcp_tool(server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Use an MCP tool.
    
    Args:
        server_name (str): Name of the MCP server
        tool_name (str): Name of the tool to use
        arguments (Dict[str, Any]): Tool arguments
        
    Returns:
        Any: Tool response
    """
    try:
        # For crypto-price server, handle price data
        if server_name == "crypto-price" and tool_name == "get_prices":
            response = await _use_mcp_tool(server_name, tool_name, arguments)
            if response and 'prices' in response:
                prices = {}
                for coin, data in response['prices'].items():
                    if isinstance(data, dict) and 'price_usd' in data:
                        prices[coin] = data['price_usd']
                return prices
            return None
            
        # For other tools, pass through to MCP
        return await _use_mcp_tool(server_name, tool_name, arguments)
        
    except Exception as e:
        logger.error(f"Failed to use MCP tool {tool_name} on {server_name}: {e}")
        raise

async def validate_prices(token_addresses: List[str], amounts_in: List[int] = None, amounts_out: List[int] = None, decimals: List[int] = None) -> Dict[str, Dict[str, Any]]:
    """
    Validate token prices using crypto-price MCP.
    
    Args:
        token_addresses (List[str]): List of token addresses to validate
        
    Returns:
        Dict[str, Dict[str, float]]: Price data for each token
    """
    try:
        # Map addresses to MCP token IDs and track indices
        address_to_id = {
            "0x4200000000000000000000000000000000000006": "ethereum",  # WETH
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": "usd-coin",  # USDC
            "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb": "dai"       # DAI
        }
        
        # Get token IDs and track indices for validation
        token_data = []
        for i, address in enumerate(token_addresses):
            normalized_address = address.lower()
            normalized_map = {addr.lower(): token_id for addr, token_id in address_to_id.items()}
            logger.info(f"Looking up address: {normalized_address}")
            logger.info(f"Available addresses: {list(normalized_map.keys())}")
            if normalized_address in normalized_map:
                logger.info(f"Found token ID: {normalized_map[normalized_address]}")
                token_data.append({
                    'id': normalized_map[normalized_address],
                    'address': address,
                    'amount_in': amounts_in[i] if amounts_in else None,
                    'amount_out': amounts_out[i] if amounts_out else None,
                    'decimals': decimals[i] if decimals else 18
                })
            else:
                logger.warning(f"Address not found in mapping: {normalized_address}")
        
        if not token_data:
            logger.warning("No known tokens to validate prices for")
            return {}
            
        logger.info(f"Token data: {token_data}")
            
        # Get current prices from MCP server
        request = {
            "coins": [t['id'] for t in token_data],
            "include_24h_change": True
        }
        logger.info(f"Requesting live prices: {request}")
        response = await use_mcp_tool(
            "crypto-price",
            "get_prices",
            request
        )
        logger.info(f"Live price response: {response}")
        if not response or not isinstance(response, dict) or 'prices' not in response:
            logger.error("Invalid response from crypto-price MCP tool")
            return {}
        
        # Validate prices and add market analysis if needed
        result = {}
        if isinstance(response, dict) and 'prices' in response:
            prices = response['prices']
            for token in token_data:
                token_id = token['id']
                if token_id not in prices:
                    logger.warning(f"No price data for {token_id}")
                    continue
                    
                token_data = prices[token_id]
                if not isinstance(token_data, dict) or 'price_usd' not in token_data:
                    logger.warning(f"Invalid price data format for {token_id}")
                    continue
                    
                result[token['address']] = {
                    'price': token_data['price_usd'],
                    'volume_24h': token_data.get('volume_24h', 0),
                    'change_24h': token_data.get('change_24h', 0),
                    'validation': {'is_valid': True, 'reason': None}
                }
            
            # If we have amounts, validate the implied price
            if token['amount_in'] and token['amount_out']:
                # Convert amounts to decimals
                amount_in_decimal = token['amount_in'] / (10 ** token['decimals'])  # 1 ETH
                amount_out_decimal = token['amount_out'] / (10 ** 6)  # USDC has 6 decimals for USD
                implied_price = amount_out_decimal / amount_in_decimal
                market_price = float(token_data['price_usd'])
                
                # Check deviation
                deviation = abs(implied_price - market_price) / market_price
                if deviation > 0.05:  # 5% threshold
                    logger.warning(
                        f"Price deviation detected:\n"
                        f"  Token: {token_id}\n"
                        f"  Implied: ${implied_price:,.2f}\n"
                        f"  Market: ${market_price:,.2f}\n"
                        f"  Deviation: {deviation*100:.1f}%"
                    )
                    
                    # Get market analysis
                    market_response = await use_mcp_tool(
                        "market-analysis",
                        "assess_market_conditions",
                        {
                            "token": token_id,
                            "metrics": ["volatility", "volume", "trend"]
                        }
                    )
                    
                    # Add market conditions to result
                    result[token['address']]['market_conditions'] = market_response
                    
                    # Validate based on market conditions
                    volatility = market_response.get("metrics", {}).get("volatility", 0)
                    trend = market_response.get("metrics", {}).get("trend", "sideways")
                    
                    if volatility > 0.5 or trend == "bearish":
                        result[token['address']]['validation'] = {
                            'is_valid': False,
                            'reason': "Unfavorable market conditions"
                        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to validate prices: {e}")
        raise

async def assess_opportunity(
    token_pair: Tuple[str, str],
    profit_usd: float,
    volume_usd: float
) -> Dict[str, Any]:
    """
    Assess an arbitrage opportunity using market-analysis MCP.
    
    Args:
        token_pair (Tuple[str, str]): Token addresses in the pair
        profit_usd (float): Expected profit in USD
        volume_usd (float): Trade volume in USD
        
    Returns:
        Dict[str, Any]: Opportunity assessment including risk factors
    """
    try:
        # Get market conditions for both tokens
        conditions = []
        for token in token_pair:
            response = await use_mcp_tool(
                "market-analysis",
                "assess_market_conditions",
                {
                    "token": token,
                    "metrics": ["volatility", "volume", "liquidity", "trend"]
                }
            )
            conditions.append(response)
            
        # Analyze opportunity
        analysis = await use_mcp_tool(
            "market-analysis",
            "analyze_opportunities",
            {
                "token": token_pair[0],
                "days": 1,
                "min_profit_threshold": profit_usd
            }
        )
        
        # Combine all data
        assessment = {
            "market_conditions": conditions,
            "opportunity_analysis": analysis,
            "risk_factors": {
                "volatility": max(c.get("metrics", {}).get("volatility", 0) for c in conditions),
                "volume_ratio": volume_usd / min(c.get("metrics", {}).get("volume", float('inf')) for c in conditions),
                "trend_alignment": all(c.get("metrics", {}).get("trend") == "up" for c in conditions)
            }
        }
        
        return assessment
        
    except Exception as e:
        logger.error(f"Failed to assess opportunity: {e}")
        raise

async def evaluate_risk(assessment: Dict[str, Any], config: Dict[str, Any]) -> Tuple[bool, float]:
    """
    Evaluate risk level of an opportunity based on market assessment.
    
    Args:
        assessment (Dict[str, Any]): Opportunity assessment from assess_opportunity
        config (Dict[str, Any]): Trading configuration with risk thresholds
        
    Returns:
        Tuple[bool, float]: (is_safe, confidence_score)
    """
    try:
        # Get risk thresholds from config
        thresholds = config.get("trading", {}).get("safety", {}).get("validation_thresholds", {})
        
        # Extract risk factors
        volatility = assessment["risk_factors"]["volatility"]
        volume_ratio = assessment["risk_factors"]["volume_ratio"]
        trend_alignment = assessment["risk_factors"]["trend_alignment"]
        
        # Calculate confidence score (0-1)
        confidence = 1.0
        
        # Adjust for volatility (high volatility reduces confidence)
        if volatility > thresholds.get("max_volatility", 0.5):
            confidence *= 0.5
        elif volatility > thresholds.get("med_volatility", 0.3):
            confidence *= 0.7
            
        # Adjust for volume (low volume ratio reduces confidence)
        if volume_ratio > thresholds.get("max_volume_share", 0.1):
            confidence *= 0.6
            
        # Adjust for trend
        if not trend_alignment:
            confidence *= 0.8
            
        # Check if meets minimum confidence
        is_safe = confidence >= thresholds.get("min_confidence", 0.8)
        
        return is_safe, confidence
        
    except Exception as e:
        logger.error(f"Failed to evaluate risk: {e}")
        raise

async def use_market_analysis(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use the market analysis MCP server.
    
    Args:
        method (str): Method name to call
        params (Dict[str, Any]): Parameters for the method
        
    Returns:
        Dict[str, Any]: Response from the market analysis server
    """
    try:
        response = await use_mcp_tool(
            "market-analysis",
            method,
            params
        )
        return response
        
    except Exception as e:
        logger.error(f"Failed to use market analysis server: {e}")
        raise
