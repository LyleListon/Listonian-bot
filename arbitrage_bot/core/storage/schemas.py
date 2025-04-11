"""Common JSON schemas for data validation."""

# Trade schema for storing executed trades
TRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "timestamp": {"type": "number"},
        "pair": {"type": "string"},
        "dex": {"type": "string"},
        "amount": {"type": "number"},
        "price": {"type": "number"},
        "side": {"type": "string", "enum": ["buy", "sell"]},
        "gas_price": {"type": "number"},
        "gas_used": {"type": "number"},
        "transaction_hash": {"type": "string"},
        "status": {"type": "string", "enum": ["pending", "completed", "failed"]},
        "profit_loss": {"type": "number"},
        "error": {"type": "string", "nullable": True},
    },
    "required": ["id", "timestamp", "pair", "dex", "amount", "price", "side", "status"],
}

# Opportunity schema for storing arbitrage opportunities
OPPORTUNITY_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "timestamp": {"type": "number"},
        "pair": {"type": "string"},
        "buy_dex": {"type": "string"},
        "sell_dex": {"type": "string"},
        "buy_price": {"type": "number"},
        "sell_price": {"type": "number"},
        "amount": {"type": "number"},
        "profit": {"type": "number"},
        "gas_estimate": {"type": "number"},
        "net_profit": {"type": "number"},
        "executed": {"type": "boolean"},
        "execution_id": {"type": "string", "nullable": True},
    },
    "required": [
        "id",
        "timestamp",
        "pair",
        "buy_dex",
        "sell_dex",
        "buy_price",
        "sell_price",
        "amount",
        "profit",
        "gas_estimate",
        "net_profit",
        "executed",
    ],
}

# Market data schema for storing price and liquidity information
MARKET_DATA_SCHEMA = {
    "type": "object",
    "properties": {
        "timestamp": {"type": "number"},
        "pair": {"type": "string"},
        "dex": {"type": "string"},
        "price": {"type": "number"},
        "liquidity": {"type": "number"},
        "volume_24h": {"type": "number"},
        "high_24h": {"type": "number"},
        "low_24h": {"type": "number"},
        "price_change_24h": {"type": "number"},
    },
    "required": ["timestamp", "pair", "dex", "price", "liquidity"],
}

# Configuration schema for storing bot settings
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "network": {
            "type": "object",
            "properties": {
                "chain_id": {"type": "integer"},
                "rpc_url": {"type": "string"},
                "ws_url": {"type": "string", "nullable": True},
                "explorer_url": {"type": "string"},
            },
            "required": ["chain_id", "rpc_url", "explorer_url"],
        },
        "trading": {
            "type": "object",
            "properties": {
                "min_profit": {"type": "number"},
                "max_slippage": {"type": "number"},
                "gas_limit": {"type": "integer"},
                "max_gas_price": {"type": "number"},
                "retry_attempts": {"type": "integer"},
                "retry_delay": {"type": "integer"},
            },
            "required": [
                "min_profit",
                "max_slippage",
                "gas_limit",
                "max_gas_price",
                "retry_attempts",
                "retry_delay",
            ],
        },
        "monitoring": {
            "type": "object",
            "properties": {
                "update_interval": {"type": "integer"},
                "price_deviation_threshold": {"type": "number"},
                "liquidity_threshold": {"type": "number"},
                "gas_price_threshold": {"type": "number"},
            },
            "required": [
                "update_interval",
                "price_deviation_threshold",
                "liquidity_threshold",
                "gas_price_threshold",
            ],
        },
        "dexes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "enabled": {"type": "boolean"},
                    "factory_address": {"type": "string"},
                    "router_address": {"type": "string"},
                    "fee_tiers": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["name", "enabled", "factory_address", "router_address"],
            },
        },
        "tokens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "address": {"type": "string"},
                    "decimals": {"type": "integer"},
                    "min_amount": {"type": "number"},
                    "max_amount": {"type": "number"},
                },
                "required": ["symbol", "address", "decimals"],
            },
        },
    },
    "required": ["version", "network", "trading", "monitoring", "dexes", "tokens"],
}

# Performance metrics schema for storing bot performance data
PERFORMANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "timestamp": {"type": "number"},
        "period": {"type": "string", "enum": ["hourly", "daily", "weekly", "monthly"]},
        "total_trades": {"type": "integer"},
        "successful_trades": {"type": "integer"},
        "failed_trades": {"type": "integer"},
        "total_profit": {"type": "number"},
        "total_loss": {"type": "number"},
        "net_profit": {"type": "number"},
        "total_gas_used": {"type": "number"},
        "average_profit_per_trade": {"type": "number"},
        "win_rate": {"type": "number"},
        "average_execution_time": {"type": "number"},
        "opportunities_found": {"type": "integer"},
        "opportunities_executed": {"type": "integer"},
        "execution_rate": {"type": "number"},
    },
    "required": [
        "timestamp",
        "period",
        "total_trades",
        "successful_trades",
        "failed_trades",
        "total_profit",
        "total_loss",
        "net_profit",
        "total_gas_used",
        "opportunities_found",
        "opportunities_executed",
    ],
}

# Error log schema for storing error information
ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "timestamp": {"type": "number"},
        "error_type": {"type": "string"},
        "message": {"type": "string"},
        "stack_trace": {"type": "string"},
        "component": {"type": "string"},
        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
        "related_data": {"type": "object", "additionalProperties": True},
    },
    "required": ["timestamp", "error_type", "message", "component", "severity"],
}

