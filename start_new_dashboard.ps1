# Arbitrage System New Dashboard
# PowerShell Wrapper

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "                  ARBITRAGE SYSTEM NEW DASHBOARD                              " -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting the new FastAPI dashboard..." -ForegroundColor Green
Write-Host ""

# Navigate to the new_dashboard directory and run the script
Push-Location -Path "new_dashboard"
try {
    & ".\start_dashboard.ps1"
}
finally {
    Pop-Location
}