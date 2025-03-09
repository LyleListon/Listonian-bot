from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ..templates_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def test_page(request: Request):
    """
    Render the test dashboard page that displays real-time memory bank data
    """
    return templates.TemplateResponse(
        "test.html",
        {
            "request": request,
            "page_title": "Dashboard Test"
        }
    )
