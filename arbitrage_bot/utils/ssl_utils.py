"""SSL/TLS utilities for secure connections."""

import os
import logging
from pathlib import Path
from OpenSSL import crypto

logger = logging.getLogger(__name__)

def generate_self_signed_cert(cert_dir: str = "secure/ssl") -> tuple:
    """
    Generate a self-signed certificate for development.
    
    Args:
        cert_dir: Directory to store certificates
        
    Returns:
        tuple: (cert_path, key_path)
    """
    try:
        # Create directory if it doesn't exist
        cert_path = Path(cert_dir)
        cert_path.mkdir(parents=True, exist_ok=True)
        
        cert_file = cert_path / "server.crt"
        key_file = cert_path / "server.key"
        
        # If certificates already exist, return their paths
        if cert_file.exists() and key_file.exists():
            logger.info("Using existing SSL certificates")
            return str(cert_file), str(key_file)
            
        # Generate key
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)
        
        # Generate certificate
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "State"
        cert.get_subject().L = "City"
        cert.get_subject().O = "Organization"
        cert.get_subject().OU = "Organizational Unit"
        cert.get_subject().CN = "localhost"
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365*24*60*60)  # Valid for one year
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha256')
        
        # Save certificate
        with open(cert_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
            
        # Save private key
        with open(key_file, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
            
        logger.info("Generated new SSL certificates")
        return str(cert_file), str(key_file)
        
    except Exception as e:
        logger.error(f"Failed to generate SSL certificates: {e}")
        raise
