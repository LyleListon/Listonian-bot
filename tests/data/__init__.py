"""
Test data and fixtures.

This module provides:
1. Sample monitoring data
2. Mock DEX responses
3. Test configurations
4. Sample transactions
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Directory containing test data
DATA_DIR = Path(__file__).parent

def load_json_fixture(filename: str) -> Dict[str, Any]:
    """Load a JSON fixture file."""
    path = DATA_DIR / filename
    with open(path) as f:
        return json.load(f)

def get_monitoring_data(timestamp: Optional[str] = None) -> Dict[str, Any]:
    """Get monitoring data fixture.
    
    Args:
        timestamp: Optional specific timestamp to load
    """
    if timestamp:
        filename = f"monitoring_{timestamp}.json"
    else:
        # Use the first available file
        files = list(DATA_DIR.glob("monitoring_*.json"))
        if not files:
            raise FileNotFoundError("No monitoring data fixtures found")
        filename = files[0].name
    
    return load_json_fixture(filename)

def get_dex_response(dex_name: str) -> Dict[str, Any]:
    """Get mock DEX response data."""
    return load_json_fixture(f"dex_response_{dex_name}.json")

def get_test_config() -> Dict[str, Any]:
    """Get test configuration."""
    return load_json_fixture("test_config.json")

def get_sample_transactions() -> List[Dict[str, Any]]:
    """Get sample transaction data."""
    return load_json_fixture("sample_transactions.json")