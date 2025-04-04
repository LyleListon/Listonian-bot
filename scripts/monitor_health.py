#!/usr/bin/env python3
"""
Health Monitoring Script

This script checks the health of the Listonian Arbitrage Bot and sends alerts if there are any issues.
It can be run as a cron job to periodically check the system.
"""

import os
import sys
import logging
import json
import time
import socket
import smtplib
import subprocess
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the environment loader
from scripts.load_env import load_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/health_monitor.log"),
    ],
)
logger = logging.getLogger(__name__)

# Health check configuration
HEALTH_CHECK_CONFIG = {
    "process_name": "python",  # Process name to check
    "service_name": "listonian-bot",  # Systemd service name
    "api_endpoint": "http://localhost:9050/health",  # Health check endpoint
    "log_file": "logs/base_dex_scanner_mcp.log",  # Log file to check
    "max_log_age_hours": 1,  # Maximum age of the last log entry in hours
    "alert_email": "admin@example.com",  # Email to send alerts to
    "smtp_server": "smtp.example.com",  # SMTP server for sending emails
    "smtp_port": 587,  # SMTP port
    "smtp_username": "alerts@example.com",  # SMTP username
    "smtp_password": "your_password_here",  # SMTP password
    "from_email": "alerts@example.com",  # From email address
}

def check_process_running():
    """Check if the process is running."""
    try:
        # Get the process name from config
        process_name = HEALTH_CHECK_CONFIG.get("process_name", "python")
        
        # Use ps to check if the process is running
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check if the process is in the output
        if process_name in result.stdout and "run_base_dex_scanner_mcp" in result.stdout:
            logger.info(f"Process '{process_name}' is running")
            return True
        else:
            logger.error(f"Process '{process_name}' is not running")
            return False
    
    except Exception as e:
        logger.exception(f"Error checking process: {str(e)}")
        return False

def check_service_status():
    """Check if the systemd service is running."""
    try:
        # Get the service name from config
        service_name = HEALTH_CHECK_CONFIG.get("service_name", "listonian-bot")
        
        # Use systemctl to check the service status
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True
        )
        
        # Check if the service is active
        if result.stdout.strip() == "active":
            logger.info(f"Service '{service_name}' is active")
            return True
        else:
            logger.error(f"Service '{service_name}' is not active: {result.stdout.strip()}")
            return False
    
    except Exception as e:
        logger.exception(f"Error checking service status: {str(e)}")
        return False

def check_api_health():
    """Check if the API is healthy."""
    try:
        # Get the API endpoint from config
        api_endpoint = HEALTH_CHECK_CONFIG.get("api_endpoint", "http://localhost:9050/health")
        
        # Make a request to the health check endpoint
        response = requests.get(api_endpoint, timeout=10)
        
        # Check if the response is successful
        if response.status_code == 200:
            logger.info(f"API health check successful: {response.text}")
            return True
        else:
            logger.error(f"API health check failed: {response.status_code} - {response.text}")
            return False
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to API: {str(e)}")
        return False
    except Exception as e:
        logger.exception(f"Error checking API health: {str(e)}")
        return False

def check_log_freshness():
    """Check if the log file has recent entries."""
    try:
        # Get the log file path from config
        log_file = HEALTH_CHECK_CONFIG.get("log_file", "logs/base_dex_scanner_mcp.log")
        max_age_hours = HEALTH_CHECK_CONFIG.get("max_log_age_hours", 1)
        
        # Get the full path to the log file
        log_path = Path(__file__).parent.parent / log_file
        
        # Check if the log file exists
        if not log_path.exists():
            logger.error(f"Log file not found: {log_path}")
            return False
        
        # Get the modification time of the log file
        mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
        now = datetime.now()
        
        # Check if the log file has been modified recently
        if now - mtime > timedelta(hours=max_age_hours):
            logger.error(f"Log file is too old: {mtime} (max age: {max_age_hours} hours)")
            return False
        
        # Check the last few lines of the log file for recent entries
        with open(log_path, "r") as f:
            # Read the last 100 lines
            lines = f.readlines()[-100:]
            
            # Look for timestamps in the lines
            for line in reversed(lines):
                # Most log lines start with a timestamp like "2025-04-03 12:45:14,011"
                if " - " in line:
                    try:
                        # Extract the timestamp
                        timestamp_str = line.split(" - ")[0].strip()
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                        
                        # Check if the timestamp is recent
                        if now - timestamp <= timedelta(hours=max_age_hours):
                            logger.info(f"Log file has recent entries: {timestamp}")
                            return True
                    except (ValueError, IndexError):
                        # If we can't parse the timestamp, continue to the next line
                        continue
            
            logger.error(f"No recent log entries found (max age: {max_age_hours} hours)")
            return False
    
    except Exception as e:
        logger.exception(f"Error checking log freshness: {str(e)}")
        return False

def send_alert(subject, message):
    """Send an alert email."""
    try:
        # Get email configuration from config
        alert_email = HEALTH_CHECK_CONFIG.get("alert_email", "admin@example.com")
        smtp_server = HEALTH_CHECK_CONFIG.get("smtp_server", "smtp.example.com")
        smtp_port = HEALTH_CHECK_CONFIG.get("smtp_port", 587)
        smtp_username = HEALTH_CHECK_CONFIG.get("smtp_username", "alerts@example.com")
        smtp_password = HEALTH_CHECK_CONFIG.get("smtp_password", "your_password_here")
        from_email = HEALTH_CHECK_CONFIG.get("from_email", "alerts@example.com")
        
        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = alert_email
        msg["Subject"] = subject
        
        # Add the message body
        msg.attach(MIMEText(message, "plain"))
        
        # Connect to the SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        
        # Send the email
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Alert email sent to {alert_email}")
        return True
    
    except Exception as e:
        logger.exception(f"Error sending alert email: {str(e)}")
        return False

def main():
    """Main entry point for the script."""
    try:
        logger.info("Starting health check")
        
        # Load environment variables
        load_env(".env.production")
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Run health checks
        process_running = check_process_running()
        service_active = check_service_status()
        api_healthy = check_api_health()
        logs_fresh = check_log_freshness()
        
        # Determine overall health
        overall_health = process_running and service_active and api_healthy and logs_fresh
        
        # Log the results
        logger.info(f"Overall health: {'HEALTHY' if overall_health else 'UNHEALTHY'}")
        logger.info(f"Process running: {process_running}")
        logger.info(f"Service active: {service_active}")
        logger.info(f"API healthy: {api_healthy}")
        logger.info(f"Logs fresh: {logs_fresh}")
        
        # Send an alert if the system is unhealthy
        if not overall_health:
            hostname = socket.gethostname()
            subject = f"ALERT: Listonian Arbitrage Bot Unhealthy on {hostname}"
            message = f"""
Health check failed for Listonian Arbitrage Bot on {hostname} at {datetime.now()}.

Health check results:
- Process running: {process_running}
- Service active: {service_active}
- API healthy: {api_healthy}
- Logs fresh: {logs_fresh}

Please check the system as soon as possible.
"""
            send_alert(subject, message)
        
        return 0 if overall_health else 1
    
    except Exception as e:
        logger.exception(f"Error in health check: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())