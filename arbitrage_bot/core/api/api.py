"""API system for exposing system functionality through REST endpoints."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import jwt
import bcrypt
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Models
class User(BaseModel):
    """User model."""
    username: str = Field(..., description="Username")
    role: str = Field(..., description="User role")
    api_key: Optional[str] = Field(None, description="API key")

class Token(BaseModel):
    """Token model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")

class APIKey(BaseModel):
    """API key model."""
    key: str = Field(..., description="API key")
    name: str = Field(..., description="Key name")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")

class APIKeyRequest(BaseModel):
    """API key request model."""
    name: str = Field(..., description="Key name")
    expires_in_days: Optional[int] = Field(None, description="Days until expiration")

class APISystem:
    """System for managing API functionality."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize API system.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.secret_key = config['secret_key']
        self.token_expiry = timedelta(minutes=config.get('token_expiry_minutes', 60))
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        
        # Initialize FastAPI
        self.app = FastAPI(
            title="Arbitrage Bot API",
            description="API for interacting with the arbitrage bot system",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config.get('cors_origins', ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Security
        self.security = HTTPBearer()
        
        # Register routes
        self._register_routes()
        
        logger.info("API system initialized")

    def _register_routes(self):
        """Register API routes."""
        
        # Auth endpoints
        @self.app.post("/api/v1/auth/token", response_model=Token)
        async def login(username: str, password: str) -> Token:
            """Get JWT token."""
            try:
                # Verify credentials (implement your auth logic)
                if not self._verify_credentials(username, password):
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid credentials"
                    )
                    
                # Generate token
                token = self._create_token({
                    'sub': username,
                    'role': 'user'  # Get from your user store
                })
                
                return Token(access_token=token)
                
            except Exception as e:
                logger.error(f"Login failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Login failed"
                )

        @self.app.post("/api/v1/auth/api-key", response_model=APIKey)
        async def create_api_key(
            request: APIKeyRequest,
            token: HTTPAuthorizationCredentials = Security(self.security)
        ) -> APIKey:
            """Create API key."""
            try:
                # Verify JWT
                payload = self._verify_token(token.credentials)
                
                # Generate API key
                key = self._generate_api_key()
                expires_at = None
                
                if request.expires_in_days:
                    expires_at = datetime.now() + timedelta(days=request.expires_in_days)
                    
                # Store API key
                self.api_keys[key] = {
                    'name': request.name,
                    'user': payload['sub'],
                    'created_at': datetime.now(),
                    'expires_at': expires_at
                }
                
                return APIKey(
                    key=key,
                    name=request.name,
                    expires_at=expires_at
                )
                
            except jwt.InvalidTokenError:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token"
                )
            except Exception as e:
                logger.error(f"Failed to create API key: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create API key"
                )

        @self.app.get("/api/v1/auth/api-keys", response_model=List[APIKey])
        async def list_api_keys(
            token: HTTPAuthorizationCredentials = Security(self.security)
        ) -> List[APIKey]:
            """List API keys."""
            try:
                # Verify JWT
                payload = self._verify_token(token.credentials)
                
                # Get user's API keys
                keys = [
                    APIKey(
                        key=key,
                        name=data['name'],
                        expires_at=data['expires_at']
                    )
                    for key, data in self.api_keys.items()
                    if data['user'] == payload['sub']
                ]
                
                return keys
                
            except jwt.InvalidTokenError:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token"
                )
            except Exception as e:
                logger.error(f"Failed to list API keys: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to list API keys"
                )

        @self.app.delete("/api/v1/auth/api-key/{key}")
        async def delete_api_key(
            key: str,
            token: HTTPAuthorizationCredentials = Security(self.security)
        ):
            """Delete API key."""
            try:
                # Verify JWT
                payload = self._verify_token(token.credentials)
                
                # Check key exists
                if key not in self.api_keys:
                    raise HTTPException(
                        status_code=404,
                        detail="API key not found"
                    )
                    
                # Check ownership
                if self.api_keys[key]['user'] != payload['sub']:
                    raise HTTPException(
                        status_code=403,
                        detail="Not authorized to delete this key"
                    )
                    
                # Delete key
                del self.api_keys[key]
                
            except jwt.InvalidTokenError:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token"
                )
            except Exception as e:
                logger.error(f"Failed to delete API key: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to delete API key"
                )

    def _verify_credentials(self, username: str, password: str) -> bool:
        """Verify user credentials.

        Args:
            username: Username
            password: Password

        Returns:
            Valid credentials
        """
        # Implement your credential verification logic
        # This is just a placeholder
        return True

    def _create_token(self, data: Dict[str, Any]) -> str:
        """Create JWT token.

        Args:
            data: Token data

        Returns:
            JWT token
        """
        try:
            # Add expiry
            data['exp'] = datetime.utcnow() + self.token_expiry
            
            # Create token
            return jwt.encode(data, self.secret_key, algorithm='HS256')
            
        except Exception as e:
            logger.error(f"Failed to create token: {e}")
            raise

    def _verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token.

        Args:
            token: JWT token

        Returns:
            Token payload
        """
        try:
            return jwt.decode(token, self.secret_key, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    def _generate_api_key(self) -> str:
        """Generate API key.

        Returns:
            API key
        """
        try:
            # Generate random bytes
            key_bytes = bcrypt.gensalt()
            
            # Convert to hex string
            return key_bytes.hex()
            
        except Exception as e:
            logger.error(f"Failed to generate API key: {e}")
            raise

    def _verify_api_key(self, key: str) -> bool:
        """Verify API key.

        Args:
            key: API key

        Returns:
            Valid key
        """
        try:
            # Check key exists
            if key not in self.api_keys:
                return False
                
            # Check expiration
            if self.api_keys[key]['expires_at']:
                if datetime.now() > self.api_keys[key]['expires_at']:
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify API key: {e}")
            return False

    async def start(self):
        """Start API server."""
        try:
            import uvicorn
            
            # Get config
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 8000)
            
            # Start server
            config = uvicorn.Config(
                self.app,
                host=host,
                port=port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            raise

    async def stop(self):
        """Stop API server."""
        try:
            # Cleanup
            self.api_keys.clear()
            
        except Exception as e:
            logger.error(f"Failed to stop API server: {e}")
            raise

async def create_api_system(config: Dict[str, Any]) -> APISystem:
    """Create API system."""
    try:
        system = APISystem(config)
        await system.start()
        return system
    except Exception as e:
        logger.error(f"Failed to create API system: {e}")
        raise
