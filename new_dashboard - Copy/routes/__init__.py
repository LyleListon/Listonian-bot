from fastapi import APIRouter

router = APIRouter()

# Import all route modules here
from . import test

# Include all routers
router.include_router(test.router)