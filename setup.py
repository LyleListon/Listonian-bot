"""
Setup script for arbitrage_bot package.
"""

from setuptools import setup, find_packages

setup(
    name="arbitrage_bot",
    version="0.1.0",
    description="Arbitrage bot with Flashbots integration",
    author="Listonian",
    packages=find_packages(),
    python_requires=">=3.12",
    install_requires=[
        "web3>=6.0.0",
        "aiohttp>=3.8.0",
        "eth-account>=0.8.0",
        "eth-typing>=3.0.0",
        "eth-utils>=2.1.0",
        "eth-abi>=4.0.0",
        "eth-hash[pycryptodome]>=0.5.0",
        "eth-keyfile>=0.6.0",
        "eth-keys>=0.4.0",
        "eth-rlp>=0.3.0",
        "hexbytes>=0.3.0",
        "rlp>=3.0.0",
        "cytoolz>=0.12.0",
        "eth-bloom>=2.0.0",
        "typing-extensions>=4.5.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        # Dashboard specific dependencies
        "aiohttp-cors>=0.7.0",
        "aiohttp-jinja2>=1.5.0",
        "jinja2>=3.1.0",
        "fastapi>=0.110.0",
        "uvicorn>=0.27.0",
        "psutil>=5.9.0",
        "websockets>=12.0"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
            "flake8>=6.1.0"
        ]
    }
)
