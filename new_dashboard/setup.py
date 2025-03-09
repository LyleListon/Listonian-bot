"""Setup script for the dashboard package."""

from setuptools import setup, find_packages

setup(
    name="dashboard",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn[standard]>=0.15.0",
        "jinja2>=3.0.1",
        "websockets>=10.0",
        "python-multipart>=0.0.5",
        "aiofiles>=0.7.0",
        "psutil>=5.8.0",
        "python-socketio>=5.4.0"
    ],
    python_requires=">=3.9",
)