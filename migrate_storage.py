#!/usr/bin/env python3

import os
import json
import shutil
from pathlib import Path

# Category mapping from old to new
CATEGORY_MAPPING = {
    'trades': 'transactions',
    'opportunities': 'market_data',
    'market_data': 'analytics',
    'config': 'storage',
    'performance': 'analytics',
    'errors': 'temp',
    'health': 'cache'
}

def migrate_storage():
    """Migrate storage data to new category structure."""
    base_path = Path('arbitrage_bot/core/storage/data')
    
    # Create new category directories
    for new_category in set(CATEGORY_MAPPING.values()):
        (base_path / new_category).mkdir(parents=True, exist_ok=True)
        (base_path / new_category / 'data').mkdir(exist_ok=True)
        (base_path / new_category / 'backups').mkdir(exist_ok=True)
        (base_path / new_category / 'metadata').mkdir(exist_ok=True)
        (base_path / new_category / 'schemas').mkdir(exist_ok=True)
    
    # Migrate data from old to new categories
    for old_category, new_category in CATEGORY_MAPPING.items():
        old_path = base_path / old_category
        new_path = base_path / new_category
        
        if not old_path.exists():
            continue
        
        # Migrate metadata
        old_metadata = old_path / 'metadata' / 'items.json'
        if old_metadata.exists():
            try:
                with open(old_metadata, 'r') as f:
                    metadata = json.load(f)
                    # Update category in metadata
                    for key in metadata:
                        if isinstance(metadata[key], dict):
                            metadata[key]['category'] = new_category
                new_metadata = new_path / 'metadata' / 'items.json'
                with open(new_metadata, 'w') as f:
                    json.dump(metadata, f, indent=2)
            except Exception as e:
                print(f"Error migrating metadata for {old_category}: {e}")
        
        # Migrate data files
        old_data = old_path / 'data'
        new_data = new_path / 'data'
        if old_data.exists():
            for file in old_data.glob('*.json'):
                try:
                    shutil.copy2(file, new_data / file.name)
                except Exception as e:
                    print(f"Error migrating data file {file}: {e}")
        
        # Migrate backup files
        old_backups = old_path / 'backups'
        new_backups = new_path / 'backups'
        if old_backups.exists():
            for file in old_backups.glob('*.json'):
                try:
                    shutil.copy2(file, new_backups / file.name)
                except Exception as e:
                    print(f"Error migrating backup file {file}: {e}")
        
        # Migrate schema files
        old_schemas = old_path / 'schemas'
        new_schemas = new_path / 'schemas'
        if old_schemas.exists():
            for file in old_schemas.glob('*.json'):
                try:
                    shutil.copy2(file, new_schemas / file.name)
                except Exception as e:
                    print(f"Error migrating schema file {file}: {e}")
    
    # Remove old category directories
    for old_category in CATEGORY_MAPPING:
        old_path = base_path / old_category
        if old_path.exists():
            try:
                shutil.rmtree(old_path)
            except Exception as e:
                print(f"Error removing old category directory {old_path}: {e}")

if __name__ == '__main__':
    migrate_storage()