# Distribution configuration schema
DISTRIBUTION_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "max_exposure_per_dex": {"type": "string"},  # Decimal as string
        "max_exposure_per_pair": {"type": "string"},  # Decimal as string
        "min_liquidity_threshold": {"type": "string"},  # Decimal as string
        "rebalance_threshold": {"type": "string"},  # Decimal as string
        "gas_price_weight": {"type": "number", "minimum": 0, "maximum": 1},
        "liquidity_weight": {"type": "number", "minimum": 0, "maximum": 1},
        "volume_weight": {"type": "number", "minimum": 0, "maximum": 1},
        "success_rate_weight": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "max_exposure_per_dex",
        "max_exposure_per_pair",
        "min_liquidity_threshold",
        "rebalance_threshold",
        "gas_price_weight",
        "liquidity_weight",
        "volume_weight",
        "success_rate_weight",
    ],
}

# Distribution state schema
DISTRIBUTION_STATE_SCHEMA = {
    "type": "object",
    "properties": {
        "dex_exposure": {
            "type": "object",
            "patternProperties": {"^.*$": {"type": "string"}},  # Decimal as string
        },
        "pair_exposure": {
            "type": "object",
            "patternProperties": {"^.*$": {"type": "string"}},  # Decimal as string
        },
        "timestamp": {"type": "number"},
    },
    "required": ["dex_exposure", "pair_exposure", "timestamp"],
}

# DEX metrics schema for distribution scoring
DEX_METRICS_SCHEMA = {
    "type": "object",
    "patternProperties": {
        "^.*$": {
            "type": "object",
            "properties": {
                "avg_gas_price": {"type": "number"},
                "total_liquidity": {"type": "number"},
                "volume_24h": {"type": "number"},
                "successful_trades": {"type": "integer"},
                "failed_trades": {"type": "integer"},
                "timestamp": {"type": "number"},
            },
            "required": [
                "avg_gas_price",
                "total_liquidity",
                "volume_24h",
                "successful_trades",
                "failed_trades",
                "timestamp",
            ],
        }
    },
}

# Execution configuration schema
EXECUTION_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "max_slippage": {"type": "string"},  # Decimal as string
        "gas_limit": {"type": "integer"},
        "max_gas_price": {"type": "string"},  # Decimal as string
        "retry_attempts": {"type": "integer"},
        "retry_delay": {"type": "integer"},
        "confirmation_blocks": {"type": "integer"},
        "timeout": {"type": "integer"},
    },
    "required": [
        "max_slippage",
        "gas_limit",
        "max_gas_price",
        "retry_attempts",
        "retry_delay",
        "confirmation_blocks",
        "timeout",
    ],
}

# Transaction status schema
TRANSACTION_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "trade_id": {"type": "string"},
        "dex": {"type": "string"},
        "pair": {"type": "string"},
        "amount": {"type": "string"},  # Decimal as string
        "status": {
            "type": "string",
            "enum": ["pending", "submitted", "confirmed", "failed"],
        },
        "hash": {"type": "string", "nullable": True},
        "block_number": {"type": "integer", "nullable": True},
        "gas_used": {"type": "integer", "nullable": True},
        "gas_price": {"type": "integer", "nullable": True},
        "error": {"type": "string", "nullable": True},
        "timestamp": {"type": "number"},
    },
    "required": ["trade_id", "dex", "pair", "amount", "status", "timestamp"],
}

# Execution metrics schema
EXECUTION_METRICS_SCHEMA = {
    "type": "object",
    "properties": {
        "timestamp": {"type": "number"},
        "period": {"type": "string", "enum": ["hourly", "daily", "weekly", "monthly"]},
        "total_executions": {"type": "integer"},
        "successful_executions": {"type": "integer"},
        "failed_executions": {"type": "integer"},
        "average_gas_used": {"type": "number"},
        "average_gas_price": {"type": "number"},
        "average_confirmation_time": {"type": "number"},
        "total_gas_cost": {"type": "string"},  # Decimal as string
        "execution_distribution": {
            "type": "object",
            "patternProperties": {
                "^.*$": {  # DEX name pattern
                    "type": "object",
                    "properties": {
                        "executions": {"type": "integer"},
                        "success_rate": {"type": "number"},
                        "average_gas": {"type": "number"},
                        "total_amount": {"type": "string"},  # Decimal as string
                    },
                    "required": [
                        "executions",
                        "success_rate",
                        "average_gas",
                        "total_amount",
                    ],
                }
            },
        },
    },
    "required": [
        "timestamp",
        "period",
        "total_executions",
        "successful_executions",
        "failed_executions",
        "average_gas_used",
        "average_gas_price",
        "average_confirmation_time",
        "total_gas_cost",
        "execution_distribution",
    ],
}

# System health schema for storing system status information
HEALTH_SCHEMA = {
    "type": "object",
    "properties": {
        "timestamp": {"type": "number"},
        "cpu_usage": {"type": "number"},
        "memory_usage": {"type": "number"},
        "disk_usage": {"type": "number"},
        "network_latency": {"type": "number"},
        "active_connections": {"type": "integer"},
        "component_status": {
            "type": "object",
            "patternProperties": {
                "^.*$": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["healthy", "degraded", "failed"],
                        },
                        "last_update": {"type": "number"},
                        "error_count": {"type": "integer"},
                        "message": {"type": "string"},
                    },
                    "required": ["status", "last_update"],
                }
            },
        },
    },
    "required": [
        "timestamp",
        "cpu_usage",
        "memory_usage",
        "disk_usage",
        "network_latency",
        "component_status",
    ],
}
