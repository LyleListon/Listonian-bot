# PowerShell script to start the robust dashboard system
# This script bypasses execution policy for itself only

Write-Host "Starting Robust Bot Dashboard System" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""

Write-Host "Step 1: Starting robust API server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -Command `"python robust_bot_api_server.py`""

Write-Host "Step 2: Waiting for API server to initialize (5 seconds)..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host "Step 3: Starting HTTP server for dashboard..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -Command `"python -m http.server 8080`""

Write-Host "Step 4: Opening dashboard in browser..." -ForegroundColor Cyan
Start-Sleep -Seconds 2
Start-Process "http://localhost:8080/robust_dashboard.html"

Write-Host ""
Write-Host "Dashboard system started successfully!" -ForegroundColor Green
Write-Host "API Server: http://localhost:8081" -ForegroundColor Yellow
Write-Host "Dashboard: http://localhost:8080/robust_dashboard.html" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit this window (servers will continue running)..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
