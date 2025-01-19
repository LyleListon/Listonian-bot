from arbitrage_bot.utils.secure_env import SecureEnvironment
import os
from dotenv import load_dotenv

def init_secure_storage():
    # Initialize secure environment
    secure_env = SecureEnvironment()
    
    # Read and parse .env.production
    env_vars = {}
    with open('.env.production', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    env_vars[key] = value
                    # Set environment variable directly for URLs
                    if key.endswith('_URL'):
                        os.environ[key] = value
    
    # Store each variable securely
    secure_env.secure_env(env_vars)
    
    # Load secure values into environment
    secure_env.load_secure_env()
    
    # Double check URLs are set correctly
    for key in env_vars:
        if key.endswith('_URL'):
            os.environ[key] = env_vars[key]
    
    print("Secure environment initialized successfully")

if __name__ == '__main__':
    init_secure_storage()
