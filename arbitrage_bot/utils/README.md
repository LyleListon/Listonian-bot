# Arbitrage Bot - Utilities

This directory contains various utility modules and helper functions used across the Listonian Arbitrage Bot codebase.

## Key Components

- **`async_manager.py`**: Provides utilities for managing asynchronous operations, potentially including decorators like `@with_retry` and custom `AsyncLock` implementations for handling concurrency.
- **`config_loader.py`**: Handles loading and validation of configuration files (e.g., `config.json`). It likely uses Pydantic models for structured configuration management.
- **`database.py`**: Contains utilities related to data storage or serialization, such as custom JSON encoders (e.g., `DateTimeEncoder`) for handling specific data types like `datetime` objects.
- **`exceptions.py`**: Defines common custom exception classes used throughout the application (distinct from DEX-specific or core-component-specific exceptions).
- **`helpers.py`**: A general-purpose module for miscellaneous helper functions that don't fit neatly into other utility categories (e.g., formatting, data conversion).
- **`mcp_helper.py`**: Provides functions to interact with MCP (Model Context Protocol) servers, allowing the bot to leverage external tools and resources.
- **`setup.py`**: (Potentially outdated) Might contain package setup information if the bot was structured as an installable Python package.
- **`validation.py`**: Contains functions for validating data, such as checksumming Ethereum addresses or validating configuration parameters.

## Overview

The `utils` directory provides essential support functions that help keep the main application logic clean and focused. By centralizing common tasks like configuration loading, async management, data validation, and external tool interaction (MCP), these utilities promote code reuse and maintainability.