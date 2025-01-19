from setuptools import setup, find_packages

setup(
    name="arbitrage_bot",
    version="0.1.0",
    packages=find_packages(exclude=["tests*", "scripts*"]),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "quart>=0.18.0",
        "quart-cors>=0.7.0",
        "hypercorn>=0.15.0",
        "web3>=7.0.0",
        "asyncio>=3.4.3",
        "aiohttp>=3.8.0",
        "requests>=2.31.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-mock>=3.10.0",
        "pytest-timeout>=2.1.0",
        "coverage>=7.2.0",
        "python-dotenv>=1.0.0",
        "websockets>=11.0.0",
        "eth-account>=0.9.0",
        "eth-typing>=3.0.0",
        "eth-utils>=2.2.0",
    ],
    extras_require={
        "dev": [
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=0.950",
            "pytest-cov>=4.1.0",
        ],
        "docs": [
            "Sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0",
        ],
    },
    package_data={
        "arbitrage_bot": [
            "dashboard/static/*",
            "dashboard/templates/*",
            "configs/*.json",
            "abi/*.json",
        ],
    },
    entry_points={
        "console_scripts": [
            "arbitrage-bot=arbitrage_bot.main:main",
            "arbitrage-dashboard=arbitrage_bot.dashboard.run:main",
        ],
    },
)
