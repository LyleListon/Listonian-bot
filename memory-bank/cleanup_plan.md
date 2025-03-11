# Project Cleanup Plan

## Core Components (Keep)
- arbitrage_bot/ (Main bot implementation)
- abi/ (Critical contract ABIs)
- configs/ (Configuration files)
- memory-bank/ (Project documentation)
- requirements.txt (Core dependencies)
- setup.py (Package setup)
- .env (Environment configuration)
- LICENSE
- README.md

## Dashboard Consolidation
Keep:
- final_dashboard.py (Main dashboard)
- dashboard/ (Dashboard components)

Remove (Outdated/Redundant):
- basic_dashboard.py
- arbitrage_dashboard.py
- enhanced_arbitrage_dashboard.py
- minimal_dashboard.py
- minimal_real_dashboard.py
- multi_chain_dashboard.py
- simple_dashboard.py
- token_price_dashboard.py
- alchemy_price_dashboard.py
- live_data_dashboard.py

## Script Consolidation
Keep:
- start_production.py (Main entry point)
- deploy_production.ps1 (Deployment script)
- setup_production.py (Production setup)

Remove (Redundant/Development):
- start_all.bat/ps1/sh
- start_bot.bat/ps1
- start_dashboard.bat/ps1/py
- run_*.bat (All run_* batch files)
- setup_*.bat (All setup_* batch files except production)
- fix_*.bat (All fix_* batch files)
- check_*.py/bat (All check_* files)
- cleanup_*.bat (All cleanup_* files)
- rebuild_*.bat (All rebuild_* files)

## Documentation Consolidation
Keep:
- DEPLOYMENT_CHECKLIST.md
- FLASHBOTS_INTEGRATION_GUIDE.md
- PROJECT_ARCHITECTURE.md
- QUICK_START.md

Remove (Outdated/Redundant):
- PROJECT_ARCHITECTURE_ASCII.txt (Replaced by .md version)
- MEMORY_BANK_UPDATES.md (Content moved to activeContext.md)
- STATUS_UPDATE.md (Content in progress.md)
- PRODUCTION_CLEANUP.md (Will be replaced by this plan)

## Directory Cleanup
Keep:
- arbitrage_bot/
- abi/
- configs/
- contracts/
- memory-bank/
- tests/

Consider Removing:
- analytics/ (If functionality moved to dashboard)
- archive/ (Old files)
- cline_docs/ (If outdated)
- docker-ai-tools/ (If not actively used)
- examples/ (If outdated)
- minimal_dashboard/ (Redundant)
- monitoring_data/ (If data archived)
- new_dashboard/ (If merged into main dashboard)
- scripts/ (If scripts consolidated)
- static/ (If not actively used)
- test_reports/ (If tests regenerate these)

## Next Steps
1. Verify active components in use
2. Archive important historical data
3. Remove redundant files
4. Update documentation to reflect changes
5. Test core functionality after cleanup

## Notes
- Backup all files before removal
- Update any dependent paths in remaining files
- Document any necessary manual steps
- Test system thoroughly after cleanup