"""
Project structure validation.

This module verifies:
1. Directory structure
2. Required files
3. Package organization
4. Configuration files
"""

import os
import sys
import json
import pytest
import logging
from pathlib import Path
from typing import Dict, List, Set

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Required project structure
REQUIRED_DIRECTORIES = {
    'abi': 'Smart contract ABIs',
    'arbitrage_bot': 'Main package',
    'arbitrage_bot/core': 'Core functionality',
    'configs': 'Configuration files',
    'docs': 'Documentation',
    'logs': 'Log files',
    'memory-bank': 'Project context',
    'tests': 'Test files',
    'tests/core': 'Core tests',
    'tests/integration': 'Integration tests',
    'tests/environment': 'Environment tests'
}

REQUIRED_FILES = {
    'pyproject.toml': 'Project configuration',
    'pytest.ini': 'Pytest configuration',
    'requirements.txt': 'Project dependencies',
    'requirements-dev.txt': 'Development dependencies',
    '.env': 'Environment variables',
    'configs/config.json': 'Main configuration',
    'configs/dex_config.json': 'DEX configuration'
}

REQUIRED_PACKAGES = [
    'arbitrage_bot',
    'arbitrage_bot.core',
    'arbitrage_bot.core.web3',
    'arbitrage_bot.core.dex',
    'arbitrage_bot.core.monitoring'
]

def test_directory_structure():
    """Test required directories exist."""
    root = Path.cwd()
    missing_dirs = []
    
    for directory, description in REQUIRED_DIRECTORIES.items():
        path = root / directory
        if not path.exists():
            missing_dirs.append(directory)
            logger.error(f"Missing directory: {directory} ({description})")
        elif not path.is_dir():
            missing_dirs.append(directory)
            logger.error(f"Not a directory: {directory}")
    
    assert not missing_dirs, f"Missing directories: {', '.join(missing_dirs)}"

def test_required_files():
    """Test required files exist."""
    root = Path.cwd()
    missing_files = []
    
    for file_path, description in REQUIRED_FILES.items():
        path = root / file_path
        if not path.exists():
            missing_files.append(file_path)
            logger.error(f"Missing file: {file_path} ({description})")
        elif not path.is_file():
            missing_files.append(file_path)
            logger.error(f"Not a file: {file_path}")
    
    assert not missing_files, f"Missing files: {', '.join(missing_files)}"

def test_package_structure():
    """Test Python package structure."""
    missing_packages = []
    
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
            logger.info(f"Found package: {package}")
        except ImportError as e:
            missing_packages.append(package)
            logger.error(f"Missing package: {package} ({e})")
    
    assert not missing_packages, f"Missing packages: {', '.join(missing_packages)}"

def test_config_files():
    """Test configuration file validity."""
    root = Path.cwd()
    config_files = [
        'configs/config.json',
        'configs/dex_config.json'
    ]
    
    for config_file in config_files:
        path = root / config_file
        try:
            with open(path) as f:
                config = json.load(f)
            logger.info(f"Valid JSON: {config_file}")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {config_file}: {e}")
        except FileNotFoundError:
            pytest.fail(f"Missing config file: {config_file}")

def test_memory_bank():
    """Test memory bank structure."""
    memory_bank = Path.cwd() / 'memory-bank'
    required_files = [
        'projectbrief.md',
        'activeContext.md',
        'techContext.md',
        'systemPatterns.md',
        'productContext.md',
        'progress.md'
    ]
    
    missing_files = []
    for file_name in required_files:
        path = memory_bank / file_name
        if not path.exists():
            missing_files.append(file_name)
            logger.error(f"Missing memory bank file: {file_name}")
    
    assert not missing_files, f"Missing memory bank files: {', '.join(missing_files)}"

def test_test_organization():
    """Test test directory organization."""
    test_dir = Path.cwd() / 'tests'
    required_test_dirs = ['core', 'integration', 'environment']
    
    for directory in required_test_dirs:
        path = test_dir / directory
        assert path.exists(), f"Missing test directory: {directory}"
        assert path.is_dir(), f"Not a directory: {directory}"
        
        # Check for __init__.py
        init_file = path / '__init__.py'
        assert init_file.exists(), f"Missing __init__.py in {directory}"

def test_documentation():
    """Test documentation structure."""
    docs_dir = Path.cwd() / 'docs'
    required_docs = [
        'ARCHITECTURE.md',
        'DEPLOYMENT.md',
        'DEVELOPMENT.md'
    ]
    
    missing_docs = []
    for doc_file in required_docs:
        path = docs_dir / doc_file
        if not path.exists():
            missing_docs.append(doc_file)
            logger.error(f"Missing documentation: {doc_file}")
    
    assert not missing_docs, f"Missing documentation files: {', '.join(missing_docs)}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])