"""Integration system for connecting with external services."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import aiohttp
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class ServiceConnection:
    """Base class for service connections."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize service connection.

        Args:
            config: Connection configuration
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        self.session = None

    async def connect(self) -> bool:
        """Connect to service.

        Returns:
            Success status
        """
        try:
            if not self.enabled:
                logger.info("Service connection disabled")
                return False
                
            self.session = aiohttp.ClientSession()
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to service: {e}")
            return False

    async def disconnect(self):
        """Disconnect from service."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
                
        except Exception as e:
            logger.error(f"Failed to disconnect from service: {e}")

    async def send(
        self,
        endpoint: str,
        data: Dict[str, Any],
        method: str = 'POST'
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Send data to service endpoint.

        Args:
            endpoint: Service endpoint
            data: Data to send
            method: HTTP method

        Returns:
            Success status and response data
        """
        try:
            if not self.session:
                raise ValueError("Not connected to service")
                
            async with self.session.request(
                method,
                endpoint,
                json=data,
                headers=self.config.get('headers', {})
            ) as response:
                success = response.status < 400
                response_data = await response.json()
                return success, response_data
                
        except Exception as e:
            logger.error(f"Failed to send data to service: {e}")
            return False, None

class WebhookService(ServiceConnection):
    """Webhook service connection."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize webhook service.

        Args:
            config: Webhook configuration
        """
        super().__init__(config)
        self.webhooks = config['webhooks']
        self.timeout = config.get('timeout', 30)
        self.retry_count = config.get('retry_count', 3)
        self.retry_delay = config.get('retry_delay', 5)

    async def broadcast(
        self,
        event: str,
        data: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Broadcast event to all webhooks.

        Args:
            event: Event name
            data: Event data

        Returns:
            Dictionary of webhook results
        """
        try:
            if not self.enabled:
                logger.info("Webhook service disabled")
                return {}
                
            results = {}
            
            # Send to each webhook
            for webhook in self.webhooks:
                success = False
                
                # Retry logic
                for attempt in range(self.retry_count):
                    try:
                        success, _ = await self.send(
                            webhook['url'],
                            {
                                'event': event,
                                'data': data,
                                'timestamp': datetime.now().isoformat()
                            }
                        )
                        
                        if success:
                            break
                            
                        await asyncio.sleep(self.retry_delay)
                        
                    except Exception as e:
                        logger.error(f"Webhook attempt {attempt + 1} failed: {e}")
                        
                results[webhook['url']] = success
                
            return results
            
        except Exception as e:
            logger.error(f"Failed to broadcast event: {e}")
            return {}

class APIService(ServiceConnection):
    """API service connection."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize API service.

        Args:
            config: API configuration
        """
        super().__init__(config)
        self.base_url = config['base_url']
        self.api_key = config.get('api_key')
        self.version = config.get('version', 'v1')
        
        # Add API key to headers if provided
        if self.api_key:
            self.config.setdefault('headers', {})
            self.config['headers']['Authorization'] = f"Bearer {self.api_key}"

    async def request(
        self,
        endpoint: str,
        method: str = 'GET',
        data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Make API request.

        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request data

        Returns:
            Success status and response data
        """
        try:
            if not self.enabled:
                logger.info("API service disabled")
                return False, None
                
            url = f"{self.base_url}/{self.version}/{endpoint.lstrip('/')}"
            return await self.send(url, data or {}, method)
            
        except Exception as e:
            logger.error(f"Failed to make API request: {e}")
            return False, None

class IntegrationSystem:
    """System for managing external integrations."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize integration system.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize services
        self.services: Dict[str, ServiceConnection] = {}
        self._initialize_services()
        
        logger.info("Integration system initialized")

    def _initialize_services(self):
        """Initialize integration services from config."""
        try:
            # Initialize webhook service
            if 'webhooks' in self.config:
                self.services['webhook'] = WebhookService(self.config['webhooks'])
                
            # Initialize API services
            if 'apis' in self.config:
                for name, config in self.config['apis'].items():
                    self.services[name] = APIService(config)
                    
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    async def connect_services(self) -> Dict[str, bool]:
        """Connect to all services.

        Returns:
            Dictionary of connection results
        """
        try:
            results = {}
            
            for name, service in self.services.items():
                results[name] = await service.connect()
                
            return results
            
        except Exception as e:
            logger.error(f"Failed to connect services: {e}")
            raise

    async def disconnect_services(self):
        """Disconnect from all services."""
        try:
            for service in self.services.values():
                await service.disconnect()
                
        except Exception as e:
            logger.error(f"Failed to disconnect services: {e}")
            raise

    async def broadcast_event(
        self,
        event: str,
        data: Dict[str, Any]
    ) -> Dict[str, Dict[str, bool]]:
        """Broadcast event to all webhook services.

        Args:
            event: Event name
            data: Event data

        Returns:
            Dictionary of service results
        """
        try:
            results = {}
            
            for name, service in self.services.items():
                if isinstance(service, WebhookService):
                    results[name] = await service.broadcast(event, data)
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to broadcast event: {e}")
            raise

    async def api_request(
        self,
        service: str,
        endpoint: str,
        method: str = 'GET',
        data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Make API request to service.

        Args:
            service: Service name
            endpoint: API endpoint
            method: HTTP method
            data: Request data

        Returns:
            Success status and response data
        """
        try:
            if service not in self.services:
                raise ValueError(f"Service not found: {service}")
                
            api_service = self.services[service]
            if not isinstance(api_service, APIService):
                raise ValueError(f"Service {service} is not an API service")
                
            return await api_service.request(endpoint, method, data)
            
        except Exception as e:
            logger.error(f"Failed to make API request: {e}")
            return False, None

    def get_services(self) -> List[str]:
        """Get list of available services.

        Returns:
            List of service names
        """
        return list(self.services.keys())

    def get_service_status(self) -> Dict[str, bool]:
        """Get status of all services.

        Returns:
            Dictionary of service enabled states
        """
        return {
            name: service.enabled
            for name, service in self.services.items()
        }

async def create_integration_system(config: Dict[str, Any]) -> IntegrationSystem:
    """Create integration system."""
    try:
        system = IntegrationSystem(config)
        await system.connect_services()
        return system
    except Exception as e:
        logger.error(f"Failed to create integration system: {e}")
        raise
