"""
Secure environment variable handler for production environment with enhanced security
"""

import os
import base64
import logging
import secrets
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

class SecureEnvironment:
    def __init__(self, master_key_env: str = 'MASTER_KEY'):
        """
        Initialize secure environment with enhanced security.
        
        Args:
            master_key_env: Environment variable name for master key
        """
        self.secure_path = Path('secure')
        self.secure_path.mkdir(exist_ok=True, mode=0o700)  # Restricted permissions
        
        # Ensure secure directory permissions
        if os.name != 'nt':  # Skip on Windows
            os.chmod(self.secure_path, 0o700)
        
        self._init_encryption(master_key_env)
        
    def _init_encryption(self, master_key_env: str):
        """Initialize encryption with secure key derivation."""
        try:
            # Get or generate master key
            master_key = os.getenv(master_key_env)
            if not master_key:
                master_key = secrets.token_hex(32)
                logger.warning(f"Generated new master key. Store this securely: {master_key}")
            
            # Key derivation
            salt = self._get_or_create_salt()
            
            # Create KDF for Fernet
            kdf_fernet = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf_fernet.derive(master_key.encode()))
            self.fernet = Fernet(key)
            
            # Create separate KDF for AESGCM
            kdf_aesgcm = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            # Initialize AESGCM for sensitive operations
            self.aesgcm = AESGCM(kdf_aesgcm.derive(master_key.encode()))
            
        except Exception as e:
            logger.error(f"Encryption initialization failed: {e}")
            raise
            
    def _get_or_create_salt(self) -> bytes:
        """Get or create salt for key derivation."""
        salt_file = self.secure_path / '.salt'
        if not salt_file.exists():
            salt = os.urandom(16)
            with open(salt_file, 'wb') as f:
                f.write(salt)
            if os.name != 'nt':
                os.chmod(salt_file, 0o600)
        else:
            with open(salt_file, 'rb') as f:
                salt = f.read()
        return salt
        
    def encrypt_value(self, value: str) -> str:
        """
        Encrypt a value with additional security measures.
        
        Args:
            value: Value to encrypt
            
        Returns:
            str: Encrypted value
        """
        try:
            # Add nonce for additional security
            nonce = os.urandom(12)
            encrypted = self.aesgcm.encrypt(
                nonce,
                value.encode(),
                None  # Additional data
            )
            # Combine nonce and encrypted data
            combined = nonce + encrypted
            return base64.urlsafe_b64encode(combined).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
            
    def decrypt_value(self, encrypted_value: str) -> Optional[str]:
        """
        Decrypt a value with additional security measures.
        
        Args:
            encrypted_value: Encrypted value to decrypt
            
        Returns:
            Optional[str]: Decrypted value or None if failed
        """
        try:
            # Decode and split nonce and encrypted data
            combined = base64.urlsafe_b64decode(encrypted_value.encode())
            nonce = combined[:12]
            encrypted = combined[12:]
            
            # Decrypt with AESGCM
            decrypted = self.aesgcm.decrypt(
                nonce,
                encrypted,
                None  # Additional data
            )
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
            
    def secure_store(self, name: str, value: str):
        """
        Store encrypted value with secure permissions.
        
        Args:
            name: Name of value to store
            value: Value to store
        """
        try:
            encrypted = self.encrypt_value(value)
            file_path = self.secure_path / f'{name}.enc'
            
            # Write with restricted permissions
            with open(file_path, 'w') as f:
                f.write(encrypted)
            
            if os.name != 'nt':  # Skip on Windows
                os.chmod(file_path, 0o600)
                
        except Exception as e:
            logger.error(f"Secure store failed for {name}: {e}")
            raise
            
    def secure_load(self, name: str) -> Optional[str]:
        """
        Load and decrypt value.
        
        Args:
            name: Name of value to load
            
        Returns:
            Optional[str]: Decrypted value or None if failed
        """
        try:
            file_path = self.secure_path / f'{name}.enc'
            if not file_path.exists():
                return None
                
            with open(file_path, 'r') as f:
                encrypted = f.read()
            return self.decrypt_value(encrypted)
            
        except Exception as e:
            logger.error(f"Secure load failed for {name}: {e}")
            return None
            
    def secure_env(self, env_vars: Dict[str, str]):
        """
        Securely store sensitive environment variables.
        
        Args:
            env_vars: Dictionary of environment variables to store
        """
        for name, value in env_vars.items():
            if value and not value.startswith('$SECURE:'):
                try:
                    self.secure_store(name, value)
                    # Clear from environment after secure storage
                    if name.endswith('_URL'):
                        # Don't modify URLs in environment to prevent encoding issues
                        os.environ[name] = value
                    else:
                        os.environ[name] = '$SECURE:' + name
                except Exception as e:
                    logger.error(f"Failed to secure {name}: {e}")
                    
    def load_secure_env(self):
        """Load secure environment variables."""
        for file in self.secure_path.glob('*.enc'):
            name = file.stem
            value = self.secure_load(name)
            if value:
                if name.endswith('_URL'):
                    # Don't modify URLs to prevent encoding issues
                    os.environ[name] = value
                else:
                    os.environ[name] = value

def init_secure_environment():
    """Initialize secure environment with enhanced security."""
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
    env_vars = {var: os.getenv(var) for var in sensitive_vars if os.getenv(var)}
    secure_env.secure_env(env_vars)
    
    # Load secure values into environment
    secure_env.load_secure_env()
    
    logger.info("Secure environment initialized successfully")
    return secure_env
