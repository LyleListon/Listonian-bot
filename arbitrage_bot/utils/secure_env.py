"""
Secure environment variable handler for production environment
"""

import os
import base64
from cryptography.fernet import Fernet
from pathlib import Path

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
        except Exception:
            return None
    
    def secure_store(self, name: str, value: str):
        """Store encrypted value"""
        encrypted = self.encrypt_value(value)
        with open(self.secure_path / f'{name}.enc', 'w') as f:
            f.write(encrypted)
            
    def secure_load(self, name: str) -> str:
        """Load and decrypt value"""
        try:
            with open(self.secure_path / f'{name}.enc', 'r') as f:
                encrypted = f.read()
            return self.decrypt_value(encrypted)
        except FileNotFoundError:
            return None
            
    def secure_env(self, env_vars: dict):
        """Securely store sensitive environment variables"""
        for name, value in env_vars.items():
            if value and not value.startswith('$SECURE:'):
                self.secure_store(name, value)
                
    def load_secure_env(self):
        """Load secure environment variables"""
        for file in self.secure_path.glob('*.enc'):
            name = file.stem
            value = self.secure_load(name)
            if value:
                os.environ[name] = value

def init_secure_environment():
    """Initialize secure environment"""
    secure_env = SecureEnvironment()
    
    # Define sensitive variables
    sensitive_vars = [
        'PRIVATE_KEY',
        'WALLET_ADDRESS',
        'INFURA_API_KEY',
        'ALCHEMY_API_KEY',
        'DISCORD_WEBHOOK_URL'
    ]
    
    # Store current values securely
    env_vars = {var: os.getenv(var) for var in sensitive_vars}
    secure_env.secure_env(env_vars)
    
    # Load secure values into environment
    secure_env.load_secure_env()
    
    return secure_env
