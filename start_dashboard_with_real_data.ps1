# PowerShell script to start the dashboard with real data
Write-Host "Starting dashboard with real data..." -ForegroundColor Green
python start_dashboard_with_real_data.py
Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
