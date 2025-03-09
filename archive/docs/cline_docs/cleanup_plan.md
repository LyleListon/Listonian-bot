# Project Cleanup Plan

## Overview
This plan outlines a strategy to organize the project while preserving all existing code and documentation for reference.

## 1. Create Archive Structure
```
archive/
├── configs/              # Old configuration files
├── docs/                # Old documentation
├── scripts/             # Old startup scripts
└── src/                 # Old source code
```

## 2. Configuration Management
### Current Issues
- Multiple config locations
- Overlapping settings
- Inconsistent formats

### Action Plan
1. **Preserve Existing**
   - Move to `archive/configs/`
   - Keep all versions for reference

2. **Create New Structure**
   ```
   configs/
   ├── default.json       # Base configuration
   ├── production.json    # Production overrides
   └── local.json        # Local development settings
   ```

## 3. Entry Points
### Current Issues
- Multiple startup scripts
- Inconsistent launch methods
- Scattered entry points

### Action Plan
1. **Archive Existing**
   - Move to `archive/scripts/`
   - Maintain all variants (.bat, .ps1, .sh)

2. **Create Unified Entry Points**
   ```
   scripts/
   ├── start.py          # Main entry point
   ├── dashboard.py      # Dashboard entry point
   └── cli.py           # Command-line interface
   ```

## 4. Documentation Organization
### Current Issues
- Fragmented documentation
- Overlapping information
- Multiple locations

### Action Plan
1. **Archive Existing**
   - Move to `archive/docs/`
   - Preserve all versions

2. **Create New Structure**
   ```
   docs/
   ├── architecture/     # System design docs
   ├── guides/          # User & developer guides
   ├── api/            # API documentation
   └── README.md       # Main documentation entry
   ```

## 5. Code Structure
### Current Issues
- Mixed old and new implementations
- Inconsistent patterns
- Tight coupling

### Action Plan
1. **Archive Existing**
   - Move to `archive/src/`
   - Keep all implementations

2. **Create Clean Structure**
   ```
   src/
   ├── core/            # Core business logic
   ├── blockchain/      # Blockchain interactions
   ├── dashboard/       # Dashboard application
   └── utils/          # Shared utilities
   ```

## Implementation Steps

### Phase 1: Archive Creation (No Disruption)
1. Create archive directory structure
2. Copy (not move) all existing files to archive
3. Verify archive completeness
4. Document archive structure

### Phase 2: New Structure Setup
1. Create new directory structure
2. Set up new configuration system
3. Create unified entry points
4. Establish new documentation structure

### Phase 3: Gradual Migration
1. Move active development to new structure
2. Update references to use new paths
3. Verify system functionality
4. Keep archive for reference

## Notes
- All existing code remains available in archive
- No permanent deletion of files
- Archive serves as reference implementation
- New structure follows best practices
- Migration can be reversed if needed

## Success Criteria
1. All existing code preserved in archive
2. Clean, standardized new structure
3. Single source of truth for active development
4. Clear separation between archive and active code
5. No loss of functionality or information

Last Updated: 2025-02-10