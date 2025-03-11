@echo off
echo ===============================================================================
echo SIMPLIFIED ARBITRAGE DASHBOARD
echo ===============================================================================
echo.

echo Creating required directories...
mkdir templates 2>nul
mkdir static 2>nul
mkdir static\css 2>nul
mkdir logs 2>nul
mkdir data 2>nul
mkdir data\performance 2>nul
mkdir data\transactions 2>nul

echo Installing required packages...
pip install fastapi uvicorn jinja2 python-dotenv web3

echo Creating basic template file...
if not exist "templates\index.html" (
    echo ^<!DOCTYPE html^> > templates\index.html
    echo ^<html lang="en"^> >> templates\index.html
    echo ^<head^> >> templates\index.html
    echo     ^<meta charset="UTF-8"^> >> templates\index.html
    echo     ^<meta name="viewport" content="width=device-width, initial-scale=1.0"^> >> templates\index.html
    echo     ^<title^>Simplified Arbitrage Dashboard^</title^> >> templates\index.html
    echo     ^<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"^> >> templates\index.html
    echo ^</head^> >> templates\index.html
    echo ^<body^> >> templates\index.html
    echo     ^<div class="container mt-5"^> >> templates\index.html
    echo         ^<div class="card"^> >> templates\index.html
    echo             ^<div class="card-header bg-primary text-white"^> >> templates\index.html
    echo                 ^<h2^>Arbitrage Dashboard^</h2^> >> templates\index.html
    echo             ^</div^> >> templates\index.html
    echo             ^<div class="card-body"^> >> templates\index.html
    echo                 ^<div class="alert alert-success"^> >> templates\index.html
    echo                     ^<h4^>Dashboard is running!^</h4^> >> templates\index.html
    echo                     ^<p^>Status: {{ status }}^</p^> >> templates\index.html
    echo                     ^<p^>Uptime: {{ uptime }}^</p^> >> templates\index.html
    echo                     ^<p^>Current time: {{ current_time }}^</p^> >> templates\index.html
    echo                 ^</div^> >> templates\index.html
    echo             ^</div^> >> templates\index.html
    echo         ^</div^> >> templates\index.html
    echo     ^</div^> >> templates\index.html
    echo     ^<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"^>^</script^> >> templates\index.html
    echo ^</body^> >> templates\index.html
    echo ^</html^> >> templates\index.html
)

echo Creating CSS file...
if not exist "static\css\styles.css" (
    echo body { > static\css\styles.css
    echo     background-color: #f8f9fa; >> static\css\styles.css
    echo } >> static\css\styles.css
    echo .card { >> static\css\styles.css
    echo     margin-bottom: 20px; >> static\css\styles.css
    echo } >> static\css\styles.css
)

echo.
echo Running simplified dashboard...
python simple_dashboard.py

echo.
echo Dashboard stopped.
echo ===============================================================================
pause