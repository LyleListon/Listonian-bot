"""Simplified delivery system."""

import logging
import json
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class DeliverySystem:
    """Mock delivery system that saves to files."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize delivery system.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.delivery_dir = Path("report_deliveries")
        self.delivery_dir.mkdir(exist_ok=True)
        
        logger.info("Mock delivery system initialized")

    async def deliver_report(
        self,
        report_path: str,
        delivery_type: str = "file",
        **kwargs
    ) -> bool:
        """Deliver a report.

        Args:
            report_path: Path to report file
            delivery_type: Type of delivery (only 'file' supported)
            **kwargs: Additional delivery options

        Returns:
            True if successful
        """
        try:
            if delivery_type != "file":
                logger.warning(f"Unsupported delivery type: {delivery_type}")
                return False
                
            report_file = Path(report_path)
            if not report_file.exists():
                logger.error(f"Report file not found: {report_path}")
                return False
                
            # Copy report to delivery directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            delivery_path = self.delivery_dir / f"{report_file.stem}_{timestamp}{report_file.suffix}"
            
            with open(report_file) as f:
                report_data = json.load(f)
                
            with open(delivery_path, "w") as f:
                json.dump(report_data, f, indent=2)
                
            logger.info(f"Delivered report to {delivery_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deliver report: {e}")
            return False

    async def get_delivery_status(
        self,
        report_path: str
    ) -> Dict[str, Any]:
        """Get delivery status for a report.

        Args:
            report_path: Path to report file

        Returns:
            Delivery status information
        """
        try:
            report_file = Path(report_path)
            if not report_file.exists():
                return {
                    "status": "error",
                    "message": "Report file not found"
                }
                
            deliveries = list(
                self.delivery_dir.glob(f"{report_file.stem}_*.json")
            )
            
            return {
                "status": "delivered" if deliveries else "pending",
                "count": len(deliveries),
                "latest": str(sorted(deliveries)[-1]) if deliveries else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get delivery status: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def list_deliveries(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get list of recent deliveries.

        Args:
            limit: Maximum number of deliveries to return

        Returns:
            List of delivery information
        """
        try:
            deliveries = []
            for delivery_file in sorted(
                self.delivery_dir.glob("*.json"),
                reverse=True
            )[:limit]:
                try:
                    with open(delivery_file) as f:
                        report_data = json.load(f)
                    deliveries.append({
                        "path": str(delivery_file),
                        "timestamp": delivery_file.stem.split("_")[-2:],
                        "type": report_data.get("type", "unknown")
                    })
                except Exception as e:
                    logger.error(f"Failed to load delivery {delivery_file}: {e}")
                    continue
                    
            return deliveries
            
        except Exception as e:
            logger.error(f"Failed to list deliveries: {e}")
            return []

async def create_delivery_system(
    config: Dict[str, Any]
) -> DeliverySystem:
    """Create delivery system."""
    try:
        system = DeliverySystem(config)
        return system
    except Exception as e:
        logger.error(f"Failed to create delivery system: {e}")
        raise
