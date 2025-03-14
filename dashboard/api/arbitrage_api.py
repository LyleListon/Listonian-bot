"""
Arbitrage System API

This module provides FastAPI endpoints for the arbitrage system dashboard.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

# Define router
router = APIRouter(prefix="/api/arbitrage", tags=["arbitrage"])

# Define models for API responses
class ArbitrageOpportunityResponse(BaseModel):
    id: str
    strategy_type: str
    input_token: str
    output_token: str
    expected_profit: float
    confidence_score: float
    status: str
    timestamp: float

class ExecutionResultResponse(BaseModel):
    opportunity_id: str
    success: bool
    transaction_hash: Optional[str]
    status: str
    gas_used: Optional[int]
    actual_profit: Optional[float]
    timestamp: float

class PerformanceMetricsResponse(BaseModel):
    opportunities_found: int
    executed: int
    successful: int
    total_profit_eth: float
    success_rate: float
    average_gas_used: Optional[int]
    average_execution_time: Optional[float]
    timestamp: float

class Web3Settings(BaseModel):
    chain_id: int
    rpc_url: str
    wallet_key: str
    providers: Dict[str, Any]
    alchemy: Dict[str, Any]

class WalletSettings(BaseModel):
    min_eth_balance: str
    max_eth_balance: str
    target_token_ratios: Dict[str, float]
    rebalance_threshold: float
    profit_withdrawal: Dict[str, Any]
    balance_check_interval: int

class TokenSettings(BaseModel):
    address: str
    decimals: int

class DexSettings(BaseModel):
    factory: str
    router: str
    version: str
    fee: int
    quoter: Optional[str] = None
    pool_deployer: Optional[str] = None
    enabled: Optional[bool] = None

class PathFinderSettings(BaseModel):
    max_path_length: int
    min_profit_threshold: str
    max_paths_to_check: int
    min_liquidity_ratio: float
    max_price_impact: float
    max_parallel_requests: int
    parallel_search: bool
    cache_ttl: int

class FlashLoanSettings(BaseModel):
    enabled: bool
    use_flashbots: bool
    min_profit_threshold_eth: float
    max_trade_size: str
    slippage_tolerance: int
    transaction_timeout: int
    aave_pool: str
    max_parallel_pools: int
    min_liquidity_ratio: float
    gas_buffer: float

class FlashbotsSettings(BaseModel):
    relay_url: str
    auth_key: str
    min_profit: str
    max_gas_price: str

class MevProtectionSettings(BaseModel):
    enabled: bool
    use_flashbots: bool
    max_bundle_size: int
    max_blocks_ahead: int
    min_priority_fee: str
    max_priority_fee: str
    sandwich_detection: bool
    frontrun_detection: bool
    backrun_detection: bool
    time_bandit_detection: bool
    profit_threshold: str
    gas_threshold: str
    confidence_threshold: str
    adaptive_gas: bool

class ScanSettings(BaseModel):
    interval: float
    amount_wei: str
    max_paths: int

class RateLimitSettings(BaseModel):
    requests_per_second: int
    max_backoff: float
    batch_size: int
    cache_ttl: int

class Settings(BaseModel):
    web3: Web3Settings
    wallet: WalletSettings
    tokens: Dict[str, TokenSettings]
    dexes: Dict[str, DexSettings]
    path_finder: PathFinderSettings
    flash_loan: FlashLoanSettings
    flashbots: FlashbotsSettings
    mev_protection: MevProtectionSettings
    scan: ScanSettings
    monitoring: Dict[str, Any]
    rate_limits: RateLimitSettings

# Global variable to store the arbitrage system instance
_arbitrage_system = None

def get_arbitrage_system():
    """Get the global arbitrage system instance."""
    if _arbitrage_system is None:
        raise HTTPException(status_code=503, detail="Arbitrage system not initialized")
    return _arbitrage_system

def set_arbitrage_system(arbitrage_system):
    """Set the global arbitrage system instance."""
    global _arbitrage_system
    _arbitrage_system = arbitrage_system
    logger.info("Arbitrage system set in API")

@router.get("/opportunities", response_model=List[ArbitrageOpportunityResponse])
async def get_opportunities(
    max_results: int = Query(10, ge=1, le=100),
    min_profit: float = Query(0.001, ge=0),
    arbitrage_system=Depends(get_arbitrage_system)
):
    """Get recent arbitrage opportunities."""
    try:
        # Get opportunities from the arbitrage system
        opportunities = await arbitrage_system.get_recent_opportunities(
            max_results=max_results, 
            min_profit_eth=min_profit
        )
        
        # Convert to response format
        return [
            ArbitrageOpportunityResponse(
                id=opp.id,
                strategy_type=opp.strategy_type.value,
                input_token=opp.route.input_token_address,
                output_token=opp.route.output_token_address,
                expected_profit=opp.expected_profit / 10**18,  # Convert to ETH
                confidence_score=opp.confidence_score,
                status=opp.status.value,
                timestamp=opp.timestamp
            )
            for opp in opportunities
        ]
    except Exception as e:
        logger.error(f"Error getting opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions", response_model=List[ExecutionResultResponse])
async def get_executions(
    max_results: int = Query(10, ge=1, le=100),
    arbitrage_system=Depends(get_arbitrage_system)
):
    """Get recent arbitrage executions."""
    try:
        # Get executions from the arbitrage system
        executions = await arbitrage_system.get_recent_executions(max_results=max_results)
        
        # Convert to response format
        return [
            ExecutionResultResponse(
                opportunity_id=execution.opportunity_id,
                success=execution.success,
                transaction_hash=execution.transaction_hash,
                status=execution.status.value,
                gas_used=execution.gas_used,
                actual_profit=execution.actual_profit / 10**18 if execution.actual_profit else None,  # Convert to ETH
                timestamp=execution.timestamp
            )
            for execution in executions
        ]
    except Exception as e:
        logger.error(f"Error getting executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_metrics(arbitrage_system=Depends(get_arbitrage_system)):
    """Get arbitrage system performance metrics."""
    try:
        # Get metrics from the arbitrage system
        metrics = await arbitrage_system.get_performance_metrics()
        
        # Convert to response format
        return PerformanceMetricsResponse(
            opportunities_found=metrics.get("opportunities_found", 0),
            executed=metrics.get("executed", 0),
            successful=metrics.get("successful", 0),
            total_profit_eth=metrics.get("total_profit_eth", 0.0),
            success_rate=metrics.get("success_rate", 0.0),
            average_gas_used=metrics.get("average_gas_used"),
            average_execution_time=metrics.get("average_execution_time"),
            timestamp=metrics.get("timestamp", 0.0)
        )
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute/{opportunity_id}")
async def execute_opportunity(
    opportunity_id: str,
    background_tasks: BackgroundTasks,
    strategy_id: str = "standard",
    arbitrage_system=Depends(get_arbitrage_system)
):
    """Execute an arbitrage opportunity."""
    try:
        # Get the opportunity
        opportunity = await arbitrage_system.get_opportunity_by_id(opportunity_id)
        if not opportunity:
            raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found")
        
        # Execute in background to avoid blocking API
        background_tasks.add_task(
            arbitrage_system.execute_opportunity,
            opportunity=opportunity,
            strategy_id=strategy_id
        )
        
        return {"status": "execution_started", "opportunity_id": opportunity_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing opportunity {opportunity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start")
async def start_arbitrage_system(arbitrage_system=Depends(get_arbitrage_system)):
    """Start the arbitrage system."""
    try:
        if arbitrage_system.is_running:
            return {"status": "already_running"}
        
        await arbitrage_system.start()
        return {"status": "started"}
    except Exception as e:
        logger.error(f"Error starting arbitrage system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_arbitrage_system(arbitrage_system=Depends(get_arbitrage_system)):
    """Stop the arbitrage system."""
    try:
        if not arbitrage_system.is_running:
            return {"status": "already_stopped"}
        
        await arbitrage_system.stop()
        return {"status": "stopped"}
    except Exception as e:
        logger.error(f"Error stopping arbitrage system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_system_status(arbitrage_system=Depends(get_arbitrage_system)):
    """Get the arbitrage system status."""
    try:
        return {
            "running": arbitrage_system.is_running,
            "discovery_enabled": arbitrage_system.discovery_enabled,
            "auto_execute": arbitrage_system.auto_execute_enabled,
            "uptime_seconds": arbitrage_system.uptime_seconds
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings", response_model=Settings)
async def get_settings():
    """Get all system settings."""
    try:
        # Load settings from config file
        config_path = os.environ.get("CONFIG_PATH", "configs/default_config.json")
        with open(config_path, "r") as f:
            settings = json.load(f)
        return Settings(**settings)
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings/{section}")
async def update_settings(section: str, settings: Dict[str, Any]):
    """Update settings for a specific section."""
    valid_sections = {"web3", "wallet", "tokens", "dexes", "path_finder", "flash_loan", "flashbots", "mev_protection", "scan", "monitoring", "rate_limits"}
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section. Must be one of: {valid_sections}")

    try:
        # Load current settings
        config_path = os.environ.get("CONFIG_PATH", "configs/default_config.json")
        with open(config_path, "r") as f:
            current_settings = json.load(f)

        # Update specified section
        current_settings[section] = settings

        # Validate settings using Pydantic model
        Settings(**current_settings)

        # Save updated settings
        with open(config_path, "w") as f:
            json.dump(current_settings, f, indent=2)

        return {"status": "success", "message": f"{section} settings updated"}
    except Exception as e:
        logger.error(f"Error updating {section} settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings/{section}/reset")
async def reset_settings(section: str):
    """Reset settings for a specific section to default values."""
    valid_sections = {"web3", "wallet", "tokens", "dexes", "path_finder", "flash_loan", "flashbots", "mev_protection", "scan", "monitoring", "rate_limits"}
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section. Must be one of: {valid_sections}")

    try:
        # Load default settings
        with open("configs/default_config.json", "r") as f:
            default_settings = json.load(f)

        # Load current settings
        config_path = os.environ.get("CONFIG_PATH", "configs/default_config.json")
        if config_path != "configs/default_config.json":
            with open(config_path, "r") as f:
                current_settings = json.load(f)
        else:
            current_settings = default_settings.copy()

        # Reset specified section
        if section in default_settings:
            current_settings[section] = default_settings[section]
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Section {section} not found in default settings"
            )

        # Validate settings using Pydantic model
        Settings(**current_settings)

        # Save updated settings
        with open(config_path, "w") as f:
            json.dump(current_settings, f, indent=2)

        return {"status": "success", "message": f"{section} settings reset to default"}
    except Exception as e:
        logger.error(f"Error resetting {section} settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))