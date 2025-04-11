"""Simplified template system using JSON."""

import logging
import json
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplateSystem:
    """Mock template system using JSON."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize template system.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.templates_dir = Path("report_templates")
        self.templates_dir.mkdir(exist_ok=True)

        # Create default templates
        self._create_default_templates()

        logger.info("Mock template system initialized")

    def _create_default_templates(self):
        """Create default report templates."""
        try:
            default_templates = {
                "performance": {
                    "sections": ["Portfolio Value", "Trade History", "Gas Usage"],
                    "format": "json",
                },
                "market": {
                    "sections": ["Price Analysis", "Volume Analysis", "Trend Analysis"],
                    "format": "json",
                },
            }

            for name, template in default_templates.items():
                template_path = self.templates_dir / f"{name}.json"
                if not template_path.exists():
                    with open(template_path, "w") as f:
                        json.dump(template, f, indent=2)

            logger.info("Created default templates")

        except Exception as e:
            logger.error(f"Failed to create default templates: {e}")

    async def get_template(self, template_name: str) -> Dict[str, Any]:
        """Get a report template.

        Args:
            template_name: Name of template to get

        Returns:
            Template configuration
        """
        try:
            template_path = self.templates_dir / f"{template_name}.json"
            if not template_path.exists():
                logger.warning(f"Template {template_name} not found")
                return {}

            with open(template_path) as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Failed to get template {template_name}: {e}")
            return {}

    async def save_template(self, template_name: str, template: Dict[str, Any]) -> bool:
        """Save a report template.

        Args:
            template_name: Name of template
            template: Template configuration

        Returns:
            True if successful
        """
        try:
            template_path = self.templates_dir / f"{template_name}.json"
            with open(template_path, "w") as f:
                json.dump(template, f, indent=2)

            logger.info(f"Saved template {template_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to save template {template_name}: {e}")
            return False

    async def list_templates(self) -> List[str]:
        """Get list of available templates.

        Returns:
            List of template names
        """
        try:
            return [p.stem for p in self.templates_dir.glob("*.json")]
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []

    async def delete_template(self, template_name: str) -> bool:
        """Delete a report template.

        Args:
            template_name: Name of template to delete

        Returns:
            True if successful
        """
        try:
            template_path = self.templates_dir / f"{template_name}.json"
            if template_path.exists():
                template_path.unlink()
                logger.info(f"Deleted template {template_name}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete template {template_name}: {e}")
            return False


async def create_template_system(config: Dict[str, Any]) -> TemplateSystem:
    """Create template system."""
    try:
        system = TemplateSystem(config)
        return system
    except Exception as e:
        logger.error(f"Failed to create template system: {e}")
        raise
