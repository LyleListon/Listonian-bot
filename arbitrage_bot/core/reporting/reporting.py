"""Simplified reporting system."""

import logging
import json
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ReportingSystem:
    """Mock reporting system that saves reports as JSON."""

    def __init__(
        self,
        analytics_system: Any,
        market_analyzer: Any,
        ml_system: Any,
        benchmarking_system: Any,
        config: Dict[str, Any]
    ):
        """Initialize reporting system.

        Args:
            analytics_system: Analytics system instance
            market_analyzer: Market analyzer instance
            ml_system: ML system instance
            benchmarking_system: Benchmarking system instance
            config: Configuration dictionary
        """
        self.analytics = analytics_system
        self.market_analyzer = market_analyzer
        self.ml_system = ml_system
        self.benchmarking = benchmarking_system
        self.config = config
        
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        logger.info("Mock reporting system initialized")

    async def generate_report(
        self,
        report_type: str,
        data: Dict[str, Any]
    ) -> str:
        """Generate a report as JSON.

        Args:
            report_type: Type of report
            data: Report data

        Returns:
            Path to generated report file
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.reports_dir / f"{report_type}_{timestamp}.json"
            
            report_data = {
                "type": report_type,
                "timestamp": timestamp,
                "data": data
            }
            
            with open(report_path, "w") as f:
                json.dump(report_data, f, indent=2)
                
            logger.info(f"Generated {report_type} report: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return ""

    async def get_recent_reports(
        self,
        report_type: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent reports.

        Args:
            report_type: Optional type filter
            limit: Maximum number of reports to return

        Returns:
            List of report data
        """
        try:
            reports = []
            pattern = f"{report_type}_*.json" if report_type else "*.json"
            
            for report_file in sorted(
                self.reports_dir.glob(pattern),
                reverse=True
            )[:limit]:
                try:
                    with open(report_file) as f:
                        reports.append(json.load(f))
                except Exception as e:
                    logger.error(f"Failed to load report {report_file}: {e}")
                    continue
                    
            return reports
            
        except Exception as e:
            logger.error(f"Failed to get recent reports: {e}")
            return []

async def create_reporting_system(
    analytics_system: Any,
    market_analyzer: Any,
    ml_system: Any,
    benchmarking_system: Any,
    config: Dict[str, Any]
) -> ReportingSystem:
    """Create reporting system."""
    try:
        system = ReportingSystem(
            analytics_system,
            market_analyzer,
            ml_system,
            benchmarking_system,
            config
        )
        return system
    except Exception as e:
        logger.error(f"Failed to create reporting system: {e}")
        raise
