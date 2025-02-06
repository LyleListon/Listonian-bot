#!/usr/bin/env python3
"""
OAuth2 Setup Script

This script helps users set up OAuth2 credentials for Google and GitHub authentication.
It guides users through the process and generates the necessary configuration files.
"""

import os
import sys
import secrets
import webbrowser
from pathlib import Path
import yaml
from typing import Dict, Any

def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80 + "\n")

def generate_secret() -> str:
    """Generate a secure random secret."""
    return secrets.token_hex(32)

def get_user_input(prompt: str, default: str = "") -> str:
    """Get input from user with optional default value."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default

def setup_google_oauth():
    """Guide user through Google OAuth setup."""
    print_header("Google OAuth2 Setup")
    print("""
Steps to set up Google OAuth2:

1. Go to Google Cloud Console (https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the OAuth2 API
4. Create OAuth2 credentials
5. Add authorized redirect URIs:
   - http://localhost:3000/auth/google/callback (development)
   - https://your-domain.com/auth/google/callback (production)
""")

    # Open Google Cloud Console
    if get_user_input("Would you like to open Google Cloud Console? (y/n)", "y").lower() == "y":
        webbrowser.open("https://console.cloud.google.com")

    print("\nOnce you have created your OAuth2 credentials, enter them below:")
    client_id = get_user_input("Google Client ID")
    client_secret = get_user_input("Google Client Secret")

    return {
        "GOOGLE_CLIENT_ID": client_id,
        "GOOGLE_CLIENT_SECRET": client_secret
    }

def setup_github_oauth():
    """Guide user through GitHub OAuth setup."""
    print_header("GitHub OAuth2 Setup")
    print("""
Steps to set up GitHub OAuth2:

1. Go to GitHub Developer Settings (https://github.com/settings/developers)
2. Create a new OAuth App
3. Add Homepage URL and Authorization callback URL:
   - Homepage URL: http://localhost:3000 (development)
   - Authorization callback URL: http://localhost:3000/auth/github/callback
""")

    # Open GitHub Developer Settings
    if get_user_input("Would you like to open GitHub Developer Settings? (y/n)", "y").lower() == "y":
        webbrowser.open("https://github.com/settings/developers")

    print("\nOnce you have created your OAuth App, enter the credentials below:")
    client_id = get_user_input("GitHub Client ID")
    client_secret = get_user_input("GitHub Client Secret")

    return {
        "GITHUB_CLIENT_ID": client_id,
        "GITHUB_CLIENT_SECRET": client_secret
    }

def generate_env_file(config: Dict[str, Any], env_path: Path):
    """Generate .env file with configuration."""
    # Add additional required configuration
    config.update({
        "JWT_SECRET_KEY": generate_secret(),
        "SESSION_SECRET": generate_secret(),
        "NODE_ENV": "development",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "FRONTEND_URL": "http://localhost:3000",
        "CORS_ORIGINS": "http://localhost:3000",
        "ALLOWED_HOSTS": "localhost,127.0.0.1",
        "LOG_LEVEL": "INFO",
        "DEBUG": "false"
    })

    # Write .env file
    with open(env_path, "w") as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")

def main():
    """Run the OAuth setup process."""
    print_header("OAuth2 Setup Wizard")
    print("This wizard will help you set up OAuth2 authentication for your dashboard.")

    # Get project root directory
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"

    if env_path.exists():
        overwrite = get_user_input(
            "\n.env file already exists. Would you like to overwrite it? (y/n)",
            "n"
        )
        if overwrite.lower() != "y":
            print("\nSetup cancelled. Existing .env file was not modified.")
            sys.exit(0)

    # Collect OAuth credentials
    config = {}
    config.update(setup_google_oauth())
    config.update(setup_github_oauth())

    # Generate .env file
    generate_env_file(config, env_path)

    print_header("Setup Complete!")
    print(f"""
Configuration has been saved to: {env_path}

Next steps:
1. Review the generated .env file
2. Start the backend server:
   cd {project_root}/backend
   uvicorn api:app --reload

3. Start the frontend development server:
   cd {project_root}/frontend
   npm start

4. Open http://localhost:3000 in your browser

Note: Keep your .env file secure and never commit it to version control!
""")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during setup: {e}")
        sys.exit(1)