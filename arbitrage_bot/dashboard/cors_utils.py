"""CORS utilities for the dashboard."""

from functools import wraps
from quart import Response, request


def add_cors_headers(response):
    """Add CORS headers to response"""
    response.headers.update(
        {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "3600",
        }
    )
    return response


def handle_options(f):
    """Decorator to handle OPTIONS requests"""

    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if request.method == "OPTIONS":
            response = Response("", status=204)
            return add_cors_headers(response)
        return await f(*args, **kwargs)

    return decorated_function
