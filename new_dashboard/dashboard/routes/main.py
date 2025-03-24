"""Main routes for the dashboard."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from ..core.logging import get_logger

router = APIRouter()
# Templates instance will be set by run.py
templates = None

@router.get("/")
async def root(request: Request):
    """Serve the main dashboard page."""
    logger = get_logger("main_routes")
    logger.info("Rendering index page")
    
    try:
        if templates is None:
            logger.error("Templates not initialized")
            raise HTTPException(status_code=500, detail="Templates not initialized")
            
        logger.info("Rendering template index.html")
        try:
            response = templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "title": "Arbitrage Bot Dashboard"
                }
            )
            logger.info("Template rendered successfully")
            return response
        except Exception as e:
            logger.error(f"Error rendering template: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Template rendering error: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )