# Set environment variables
$env:DASHBOARD_PORT = "5001"
$env:PYTHONPATH = $PWD

# Create required directories if they don't exist
New-Item -ItemType Directory -Force -Path "arbitrage_bot/dashboard/static" | Out-Null
New-Item -ItemType Directory -Force -Path "arbitrage_bot/dashboard/templates" | Out-Null

# Start the dashboard
Write-Host "Starting dashboard on port 5001..."
Write-Host "In GitHub Codespace: Please ensure port 5001 is forwarded in the Ports tab"
Write-Host "The dashboard will be available at the forwarded URL provided by GitHub"

try {
    python start_dashboard.py
} catch {
    Write-Host "Error starting dashboard: $_"
    exit 1
}