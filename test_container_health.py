#!/usr/bin/env python3
import os
import json
import time
import requests
from pathlib import Path
import subprocess

def test_data_persistence():
    """Test data persistence across container restarts"""
    print("\n=== Testing Data Persistence ===")
    
    # Test VSCode remote data persistence
    vscode_data_path = Path("/root/.vscode-remote/data")
    test_file = vscode_data_path / "test_persistence.json"
    test_data = {"timestamp": time.time(), "test": "persistence"}
    
    print("Writing test data...")
    os.makedirs(vscode_data_path, exist_ok=True)
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    print(f"Test file created at: {test_file}")
    print("Please rebuild container and verify this file persists.")

def test_container_health():
    """Test container health monitoring"""
    print("\n=== Testing Container Health ===")
    
    try:
        # Test dashboard health endpoint
        response = requests.get("http://localhost:5000/health")
        print(f"Dashboard Health Status: {response.status_code}")
        
        # Check Python processes
        result = subprocess.run(["pgrep", "python"], capture_output=True, text=True)
        if result.stdout:
            print("Python processes running: ✓")
        else:
            print("No Python processes found: ✗")
            
        # Check PowerShell configuration
        ps_config = Path("/root/.config/powershell/Microsoft.PowerShell_profile.ps1")
        if ps_config.exists():
            print("PowerShell profile exists: ✓")
        else:
            print("PowerShell profile missing: ✗")
            
    except requests.RequestException as e:
        print(f"Dashboard health check failed: {e}")

def test_conversation_persistence():
    """Test conversation history persistence"""
    print("\n=== Testing Conversation Persistence ===")
    
    # Check Roo Code conversation storage
    roo_data_path = Path("/root/.vscode-remote/data/User/globalStorage/rooveterinaryinc.roo-cline")
    
    if roo_data_path.exists():
        print("Roo Code data directory exists: ✓")
        # List conversation files
        conv_files = list(roo_data_path.glob("conversations/*.json"))
        print(f"Found {len(conv_files)} conversation files")
    else:
        print("Roo Code data directory missing: ✗")

def main():
    """Run all container health tests"""
    print("Starting Container Health Tests...")
    
    test_data_persistence()
    test_container_health()
    test_conversation_persistence()
    
    print("\nTests completed. Please check results above.")

if __name__ == "__main__":
    main()