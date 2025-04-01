"""
Setup script for arbitrage_bot package.
"""

from setuptools import setup, find_namespace_packages

setup(
    name="arbitrage_bot",
    version="0.1.0",
    description="Arbitrage bot with Flashbots integration",
    author="Listonian",
    packages=find_namespace_packages(include=[
        'arbitrage_bot',
        'arbitrage_bot.*',
        'arbitrage_bot.core.*',
        'arbitrage_bot.core.ml.*',
        'arbitrage_bot.core.market.*',
        'arbitrage_bot.core.memory.*',
        'arbitrage_bot.utils.*'
    ]),
    python_requires=">=3.12",
    install_requires=[
        # Web3 and Ethereum
        "web3>=6.0.0",
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
        
        # Async support
        "aiohttp>=3.8.0",
        "aiohttp-cors>=0.7.0",
        "websockets>=12.0",
        
        # Data processing
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scikit-learn>=1.3.0",
        
        # Caching and storage
        "redis>=5.0.0",
        "aioredis>=2.0.0",
        
        # Configuration and environment
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.0",
        "toml>=0.10.0",
        
        # Monitoring and metrics
        "prometheus-client>=0.17.0",
        "psutil>=5.9.0",
        
        # Dashboard
        "fastapi>=0.110.0",
        "uvicorn>=0.27.0",
        "jinja2>=3.1.0",
        "aiohttp-jinja2>=1.5.0",
        
        # Development and testing
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.1.0",
        "black>=23.0.0",
        "isort>=5.12.0",
        "mypy>=1.5.0",
        "flake8>=6.1.0",
        
        # Utilities
        "cytoolz>=0.12.0",
        "eth-bloom>=2.0.0",
        "typing-extensions>=4.5.0",
        "requests>=2.31.0"
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
        ],
        "ml": [
            "torch>=2.0.0",
            "tensorflow>=2.13.0",
            "scikit-learn>=1.3.0",
            "xgboost>=2.0.0",
            "lightgbm>=4.0.0"
        ],
        "monitoring": [
            "prometheus-client>=0.17.0",
            "grafana-api>=2.0.0",
            "influxdb-client>=1.36.0"
        ]
    },
    entry_points={
        'console_scripts': [
            'arbitrage-bot=arbitrage_bot.run_bot:main',
            'arbitrage-dashboard=arbitrage_bot.new_dashboard.dashboard.app:main'
        ]
    },
    package_data={
        'arbitrage_bot': [
            'abi/*.json',
            'config/*.yaml',
            'new_dashboard/dashboard/templates/*',
            'new_dashboard/dashboard/static/*'
        ]
    },
    include_package_data=True,
    zip_safe=False
)
