# Arbitrage Bot Documentation

## System Architecture

The system is divided into several key components, each documented with detailed flow diagrams:

1. [Core Components Flow](CORE_FLOW.md)
   - Main system architecture
   - Component relationships
   - MCP integration

2. [Dashboard Flow](DASHBOARD_FLOW.md)
   - Web interface components
   - Real-time monitoring
   - Data visualization

3. [Trade Execution Flow](TRADE_FLOW.md)
   - Opportunity detection
   - Risk validation
   - Execution process
   - Failure handling

## Failed Attempts Documentation

See [failed_attempts/](failed_attempts/) directory for detailed documentation of problems encountered and solutions found:

- Price monitoring challenges
- Trade execution issues
- Gas optimization attempts
- Integration problems

## Development Guidelines

1. **Documentation First Policy**
   - Update [CURRENT_WORK_STATUS.md](../CURRENT_WORK_STATUS.md) before making changes
   - Document failed attempts immediately
   - Keep diagrams current

2. **Code Organization**
   - Core logic in arbitrage_bot/core/
   - Web interface in arbitrage_bot/dashboard/
   - Utilities in arbitrage_bot/utils/
   - Configurations in arbitrage_bot/configs/

3. **MCP Integration**
   - crypto-price server for real-time pricing
   - market-analysis server for opportunity detection
   - See [project_map.html](../project_map.html) for details

## Quick Links

- [Project Map](../project_map.html) - Visual system overview
- [Current Status](../CURRENT_WORK_STATUS.md) - Latest development status
- [Quick Start Guide](../QUICK_START_GUIDE.md) - Getting started
- [System Monitor Guide](../SYSTEM_MONITOR_GUIDE.md) - Monitoring and maintenance
