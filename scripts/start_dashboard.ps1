# Start Dashboard Script
Write-Host "Starting dashboard..." -ForegroundColor Cyan

# Create necessary directories if they don't exist
Write-Host "Creating necessary directories..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path logs, memory-bank, "memory-bank\trades", "memory-bank\metrics", "memory-bank\state" | Out-Null
Write-Host "Directories created successfully." -ForegroundColor Green

# Initialize memory bank
Write-Host "Initializing memory bank..." -ForegroundColor Cyan
python scripts/initialize_memory_bank.py
Write-Host "Memory bank initialized successfully." -ForegroundColor Green

# Start the dashboard
Write-Host "Starting dashboard..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python run_dashboard.py" -WindowStyle Normal

# Wait for the dashboard to initialize
Write-Host "Waiting for dashboard to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Open the dashboard in the default browser
Write-Host "Opening dashboard in browser..." -ForegroundColor Cyan
Start-Process "http://localhost:9050"

Write-Host "Dashboard started successfully!" -ForegroundColor Green
Write-Host "Dashboard URL: http://localhost:9050" -ForegroundColor Cyan
