from fastapi.templating import Jinja2Templates
from pathlib import Path

# Get the absolute path to the templates directory
templates_dir = Path(__file__).parent / "templates"

# Initialize templates
templates = Jinja2Templates(directory=str(templates_dir))
