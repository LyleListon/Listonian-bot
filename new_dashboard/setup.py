"""
Setup script for the dashboard package.
"""

from setuptools import setup, find_packages

setup(
    name="arbitrage-dashboard",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["fastapi", "uvicorn", "web3", "pydantic", "eth-typing"],
    python_requires=">=3.12",
)
