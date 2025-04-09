# Simple script to start the dashboard
Write-Host "Starting dashboard..." -ForegroundColor Cyan

# Set environment variables
$env:PYTHONPATH = $PWD
$env:MEMORY_BANK_PATH = Join-Path $PWD "memory-bank"

# Create necessary directories
New-Item -ItemType Directory -Force -Path logs, memory-bank, "memory-bank\trades", "memory-bank\metrics", "memory-bank\state" | Out-Null

# Initialize memory bank
Write-Host "Initializing memory bank..." -ForegroundColor Cyan
python scripts/initialize_memory_bank.py

# Start the dashboard
Write-Host "Starting dashboard..." -ForegroundColor Cyan
python run_dashboard.py
