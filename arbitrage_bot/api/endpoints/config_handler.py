"""Config endpoint handler."""

import logging
import copy
from typing import Dict, List, Any, Optional

from arbitrage_bot.api.endpoints.base_handler import BaseHandler
from arbitrage_bot.api.models.response import ConfigResponse

logger = logging.getLogger(__name__)


class ConfigHandler(BaseHandler):
    """Handler for config endpoint."""
    
    def get_config(self) -> ConfigResponse:
        """Get system configuration.
        
        Returns:
            Config response.
        """
        # Get configuration
        config = self.bot.config
        
        # Create a sanitized copy of the configuration
        # Remove sensitive information like private keys
        sanitized_config = copy.deepcopy(config)
        
        # Sanitize blockchain configuration
        blockchain_config = sanitized_config.get("blockchain", {})
        networks = blockchain_config.get("networks", [])
        
        for network in networks:
            if "private_key" in network:
                network["private_key"] = "***"
            if "api_key" in network:
                network["api_key"] = "***"
            if "api_secret" in network:
                network["api_secret"] = "***"
        
        # Sanitize DEX configuration
        dexes = sanitized_config.get("dexes", [])
        
        for dex in dexes:
            if "api_key" in dex:
                dex["api_key"] = "***"
            if "api_secret" in dex:
                dex["api_secret"] = "***"
        
        # Sanitize flash loan configuration
        flash_loans = sanitized_config.get("flash_loans", {})
        providers = flash_loans.get("providers", [])
        
        for provider in providers:
            if "api_key" in provider:
                provider["api_key"] = "***"
            if "api_secret" in provider:
                provider["api_secret"] = "***"
        
        # Sanitize MEV protection configuration
        mev_protection = sanitized_config.get("mev_protection", {})
        
        if "api_key" in mev_protection:
            mev_protection["api_key"] = "***"
        if "api_secret" in mev_protection:
            mev_protection["api_secret"] = "***"
        
        # Create response
        response = ConfigResponse(
            trading=sanitized_config.get("trading", {}),
            dexes=dexes,
            networks=networks,
            mev_protection=mev_protection,
            flash_loans=flash_loans,
        )
        
        return response
