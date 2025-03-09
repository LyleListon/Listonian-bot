"""Test routes for verifying dashboard functionality."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()

# Set up templates
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

@router.get("/test")
async def test_page(request: Request):
    """Serve a simple test page."""
    return templates.TemplateResponse(
        "test.html",
        {
            "request": request,
            "page_title": "Test Dashboard"
        }
    )