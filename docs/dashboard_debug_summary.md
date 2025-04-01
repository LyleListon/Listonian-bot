# Dashboard Debugging Summary (2025-03-31)

## Initial Problem

The user reported that the dashboard (`new_dashboard`) was not displaying any metrics, including basic system metrics like CPU and memory usage.

## Investigation Steps & Findings

1.  **WebSocket Logging:** Added logging to `new_dashboard/dashboard/routes/websocket.py`. Logs showed WebSocket connections were established, but no data was being received from the `MetricsService` queue.
2.  **MetricsService Check:** Examined `arbitrage_bot/dashboard/metrics_service.py`. Found it has `start()`/`stop()` methods and an update loop responsible for collecting and broadcasting metrics. Suspected it wasn't being started correctly.
3.  **Startup Crash (Exit Code 5):** Attempts to add logging to `MetricsService` revealed the application was crashing on startup with exit code 5 before the service could fully start.
4.  **Startup Script (`run_dashboard.py`):** Examined `run_dashboard.py`. Found it used Uvicorn to launch the app defined in `new_dashboard:app`.
5.  **App Definition (`new_dashboard/__init__.py`, `new_dashboard/dashboard.py`):** Found the main FastAPI app instance is defined in `new_dashboard/dashboard.py`. This file also contained its own WebSocket logic (`/ws` endpoint, internal `ConnectionManager`) separate from the `MetricsService` and routes in `new_dashboard/dashboard/routes/websocket.py`. Identified a disconnect between the running app and the intended metrics system.
6.  **Startup Crash Cause:** Traced the crash to the `@app.on_event("startup")` function in `new_dashboard/dashboard.py`, likely during component initialization (`create_production_components` or `.initialize()` calls). Added detailed logging to this function.
7.  **Syntax Errors:** Corrected several syntax errors (indentation, stray characters) introduced during diff applications within `new_dashboard/dashboard.py`.
8.  **Integration Attempt:** Modified `new_dashboard/dashboard.py` and `new_dashboard/core/dependencies.py` to:
    *   Use the existing `ServiceRegistry` pattern.
    *   Register `MetricsService`, `MemoryService`, etc., using `register_services()`.
    *   Use the `lifespan` context manager in `FastAPI()` to automatically start/stop registered services (including `MetricsService`).
    *   Include the router from `new_dashboard/dashboard/routes/websocket.py` into the main app.
    *   Comment out the redundant, locally defined `ConnectionManager` and `/ws` endpoint in `dashboard.py`.
9.  **Frontend (`index.html`) Check:** Examined `new_dashboard/static/index.html`. Found the JavaScript was connecting to the old `/ws` endpoint. Updated it to connect to the correct `/dashboard/ws/metrics` endpoint. Also adjusted JS functions to handle the expected data structure.
10. **Module Loading Error:** Encountered `ModuleNotFoundError: No module named 'new_dashboard'` when running `python new_dashboard/run_dashboard.py` from the root directory. This indicated a Python path issue.
11. **Corrected Execution:** Switched to running the app using `python -m new_dashboard.run_dashboard` from the root directory.
12. **Uvicorn Loading Error:** Encountered `ERROR: Error loading ASGI app. Could not import module "new_dashboard.app"`. This happened because Uvicorn was looking for `app` in `new_dashboard/__init__.py` instead of `new_dashboard/dashboard.py`.
13. **Corrected Uvicorn Target:** Modified `run_dashboard.py` to specify the correct app location for Uvicorn: `"new_dashboard.dashboard:app"`. Also disabled `reload=True`.
14. **Persistent Startup Crash:** Despite the corrected Uvicorn target, the application still seems to crash immediately when run with `python -m new_dashboard.run_dashboard`, preventing log file creation and indicating a very early error, likely during imports initiated by `dependencies.py`. Reverted logging changes in `dependencies.py` as a precaution.

## Current Status

*   The application fails to start when run correctly (`python -m new_dashboard.run_dashboard` from root), likely due to an error during the import phase within `new_dashboard/core/dependencies.py` or the service modules it imports (`MemoryService`, `MetricsService`, `SystemService`).
*   The exact import error is not captured because the crash happens before output redirection can create the log file.
*   The frontend (`index.html`) has been updated to point to the correct WebSocket endpoint (`/dashboard/ws/metrics`).

## Next Steps (When Resuming)

1.  **Isolate Import Error:** Systematically comment out the service imports (`MemoryService`, `MetricsService`, `SystemService`) and their registrations within `new_dashboard/core/dependencies.py` one by one to identify which specific import or instantiation is causing the immediate crash upon startup.
2.  **Debug Failing Service:** Once the problematic service file is identified, examine it for module-level errors (syntax errors, import errors, code that runs on import and fails).
3.  **Verify Startup:** Once the import/startup crash is resolved, confirm the application starts successfully using `python -m new_dashboard.run_dashboard` and that Uvicorn reports running on port 9050.
4.  **Test Dashboard:** Load `http://localhost:9050` and check if metrics display correctly. Check the browser console for any remaining errors (e.g., wallet errors, data parsing issues).