"""Run the dashboard application."""

import os
import sys
import asyncio
from pathlib import Path
from aiohttp import web

# Add parent directory to sys.path to allow absolute imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from arbitrage_bot.dashboard.app import create_app

async def run_async():
    """Run the async application."""
    app, socketio = await create_app()
    port = int(os.environ.get('DASHBOARD_PORT', 5000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    await asyncio.Event().wait()  # Keep the server running

if __name__ == "__main__":
    asyncio.run(run_async())
