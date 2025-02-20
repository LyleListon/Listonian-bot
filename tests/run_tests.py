#!/usr/bin/env python3
"""Test runner for arbitrage bot."""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_runner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TestRunner')

class TestRunner:
    """Manages test execution and reporting."""
    
    def __init__(self):
        """Initialize test runner."""
        self.test_dir = Path("tests")
        self.report_dir = Path("test_reports")
        self.report_dir.mkdir(exist_ok=True)
        
        # Test categories
        self.categories = {
            "integration": [
                "test_aerodrome.py",
                "test_performance.py",
                "test_process.py"
            ]
        }
        
    def run_tests(self):
        """Run all test suites."""
        start_time = time.time()
        results = {}
        
        try:
            # Run each category
            for category, test_files in self.categories.items():
                category_results = []
                logger.info(f"Running {category} tests...")
                
                for test_file in test_files:
                    test_path = self.test_dir / category / test_file
                    if not test_path.exists():
                        logger.error(f"Test file not found: {test_path}")
                        continue
                        
                    # Run tests
                    result = self._run_test_file(test_path)
                    category_results.append(result)
                    
                results[category] = category_results
                
            # Generate report
            self._generate_report(results, time.time() - start_time)
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            sys.exit(1)
            
    def _run_test_file(self, test_path: Path) -> Dict[str, Any]:
        """Run tests in a single file."""
        logger.info(f"Running tests in {test_path}")
        
        try:
            # Run pytest in a subprocess
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-v",
                    "--asyncio-mode=auto",
                    str(test_path)
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(Path.cwd())}
            )
            
            # Parse output
            output = result.stdout + result.stderr
            logger.info(output)
            
            return {
                "file": test_path.name,
                "status": "passed" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
                "output": output
            }
            
        except Exception as e:
            logger.error(f"Error running {test_path}: {e}")
            return {
                "file": test_path.name,
                "status": "error",
                "error": str(e),
                "output": ""
            }
            
    def _generate_report(self, results: Dict[str, List[Dict[str, Any]]], duration: float):
        """Generate test report."""
        try:
            # Create report
            report = {
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "results": results,
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "error": 0
                }
            }
            
            # Calculate summary
            for category_results in results.values():
                for result in category_results:
                    report["summary"]["total"] += 1
                    report["summary"][result["status"]] += 1
                    
            # Save report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.report_dir / f"test_report_{timestamp}.json"
            
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
                
            # Log summary
            logger.info("\nTest Summary:")
            logger.info(f"Total Tests: {report['summary']['total']}")
            logger.info(f"Passed: {report['summary']['passed']}")
            logger.info(f"Failed: {report['summary']['failed']}")
            logger.info(f"Errors: {report['summary']['error']}")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            
def main():
    """Main entry point."""
    try:
        runner = TestRunner()
        runner.run_tests()
        
    except KeyboardInterrupt:
        logger.info("\nTest run interrupted")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()
