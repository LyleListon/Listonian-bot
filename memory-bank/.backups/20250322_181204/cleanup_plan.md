# Project Organization Guide

## Core Project Structure
```
d:/Listonian-bot/
├── arbitrage_bot/           # Main bot package
│   ├── core/               # Core arbitrage logic
│   │   ├── web3/          # Web3 interaction layer
│   │   └── dex/           # DEX integration modules
│   ├── utils/             # Utility functions
│   └── dashboard/         # Dashboard components
├── new_dashboard/         # Modern dashboard implementation
├── memory-bank/          # Project context and documentation
├── examples/             # Integration examples
├── configs/             # Configuration files
├── abi/                 # Smart contract ABIs
└── archive/            # Archived components
```

## Key Components & Their Purpose

### 1. Core Bot Components (arbitrage_bot/)
- **core/web3/**: Web3 interaction layer
  - async_provider.py - Async Web3 provider implementation
  - flashbots/ - MEV protection integration
  - interfaces.py - Core interfaces
  - errors.py - Error handling
  
- **core/dex/**: DEX integrations
  - Base implementations for different DEX types
  - Protocol-specific adapters
  - Pool management and discovery

- **utils/**: Shared utilities
  - async_manager.py - Async operation handling
  - logging utilities
  - helper functions

### 2. Dashboard (new_dashboard/)
- Modern implementation with real-time updates
- System monitoring and metrics
- WebSocket integration
- Memory service integration

### 3. Documentation & Context (memory-bank/)
- **Core Documentation**:
  - activeContext.md - Current development state
  - projectbrief.md - Project overview
  - techContext.md - Technical stack
  - systemPatterns.md - Architecture patterns
  
- **Integration Guides**:
  - flashbots_integration.md
  - flash_loan_integration.md
  - production_deployment_guide.md

### 4. Configuration (configs/)
- production.json - Production settings
- Development and testing configs
- Environment-specific settings

### 5. Smart Contract Integration (abi/)
- Organized by protocol
- Version-specific ABIs
- Interface definitions

### 6. Examples & References (examples/)
- Flashbots integration examples
- Multi-path arbitrage implementations
- Flash loan integration patterns

## Active Development Areas

### Currently Active
1. Flashbots Integration
   - risk_analyzer.py
   - MEV protection implementation
   - Bundle submission

2. Flash Loan Management
   - unified_flash_loan_manager.py
   - Balance management refactoring

3. Web3 Layer Optimization
   - Async provider improvements
   - Rate limiting handling
   - Transaction optimization

### Production Components
- start_production.py - Main entry point
- deploy_production.ps1 - Deployment script
- DEPLOYMENT_CHECKLIST.md - Deployment guide

## Quick Reference

### Key Files for Daily Development
1. **Starting the Bot**:
   - start_production.py
   - deploy_production.ps1

2. **Monitoring**:
   - new_dashboard/ (modern UI)
   - final_dashboard.py (stable version)

3. **Configuration**:
   - configs/production.json
   - .env (environment variables)

4. **Documentation**:
   - QUICK_START.md
   - PROJECT_ARCHITECTURE.md
   - memory-bank/activeContext.md

## Best Practices

1. **Code Organization**:
   - Keep core logic in arbitrage_bot/core/
   - Place utilities in arbitrage_bot/utils/
   - Add new DEX integrations in core/dex/

2. **Documentation**:
   - Update activeContext.md for current focus
   - Keep integration guides current
   - Document new patterns in systemPatterns.md

3. **Development Flow**:
   - Test changes with test_web3_changes.py
   - Use examples/ for reference implementations
   - Follow deployment checklist for releases

## Archive Policy
- Outdated components moved to archive/
- Backup in archive/cleanup_backup_20250311/
- Reference implementations preserved in examples/

## Future Optimizations
1. AI Integration (docker-ai-tools/)
   - Profit optimization
   - Pattern recognition
   - Risk analysis

2. Dashboard Enhancements
   - Extended metrics
   - AI insights integration
   - Advanced visualization

3. Flashbots Integration
   - MEV protection
   - Bundle optimization
   - Profit maximization