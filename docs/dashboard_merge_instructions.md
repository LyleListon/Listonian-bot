# Dashboard Merge Instructions

## Files to Include
```
arbitrage_bot/dashboard/
├── app.py
├── init__.py
├── cors_utils.py
├── database.py
├── dex_utils.py
├── performance_tracker.py
├── web3_utils.py
├── websocket_server.py
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── analytics.js
│       ├── history.js
│       ├── opportunities.js
│       ├── settings.js
│       └── websocket.js
└── templates/
    ├── index.html
    ├── opportunities.html
    ├── history.html
    ├── settings.html
    └── [other template files]

start_dashboard.ps1
start_dashboard.py
```

## Git Commands to Run Locally

1. Create a new branch for the dashboard feature:
```bash
git checkout -b feature/dashboard
```

2. Add this codespace as a remote:
```bash
git remote add codespace https://github.com/codespaces/[your-codespace-name]
```

3. Pull the changes:
```bash
git pull codespace main
```

4. Review and commit the changes:
```bash
git add arbitrage_bot/dashboard/
git add start_dashboard.ps1
git add start_dashboard.py
git commit -m "Add real-time dashboard with Socket.IO"
```

5. Merge into your target branch:
```bash
git checkout [your-branch]
git merge feature/dashboard
```

## Key Features Added
- Real-time data visualization with Socket.IO
- Memory and performance monitoring
- Trade history and opportunities tracking
- Responsive UI with Tailwind CSS
- WebSocket-based live updates
- Configurable settings interface

## Dependencies Added
- Flask
- Flask-SocketIO
- eventlet
- Tailwind CSS (via CDN)
- Chart.js (via CDN)

## Configuration
The dashboard runs on port 5001 by default. You can modify this in the start_dashboard scripts or by setting the DASHBOARD_PORT environment variable.

## Running Locally
After merging, you can start the dashboard with:
```bash
./start_dashboard.ps1  # On Windows
# or
python start_dashboard.py  # On any platform
```

The dashboard will be available at http://localhost:5001