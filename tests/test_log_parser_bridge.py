"""
Tests for the Log Parser Bridge component.
"""

import asyncio
import logging
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from arbitrage_bot.core import (
    LogParserBridge,
    ConfigLoader,
    ParserBridgeConfig,
    OpportunityTracker
)

# Test data
SAMPLE_CONFIG = """
parser_bridge:
  watch_directory: "./logs"
  update_frequency: 1.0
  max_batch_size: 1000
  file_patterns:
    - "opportunities_*.log"
    - "execution_*.log"
  parser_rules:
    opportunity:
      pattern: "Found opportunity.*DEX: (.*) -> (.*), Token: (.*), Price diff: ([\\d.]+)%, Amount: ([\\d.]+) ETH, Expected profit: \\$([\\d.]+)"
      groups:
        - dex_from
        - dex_to
        - token
        - price_diff
        - amount
        - profit
    execution:
      pattern: "Trade execution.*Hash: (0x[a-fA-F0-9]+), Status: (\\w+), Profit: \\$([\\d.]+), Gas cost: \\$([\\d.]+)"
      groups:
        - tx_hash
        - status
        - profit
        - gas_cost
  error_handling:
    max_retries: 3
    retry_delay: 1.0
    log_errors: true
"""

SAMPLE_OPPORTUNITY_LOG = """
2025-03-08 05:30:00,000 - opportunities - INFO - Found opportunity:
  DEX: Uniswap V3 -> SushiSwap
  Token: WETH
  Price diff: 0.25%
  Amount: 1.5 ETH
  Expected profit: $25.50
"""

SAMPLE_EXECUTION_LOG = """
2025-03-08 05:30:01,000 - execution - INFO - Trade execution:
  Hash: 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
  Status: success
  Profit: $25.50
  Gas cost: $5.50
"""

@pytest.fixture
async def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
async def temp_config_file(temp_log_dir):
    """Create a temporary config file."""
    config_path = temp_log_dir / "config.yaml"
    config_content = SAMPLE_CONFIG.replace("./logs", str(temp_log_dir))
    config_path.write_text(config_content)
    return config_path

@pytest.fixture
async def opportunity_tracker():
    """Create an OpportunityTracker instance."""
    return OpportunityTracker()

@pytest.fixture
async def log_parser_bridge(temp_log_dir, opportunity_tracker):
    """Create a LogParserBridge instance."""
    bridge = LogParserBridge(
        log_dir=temp_log_dir,
        opportunity_tracker=opportunity_tracker
    )
    yield bridge
    await bridge.stop()

@pytest.mark.asyncio
async def test_config_loader(temp_config_file):
    """Test loading configuration from file."""
    config = await ConfigLoader.load_config(temp_config_file)
    assert isinstance(config, ParserBridgeConfig)
    assert len(config.file_patterns) == 2
    assert len(config.parser_rules) == 2
    assert config.parser_rules["opportunity"].groups == [
        "dex_from", "dex_to", "token", "price_diff", "amount", "profit"
    ]

@pytest.mark.asyncio
async def test_log_parser_bridge_initialization(log_parser_bridge):
    """Test LogParserBridge initialization."""
    assert not log_parser_bridge.is_running
    assert log_parser_bridge.update_task is None
    assert isinstance(log_parser_bridge.patterns, dict)
    assert len(log_parser_bridge.patterns) == 2

@pytest.mark.asyncio
async def test_opportunity_parsing(temp_log_dir, log_parser_bridge):
    """Test parsing opportunity logs."""
    # Create and write to opportunity log file
    log_file = temp_log_dir / "opportunities_test.log"
    log_file.write_text(SAMPLE_OPPORTUNITY_LOG)
    
    # Start the parser
    await log_parser_bridge.start()
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Check if opportunity was tracked
    opportunities = log_parser_bridge.opportunity_tracker.get_opportunities(limit=1)
    assert len(opportunities) == 1
    opp = opportunities[0]
    assert opp["source_dex"] == "Uniswap V3"
    assert opp["target_dex"] == "SushiSwap"
    assert opp["token"] == "WETH"
    assert opp["amount"] == 1.5
    assert opp["profit_usd"] == 25.50

@pytest.mark.asyncio
async def test_execution_parsing(temp_log_dir, log_parser_bridge):
    """Test parsing execution logs."""
    # Create and write to execution log file
    log_file = temp_log_dir / "execution_test.log"
    log_file.write_text(SAMPLE_EXECUTION_LOG)
    
    # Start the parser
    await log_parser_bridge.start()
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Check if execution was tracked
    executions = log_parser_bridge.opportunity_tracker.get_opportunities(limit=1)
    assert len(executions) == 1
    exec = executions[0]
    assert exec["tx_hash"] == "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    assert exec["status"] == "success"
    assert exec["profit_usd"] == 25.50
    assert exec["gas_cost_usd"] == 5.50
    assert exec["net_profit_usd"] == 20.00

@pytest.mark.asyncio
async def test_file_watching(temp_log_dir, log_parser_bridge):
    """Test file watching functionality."""
    await log_parser_bridge.start()
    
    # Create new log file after parser has started
    log_file = temp_log_dir / "opportunities_new.log"
    log_file.write_text(SAMPLE_OPPORTUNITY_LOG)
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Check if opportunity was tracked
    opportunities = log_parser_bridge.opportunity_tracker.get_opportunities(limit=1)
    assert len(opportunities) == 1

@pytest.mark.asyncio
async def test_error_handling(temp_log_dir, log_parser_bridge):
    """Test error handling in parser."""
    # Create log file with invalid format
    log_file = temp_log_dir / "opportunities_invalid.log"
    log_file.write_text("Invalid log format that shouldn't crash the parser\n")
    
    # Start parser
    await log_parser_bridge.start()
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Parser should still be running
    assert log_parser_bridge.is_running
    
    # Add valid log entry
    log_file.write_text(SAMPLE_OPPORTUNITY_LOG)
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Check if valid opportunity was tracked
    opportunities = log_parser_bridge.opportunity_tracker.get_opportunities(limit=1)
    assert len(opportunities) == 1

@pytest.mark.asyncio
async def test_graceful_shutdown(log_parser_bridge):
    """Test graceful shutdown of parser."""
    await log_parser_bridge.start()
    assert log_parser_bridge.is_running
    
    await log_parser_bridge.stop()
    assert not log_parser_bridge.is_running
    assert log_parser_bridge.update_task is None
    
    # Ensure observer is stopped
    assert not log_parser_bridge.observer.is_alive()