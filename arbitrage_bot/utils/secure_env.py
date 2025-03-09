"""
Secure environment variable handler for production environment
"""

import os
import base64
from cryptography.fernet import Fernet
from pathlib import Path
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class SecureEnvironment:
    def __init__(self):
        self.secure_path = Path('secure')
        self.secure_path.mkdir(exist_ok=True)
        self._init_key()
        
    def _init_key(self):
        """Initialize or load encryption key"""
        key_file = self.secure_path / '.key'
        if not key_file.exists():
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
        else:
            with open(key_file, 'rb') as f:
                key = f.read()
        self.fernet = Fernet(key)
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt a value"""
        return base64.urlsafe_b64encode(
            self.fernet.encrypt(value.encode())
        ).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a value"""
        try:
            return self.fernet.decrypt(
                base64.urlsafe_b64decode(encrypted_value.encode())
            ).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            return None
    
    def secure_store(self, name: str, value: str):
        """Store encrypted value"""
        if not value:
            logger.warning(f"Skipping empty value for {name}")
            return
        encrypted = self.encrypt_value(value)
        with open(self.secure_path / f'{name}.enc', 'w') as f:
            f.write(encrypted)
        logger.debug(f"Stored secure value for {name}")
            
    def secure_load(self, name: str) -> str:
        """Load and decrypt value"""
        try:
            file_path = self.secure_path / f'{name}.enc'
            logger.debug(f"Loading secure value from {file_path}")
            with open(file_path, 'r') as f:
                encrypted = f.read()
            value = self.decrypt_value(encrypted)
            if value:
                logger.debug(f"Successfully loaded secure value for {name}")
            else:
                logger.error(f"Failed to decrypt value for {name}")
            return value
        except FileNotFoundError:
            # If secure file not found, try getting from environment
            value = os.getenv(name)
            if value:
                logger.debug(f"Using value from environment for {name}")
                return value
            logger.error(f"No secure file or environment variable found for {name}")
            return None
            
    def secure_env(self, env_vars: dict):
        """Securely store sensitive environment variables"""
        for name, value in env_vars.items():
            if value and not value.startswith('$SECURE:'):
                logger.debug(f"Storing secure value for {name}")
                self.secure_store(name, value)
                
    def load_secure_env(self):
        """Load secure environment variables"""
        for file in self.secure_path.glob('*.enc'):
            name = file.stem
            value = self.secure_load(name)
            if value:
                os.environ[name] = value
                logger.debug(f"Loaded secure environment variable: {name}")

def init_secure_environment():
    """Initialize secure environment"""
    # Load environment variables from .env.production
    load_dotenv('.env.production')

    secure_env = SecureEnvironment()

    # Define sensitive variables
    sensitive_vars = [
        'PRIVATE_KEY',
        'WALLET_ADDRESS',
        'PROFIT_RECIPIENT',
        'INFURA_API_KEY',
        'ALCHEMY_API_KEY',
        'DISCORD_WEBHOOK_URL',
        'BASE_RPC_URL'
    ]

    # Store current values securely
    env_vars = {var: os.getenv(var) for var in sensitive_vars}
    secure_env.secure_env(env_vars)

    # Load secure values into environment
    secure_env.load_secure_env()

    # Verify required variables
    for var in ['BASE_RPC_URL', 'PRIVATE_KEY', 'WALLET_ADDRESS', 'PROFIT_RECIPIENT']:
        value = os.getenv(var)
        if not value:
            raise ValueError(f"Required environment variable {var} not set")
        logger.debug(f"Verified {var} is set")

    return secure_env
