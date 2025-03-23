"""Schema validation for memory bank data structures.

This module provides schema definitions and validation for memory bank data,
ensuring consistency and integrity of stored information.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, TypedDict

from jsonschema import validate, ValidationError, Draft7Validator

logger = logging.getLogger(__name__)

class OpportunityData(TypedDict):
    """Type definition for arbitrage opportunity data."""
    token_pair: str
    dex_1: str
    dex_2: str
    potential_profit: float
    confidence: float

class TradeData(TypedDict):
    """Type definition for trade data."""
    timestamp: str
    opportunity: OpportunityData
    success: bool
    net_profit: float
    gas_cost: float
    tx_hash: str
    error: Optional[str]

# Schema Definitions
OPPORTUNITY_SCHEMA = {
    "type": "object",
    "required": [
        "token_pair",
        "dex_1",
        "dex_2",
        "potential_profit",
        "confidence"
    ],
    "properties": {
        "token_pair": {"type": "string"},
        "dex_1": {"type": "string"},
        "dex_2": {"type": "string"},
        "potential_profit": {"type": "number", "minimum": 0},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    }
}

TRADE_SCHEMA = {
    "type": "object",
    "required": [
        "timestamp",
        "opportunity",
        "success",
        "net_profit",
        "gas_cost",
        "tx_hash",
        "error"
    ],
    "properties": {
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "opportunity": OPPORTUNITY_SCHEMA,
        "success": {"type": "boolean"},
        "net_profit": {"type": "number"},
        "gas_cost": {"type": "number", "minimum": 0},
        "tx_hash": {"type": "string"},
        "error": {"type": ["string", "null"]}
    }
}

METRICS_SCHEMA = {
    "type": "object",
    "required": [
        "gas_price",
        "network_status",
        "uptime",
        "performance"
    ],
    "properties": {
        "gas_price": {"type": "number", "minimum": 0},
        "network_status": {"type": "string"},
        "uptime": {"type": "number", "minimum": 0},
        "performance": {
            "type": "object",
            "required": [
                "total_profit",
                "success_rate",
                "average_profit",
                "profit_trend"
            ],
            "properties": {
                "total_profit": {"type": "number"},
                "success_rate": {"type": "number", "minimum": 0, "maximum": 1},
                "average_profit": {"type": "number"},
                "profit_trend": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["timestamp", "profit"],
                        "properties": {
                            "timestamp": {"type": "string", "format": "date-time"},
                            "profit": {"type": "number"}
                        }
                    }
                }
            }
        }
    }
}

MEMORY_BANK_STATUS_SCHEMA = {
    "type": "object",
    "required": [
        "last_check",
        "health_status",
        "integrity_checks",
        "alerts"
    ],
    "properties": {
        "last_check": {"type": "string", "format": "date-time"},
        "health_status": {
            "type": "string",
            "enum": ["healthy", "degraded", "error"]
        },
        "integrity_checks": {
            "type": "object",
            "required": ["trades", "metrics", "state"],
            "properties": {
                "trades": {
                    "type": "object",
                    "required": ["status", "file_count", "last_validated"],
                    "properties": {
                        "status": {"type": "string", "enum": ["ok", "error"]},
                        "file_count": {"type": "integer", "minimum": 0},
                        "last_validated": {"type": "string", "format": "date-time"}
                    }
                },
                "metrics": {
                    "type": "object",
                    "required": ["status", "schema_valid", "last_updated"],
                    "properties": {
                        "status": {"type": "string", "enum": ["ok", "error"]},
                        "schema_valid": {"type": "boolean"},
                        "last_updated": {"type": "string", "format": "date-time"}
                    }
                },
                "state": {
                    "type": "object",
                    "required": ["status", "last_snapshot"],
                    "properties": {
                        "status": {"type": "string", "enum": ["ok", "error"]},
                        "last_snapshot": {"type": "string", "format": "date-time"}
                    }
                }
            }
        },
        "alerts": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "timestamp",
                    "level",
                    "message",
                    "component"
                ],
                "properties": {
                    "timestamp": {"type": "string", "format": "date-time"},
                    "level": {
                        "type": "string",
                        "enum": ["info", "warning", "error"]
                    },
                    "message": {"type": "string"},
                    "component": {"type": "string"}
                }
            }
        }
    }
}

class SchemaValidator:
    """Validates data against defined schemas."""

    def __init__(self):
        self._initialized = False
        self._lock = asyncio.Lock()
        self._validators = {
            'trade': Draft7Validator(TRADE_SCHEMA),
            'metrics': Draft7Validator(METRICS_SCHEMA),
            'status': Draft7Validator(MEMORY_BANK_STATUS_SCHEMA)
        }

    async def initialize(self) -> None:
        """Initialize the schema validator."""
        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing schema validator")

            try:
                # Pre-compile all schemas
                for name, validator in self._validators.items():
                    validator.check_schema(validator.schema)

                self._initialized = True
                logger.info("Schema validator initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize schema validator: {e}")
                raise

    async def validate_trade(self, data: Dict[str, Any]) -> None:
        """Validate trade data against the trade schema."""
        if not self._initialized:
            raise RuntimeError("Schema validator not initialized")

        try:
            self._validators['trade'].validate(data)
        except ValidationError as e:
            logger.error(f"Trade validation error: {e}")
            raise

    async def validate_metrics(self, data: Dict[str, Any]) -> None:
        """Validate metrics data against the metrics schema."""
        if not self._initialized:
            raise RuntimeError("Schema validator not initialized")

        try:
            self._validators['metrics'].validate(data)
        except ValidationError as e:
            logger.error(f"Metrics validation error: {e}")
            raise

    async def validate_memory_bank_status(self, data: Dict[str, Any]) -> None:
        """Validate memory bank status data against the status schema."""
        if not self._initialized:
            raise RuntimeError("Schema validator not initialized")

        try:
            self._validators['status'].validate(data)
        except ValidationError as e:
            logger.error(f"Status validation error: {e}")
            raise

    async def validate_file(self, file_path: Path, schema_type: str) -> None:
        """Validate a JSON file against a specified schema."""
        if not self._initialized:
            raise RuntimeError("Schema validator not initialized")

        if schema_type not in self._validators:
            raise ValueError(f"Unknown schema type: {schema_type}")

        try:
            async with self._lock:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self._validators[schema_type].validate(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {file_path}: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error in {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error validating {file_path}: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up validator resources."""
        async with self._lock:
            if not self._initialized:
                return

            logger.info("Cleaning up schema validator")

            try:
                self._initialized = False
                logger.info("Schema validator cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up schema validator: {e}")
                raise