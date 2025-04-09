#!/usr/bin/env python3
"""
Project Cleanup Script

This script helps identify unused files and organize the project.
"""

import os
import sys
import re
import json
import shutil
import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Directories to exclude from analysis
EXCLUDE_DIRS = {
    ".git", ".github", ".vscode", ".pytest_cache", "__pycache__",
    "venv", ".venv", "node_modules", "test_reports", "output"
}

# File extensions to analyze
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".sol"}
CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".ini", ".env"}
SCRIPT_EXTENSIONS = {".bat", ".ps1", ".sh"}
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".pdf"}

# Core files that should not be moved or deleted
CORE_FILES = {
    "run_bot.py",
    "run_dashboard.py",
    "run_base_dex_scanner_mcp.py",
    "run_base_dex_scanner_mcp_with_api.py",
    "config.json",
    ".env",
    ".env.production",
    "README.md"
}

# Core directories that should not be moved or deleted
CORE_DIRS = {
    "arbitrage_bot",
    "new_dashboard",
    "configs",
    "scripts",
    "memory-bank",
    "secure",
    ".augment"
}

class ProjectAnalyzer:
    """Analyze the project structure and identify unused files."""
    
    def __init__(self, root_dir: Path):
        """Initialize the analyzer."""
        self.root_dir = root_dir
        self.all_files: Dict[Path, datetime.datetime] = {}
        self.imports: Dict[Path, Set[str]] = {}
        self.imported_by: Dict[str, Set[Path]] = {}
        self.entry_points: Set[Path] = set()
        self.used_files: Set[Path] = set()
        self.unused_files: Set[Path] = set()
        self.junk_candidates: Set[Path] = set()
        self.backup_files: Set[Path] = set()
        self.temp_files: Set[Path] = set()
        
    def scan_files(self) -> None:
        """Scan all files in the project."""
        print("Scanning files...")
        
        for root, dirs, files in os.walk(self.root_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.root_dir)
                
                # Skip files in excluded directories
                if any(part in EXCLUDE_DIRS for part in rel_path.parts):
                    continue
                
                # Record file with its last modified time
                self.all_files[rel_path] = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                
                # Identify backup and temp files
                if re.search(r'(\.bak|\.backup|\.old|\.tmp|\.temp|~)$', file):
                    self.backup_files.add(rel_path)
                elif re.search(r'(\.swp|\.swo|\.swn|\.pyc|\.pyo)$', file):
                    self.temp_files.add(rel_path)
        
        print(f"Found {len(self.all_files)} files")
        print(f"Found {len(self.backup_files)} backup files")
        print(f"Found {len(self.temp_files)} temporary files")
    
    def identify_entry_points(self) -> None:
        """Identify entry points in the project."""
        print("Identifying entry points...")
        
        # Main Python files in root directory
        for file_path in self.all_files:
            if file_path.suffix == '.py' and file_path.parts[0] not in EXCLUDE_DIRS:
                if file_path.name.startswith('run_') or file_path.name == 'main.py':
                    self.entry_points.add(file_path)
        
        # Script files
        for file_path in self.all_files:
            if file_path.suffix in SCRIPT_EXTENSIONS and 'scripts' in file_path.parts:
                self.entry_points.add(file_path)
        
        print(f"Found {len(self.entry_points)} entry points")
    
    def analyze_imports(self) -> None:
        """Analyze imports in Python files."""
        print("Analyzing imports...")
        
        import_pattern = re.compile(r'^\s*(?:from|import)\s+([a-zA-Z0-9_.]+)')
        
        for file_path in self.all_files:
            if file_path.suffix != '.py':
                continue
            
            self.imports[file_path] = set()
            
            try:
                with open(self.root_dir / file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        match = import_pattern.match(line)
                        if match:
                            module = match.group(1).split('.')[0]
                            self.imports[file_path].add(module)
                            
                            if module not in self.imported_by:
                                self.imported_by[module] = set()
                            self.imported_by[module].add(file_path)
            except Exception as e:
                print(f"Error analyzing imports in {file_path}: {e}")
    
    def trace_dependencies(self) -> None:
        """Trace dependencies from entry points."""
        print("Tracing dependencies...")
        
        # Start with entry points
        to_process = list(self.entry_points)
        processed = set()
        
        while to_process:
            file_path = to_process.pop(0)
            if file_path in processed:
                continue
            
            processed.add(file_path)
            self.used_files.add(file_path)
            
            # If it's a Python file, check its imports
            if file_path in self.imports:
                for module in self.imports[file_path]:
                    # Find files that might be this module
                    module_files = self._find_module_files(module)
                    for module_file in module_files:
                        if module_file not in processed:
                            to_process.append(module_file)
        
        # Identify unused files
        self.unused_files = set(self.all_files.keys()) - self.used_files - self.backup_files - self.temp_files
        
        print(f"Found {len(self.used_files)} used files")
        print(f"Found {len(self.unused_files)} potentially unused files")
    
    def _find_module_files(self, module: str) -> List[Path]:
        """Find files that might implement the given module."""
        result = []
        
        # Check if the module is directly imported by other files
        if module in self.imported_by:
            return list(self.imported_by[module])
        
        # Look for files with matching names
        for file_path in self.all_files:
            if file_path.stem == module and file_path.suffix == '.py':
                result.append(file_path)
            elif file_path.name == f"{module}.py":
                result.append(file_path)
            elif file_path.parent.name == module and file_path.name == '__init__.py':
                result.append(file_path)
        
        return result
    
    def identify_junk(self) -> None:
        """Identify potential junk files."""
        print("Identifying potential junk files...")
        
        # Files that are likely junk
        for file_path in self.unused_files:
            # Skip core files
            if file_path.name in CORE_FILES:
                continue
            
            # Skip files in core directories
            if file_path.parts[0] in CORE_DIRS:
                continue
            
            # Check for common junk patterns
            if (re.search(r'(test_|_test|\.test\.|\.spec\.|example|demo|sample)', file_path.name.lower()) or
                re.search(r'(\.log|\.tmp|\.temp|\.bak|\.backup|\.old|~)$', file_path.name.lower()) or
                re.search(r'(\.swp|\.swo|\.swn|\.pyc|\.pyo)$', file_path.name.lower())):
                self.junk_candidates.add(file_path)
        
        print(f"Found {len(self.junk_candidates)} potential junk files")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a report of the analysis."""
        print("Generating report...")
        
        # Group files by directory
        files_by_dir: Dict[str, List[Path]] = {}
        for file_path in self.all_files:
            dir_name = str(file_path.parent)
            if dir_name not in files_by_dir:
                files_by_dir[dir_name] = []
            files_by_dir[dir_name].append(file_path)
        
        # Group unused files by directory
        unused_by_dir: Dict[str, List[Path]] = {}
        for file_path in self.unused_files:
            dir_name = str(file_path.parent)
            if dir_name not in unused_by_dir:
                unused_by_dir[dir_name] = []
            unused_by_dir[dir_name].append(file_path)
        
        # Group junk candidates by directory
        junk_by_dir: Dict[str, List[Path]] = {}
        for file_path in self.junk_candidates:
            dir_name = str(file_path.parent)
            if dir_name not in junk_by_dir:
                junk_by_dir[dir_name] = []
            junk_by_dir[dir_name].append(file_path)
        
        # Create report
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_files": len(self.all_files),
            "entry_points": [str(p) for p in sorted(self.entry_points)],
            "used_files_count": len(self.used_files),
            "unused_files_count": len(self.unused_files),
            "backup_files_count": len(self.backup_files),
            "temp_files_count": len(self.temp_files),
            "junk_candidates_count": len(self.junk_candidates),
            "files_by_directory": {k: len(v) for k, v in files_by_dir.items()},
            "unused_files_by_directory": {k: len(v) for k, v in unused_by_dir.items()},
            "junk_candidates_by_directory": {k: len(v) for k, v in junk_by_dir.items()},
            "backup_files": [str(p) for p in sorted(self.backup_files)],
            "temp_files": [str(p) for p in sorted(self.temp_files)],
            "junk_candidates": [str(p) for p in sorted(self.junk_candidates)],
            "unused_files": [str(p) for p in sorted(self.unused_files)]
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], output_path: Path) -> None:
        """Save the report to a file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"Report saved to {output_path}")
    
    def create_junk_directory(self) -> Path:
        """Create a directory for junk files."""
        junk_dir = self.root_dir / "junk"
        junk_dir.mkdir(exist_ok=True)
        return junk_dir
    
    def move_junk_files(self, junk_dir: Path) -> None:
        """Move junk files to the junk directory."""
        print("Moving junk files...")
        
        for file_path in self.junk_candidates:
            src = self.root_dir / file_path
            dst = junk_dir / file_path.name
            
            # Ensure we don't overwrite existing files
            if dst.exists():
                dst = junk_dir / f"{file_path.stem}_{file_path.parent.name}{file_path.suffix}"
            
            # Create parent directories if needed
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                shutil.move(src, dst)
                print(f"Moved {file_path} to {dst.relative_to(self.root_dir)}")
            except Exception as e:
                print(f"Error moving {file_path}: {e}")
    
    def run(self) -> Dict[str, Any]:
        """Run the analysis."""
        self.scan_files()
        self.identify_entry_points()
        self.analyze_imports()
        self.trace_dependencies()
        self.identify_junk()
        
        report = self.generate_report()
        report_path = self.root_dir / "cleanup_report.json"
        self.save_report(report, report_path)
        
        return report

def main():
    """Main entry point."""
    analyzer = ProjectAnalyzer(project_root)
    report = analyzer.run()
    
    # Ask if user wants to move junk files
    print("\nAnalysis complete.")
    print(f"Found {report['junk_candidates_count']} potential junk files.")
    
    if report['junk_candidates_count'] > 0:
        response = input("Do you want to move these files to a 'junk' directory? (y/n): ")
        if response.lower() == 'y':
            junk_dir = analyzer.create_junk_directory()
            analyzer.move_junk_files(junk_dir)
            print(f"\nJunk files moved to {junk_dir}")
            print("You can review these files and delete them if they are truly unused.")
    
    print("\nCleanup suggestions:")
    print("1. Review the cleanup_report.json file for details on unused files")
    print("2. Consider organizing your project into a more structured layout")
    print("3. Create a .gitignore file to exclude temporary and generated files")
    print("4. Document your project structure in README.md")

if __name__ == "__main__":
    main()
