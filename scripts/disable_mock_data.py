#!/usr/bin/env python3
"""
Disable Mock Data

This script identifies and disables all mock data generators in the codebase.
It ensures that only real data is used in production.
"""

import os
import sys
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("disable_mock_data")

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Patterns to identify mock data generation
MOCK_DATA_PATTERNS = [
    r"generate_mock_",
    r"mock_data",
    r"test_data",
    r"fake_data",
    r"simulate_",
    r"random\.(random|uniform|choice|randint)",
    r"MockData",
    r"\.random\(",
]

# Files to exclude (test files, etc.)
EXCLUDE_DIRS = [
    "tests",
    "__pycache__",
    ".git",
    "venv",
    "env",
    ".venv",
    ".env",
    "node_modules",
]

# Files that should be completely disabled
DISABLE_FILES = [
    "new_dashboard/generate_test_data.py",
    "new_dashboard/run_test_server.py",
]

def find_mock_data_files() -> List[Tuple[Path, List[int]]]:
    """
    Find files containing mock data generation code.
    
    Returns:
        List of tuples containing file path and line numbers with mock data
    """
    mock_files = []
    
    # Compile regex patterns
    patterns = [re.compile(pattern) for pattern in MOCK_DATA_PATTERNS]
    
    # Walk through project directory
    for root, dirs, files in os.walk(project_root):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            # Only check Python and JavaScript files
            if not (file.endswith('.py') or file.endswith('.js')):
                continue
            
            file_path = Path(root) / file
            rel_path = file_path.relative_to(project_root)
            
            # Skip files in DISABLE_FILES list (they'll be handled separately)
            if str(rel_path) in DISABLE_FILES:
                continue
            
            # Check file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                mock_lines = []
                for i, line in enumerate(lines):
                    if any(pattern.search(line) for pattern in patterns):
                        # Skip comments
                        if line.strip().startswith(('#', '//')):
                            continue
                        mock_lines.append(i + 1)
                
                if mock_lines:
                    mock_files.append((rel_path, mock_lines))
            
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
    
    return mock_files

def disable_mock_data_files() -> None:
    """Disable files that should be completely disabled."""
    for file_path in DISABLE_FILES:
        full_path = project_root / file_path
        if not full_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        disabled_path = full_path.with_suffix('.py.disabled')
        try:
            # Rename file to .disabled
            full_path.rename(disabled_path)
            logger.info(f"Disabled file: {file_path} -> {disabled_path}")
        except Exception as e:
            logger.error(f"Error disabling file {file_path}: {e}")

def create_real_data_flag() -> None:
    """Create a flag file to indicate real data only mode."""
    flag_path = project_root / '.real_data_only'
    try:
        with open(flag_path, 'w') as f:
            f.write(f"REAL_DATA_ONLY=true\n")
            f.write(f"CREATED_AT={os.environ.get('DATE', '')}\n")
        logger.info(f"Created real data flag file: {flag_path}")
    except Exception as e:
        logger.error(f"Error creating flag file: {e}")

def update_env_files() -> None:
    """Update environment files to enforce real data only."""
    env_files = [
        project_root / '.env',
        project_root / '.env.production',
        project_root / '.env.development',
    ]
    
    for env_path in env_files:
        if not env_path.exists():
            continue
        
        try:
            # Read current content
            with open(env_path, 'r') as f:
                content = f.read()
            
            # Add or update USE_REAL_DATA_ONLY flag
            if 'USE_REAL_DATA_ONLY' not in content:
                with open(env_path, 'a') as f:
                    f.write("\n# Enforce real data only\nUSE_REAL_DATA_ONLY=true\n")
            else:
                content = re.sub(
                    r'USE_REAL_DATA_ONLY=.*',
                    'USE_REAL_DATA_ONLY=true',
                    content
                )
                with open(env_path, 'w') as f:
                    f.write(content)
            
            logger.info(f"Updated environment file: {env_path}")
        
        except Exception as e:
            logger.error(f"Error updating environment file {env_path}: {e}")

def main() -> int:
    """Main entry point."""
    logger.info("Identifying mock data in codebase...")
    
    # Find files with mock data
    mock_files = find_mock_data_files()
    
    # Print results
    if mock_files:
        logger.warning(f"Found {len(mock_files)} files with potential mock data:")
        for file_path, line_numbers in mock_files:
            logger.warning(f"  {file_path}: lines {', '.join(map(str, line_numbers))}")
    else:
        logger.info("No mock data found in codebase.")
    
    # Disable mock data files
    disable_mock_data_files()
    
    # Create real data flag
    create_real_data_flag()
    
    # Update environment files
    update_env_files()
    
    logger.info("Mock data identification and disabling complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
