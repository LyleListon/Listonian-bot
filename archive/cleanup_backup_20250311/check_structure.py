"""
Check the package structure and file contents.
"""

import os
import sys

def read_file_content(filepath):
    """Read and return file content."""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def check_package_structure():
    """Check package structure and file contents."""
    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")
    
    required_files = [
        ('arbitrage_bot/__init__.py', 'Package initialization'),
        ('arbitrage_bot/core/__init__.py', 'Core package initialization'),
        ('arbitrage_bot/core/web3/__init__.py', 'Web3 package initialization'),
        ('arbitrage_bot/core/web3/web3_manager.py', 'Web3 manager implementation'),
        ('arbitrage_bot/core/distribution/__init__.py', 'Distribution package initialization'),
        ('arbitrage_bot/core/distribution/manager.py', 'Distribution manager implementation'),
        ('arbitrage_bot/tests/__init__.py', 'Tests package initialization'),
        ('arbitrage_bot/tests/test_distribution_manager.py', 'Distribution manager tests')
    ]
    
    print("\nChecking required files:")
    for filepath, description in required_files:
        full_path = os.path.join(cwd, filepath)
        if os.path.exists(full_path):
            print(f"\nFound {filepath} ({description})")
            print("Content:")
            print("-" * 40)
            print(read_file_content(full_path))
            print("-" * 40)
        else:
            print(f"\nMissing {filepath} ({description})")
    
    print("\nPYTHONPATH:")
    python_path = os.environ.get('PYTHONPATH', 'Not set')
    print(python_path)
    
    print("\nPython sys.path:")
    for p in sys.path:
        print(f"  {p}")

if __name__ == "__main__":
    check_package_structure()