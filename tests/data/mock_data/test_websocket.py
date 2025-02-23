"""Test WebSocket functionality with aiohttp."""

import os
import sys
import asyncio
from datetime import datetime
from aiohttp import web
import aiohttp_cors
from aiohttp_sse import sse_response
import aiohttp_jinja2
import jinja2

async def index(request):
    """Serve test page."""
    return web.FileResponse('test_websocket.html')

async def websocket_handler(request):
    """Handle WebSocket connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    print("Client connected")

    try:
        # Send test data
        await ws.send_json({
            'type': 'memory_update',
            'data': {
                'memory_stats': {
                    'market_data_size': 100,
                    'transactions_size': 50,
                    'analytics_size': 25
                }
            },
            'timestamp': datetime.now().isoformat()
        })

        async for msg in ws:
            if msg.type == web.WSMsgType.ERROR:
                print("WebSocket connection closed with exception {}".format(ws.exception()))

        return ws

    finally:
        print("Client disconnected")

async def events_handler(request):
    """Handle Server-Sent Events."""
    async with sse_response(request) as resp:
        while True:
            # Send test data
            await resp.send_json({
                'type': 'memory_update',
                'data': {
                    'memory_stats': {
                        'market_data_size': 100,
                        'transactions_size': 50,
                        'analytics_size': 25
                    }
                },
                'timestamp': datetime.now().isoformat()
            })
            await asyncio.sleep(5)  # Send update every 5 seconds

async def init_app():
    """Initialize the application."""
    app = web.Application()
    
    # Set up CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        )
    })

    # Set up routes
    app.router.add_get('/', index)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/events', events_handler)

    # Configure CORS on all routes
    for route in list(app.router.routes()):
        cors.add(route)

    return app

async def main():
    """Main entry point."""
    port = int(os.getenv('DASHBOARD_PORT', 5001))
    print("Starting WebSocket test server on port {}".format(port))
    print("Visit http://localhost:{} to view the test page".format(port))
    
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    # Keep the server running
    while True:
        await asyncio.sleep(3600)  # Sleep for an hour

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print("Server error: {}".format(e))
        sys.exit(1)