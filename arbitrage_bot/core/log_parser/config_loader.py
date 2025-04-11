"""
Configuration Loader for Log Parser Bridge

Loads and validates configuration from YAML files.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class ParserRule(BaseModel):
    """Configuration for a single parser rule."""

    pattern: str
    groups: List[str]

    @validator("pattern")
    def validate_pattern(cls, v: str) -> str:
        """Validate that the pattern is a valid regex."""
        try:
            re.compile(v)
            return v
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")


class ErrorHandling(BaseModel):
    """Error handling configuration."""

    max_retries: int = Field(default=3, ge=1)
    retry_delay: float = Field(default=1.0, ge=0.1)
    log_errors: bool = True


class Performance(BaseModel):
    """Performance tuning configuration."""

    batch_size: int = Field(default=1000, ge=1)
    max_memory_mb: int = Field(default=512, ge=64)
    cleanup_interval: int = Field(default=3600, ge=60)


class AlertThresholds(BaseModel):
    """Alert threshold configuration."""

    error_rate: float = Field(default=0.1, ge=0, le=1.0)
    processing_delay: float = Field(default=5.0, ge=0)
    memory_usage: float = Field(default=0.8, ge=0, le=1.0)


class Monitoring(BaseModel):
    """Monitoring configuration."""

    metrics_enabled: bool = True
    health_check_interval: int = Field(default=60, ge=1)
    alert_thresholds: AlertThresholds = Field(default_factory=AlertThresholds)


class ParserBridgeConfig(BaseModel):
    """Main configuration for the Log Parser Bridge."""

    watch_directory: str = "./logs"
    update_frequency: float = Field(default=1.0, ge=0.1)
    max_batch_size: int = Field(default=1000, ge=1)
    file_patterns: List[str]
    parser_rules: Dict[str, ParserRule]
    error_handling: ErrorHandling = Field(default_factory=ErrorHandling)
    performance: Performance = Field(default_factory=Performance)
    monitoring: Monitoring = Field(default_factory=Monitoring)

    @validator("file_patterns")
    def validate_file_patterns(cls, v: List[str]) -> List[str]:
        """Validate that file patterns are valid glob patterns."""
        if not v:
            raise ValueError("At least one file pattern is required")
        return v

    @validator("watch_directory")
    def validate_watch_directory(cls, v: str) -> str:
        """Convert watch directory to absolute path."""
        path = Path(v).resolve()
        return str(path)


class ConfigLoader:
    """Loads and validates configuration for the Log Parser Bridge."""

    @staticmethod
    async def load_config(config_path: Path) -> ParserBridgeConfig:
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Validated ParserBridgeConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        try:
            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")

            # Load YAML
            with open(config_path, "r") as f:
                raw_config = yaml.safe_load(f)

            if not isinstance(raw_config, dict) or "parser_bridge" not in raw_config:
                raise ValueError(
                    "Invalid config format: missing 'parser_bridge' section"
                )

            # Parse and validate config
            config = ParserBridgeConfig(**raw_config["parser_bridge"])

            # Compile regex patterns to verify they're valid
            for rule_name, rule in config.parser_rules.items():
                try:
                    re.compile(rule.pattern)
                except re.error as e:
                    raise ValueError(
                        f"Invalid regex pattern in rule '{rule_name}': {e}"
                    )

                if len(rule.groups) != len(re.compile(rule.pattern).groups):
                    raise ValueError(
                        f"Mismatch between number of capture groups in pattern and "
                        f"group names for rule '{rule_name}'"
                    )

            logger.info("Successfully loaded Log Parser Bridge configuration")
            return config

        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML config: {e}")
        except Exception as e:
            raise ValueError(f"Error loading config: {e}")

    @staticmethod
    def validate_config(config: ParserBridgeConfig) -> None:
        """
        Perform additional validation on the configuration.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate watch directory exists or can be created
        watch_dir = Path(config.watch_directory)
        if not watch_dir.exists():
            try:
                watch_dir.mkdir(parents=True)
            except Exception as e:
                raise ValueError(f"Cannot create watch directory: {e}")

        # Validate memory limits
        import psutil

        system_memory = psutil.virtual_memory().total / (1024 * 1024)  # MB
        if config.performance.max_memory_mb > system_memory * 0.5:
            logger.warning(
                f"Configured memory limit ({config.performance.max_memory_mb}MB) "
                f"is more than 50% of system memory ({system_memory:.0f}MB)"
            )

        # Validate monitoring settings
        if config.monitoring.metrics_enabled:
            try:
                import prometheus_client  # type: ignore
            except ImportError:
                logger.warning(
                    "prometheus_client not installed but metrics are enabled. "
                    "Metrics collection will be disabled."
                )
                config.monitoring.metrics_enabled = False
