#!/usr/bin/env python3
"""
Create Symbolic Links Script

This script creates symbolic links for moved files to maintain backward compatibility.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_symlinks():
    """Create symbolic links for moved files."""
    print("Creating symbolic links for backward compatibility...")
    
    # Load reorganization report
    report_path = project_root / "reorganization_report.json"
    if not report_path.exists():
        print(f"Reorganization report not found: {report_path}")
        return False
    
    try:
        with open(report_path, 'r') as f:
            report = json.load(f)
    except Exception as e:
        print(f"Error loading reorganization report: {e}")
        return False
    
    # Create symbolic links
    for old_path, new_path in report["moved_files"].items():
        old_file = project_root / old_path
        new_file = project_root / new_path
        
        if not old_file.exists() and new_file.exists():
            try:
                # Create directory if it doesn't exist
                old_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Create symbolic link
                old_file.symlink_to(new_file)
                print(f"Created symbolic link: {old_path} -> {new_path}")
            except Exception as e:
                print(f"Error creating symbolic link for {old_path}: {e}")
    
    print("Symbolic links created successfully.")
    return True

def main():
    """Main entry point."""
    create_symlinks()

if __name__ == "__main__":
    main()
