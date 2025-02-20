"""Run the dashboard application."""

import os
import sys
from pathlib import Path

# Add parent directory to sys.path to allow absolute imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from arbitrage_bot.dashboard.app import create_app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get('DASHBOARD_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
