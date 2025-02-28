# Arbitrage System Example Launcher

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Arbitrage System Example Launcher" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version
    Write-Host "Using $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found. Please install Python and try again." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit
}

# If an argument is provided, use it as the example to run
if ($args.Count -eq 0) {
    Write-Host "Available examples:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Complete Arbitrage Example" -ForegroundColor White
    Write-Host "2. Flash Loan Example" -ForegroundColor White
    Write-Host "3. MEV Protection Example" -ForegroundColor White
    Write-Host "4. Monitoring Dashboard" -ForegroundColor White
    Write-Host "5. Run Tests" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "Enter your choice (1-5)"
} else {
    $choice = $args[0]
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan

switch ($choice) {
    "1" {
        Write-Host "Running Complete Arbitrage Example..." -ForegroundColor Yellow
        Write-Host ""
        python complete_arbitrage_example.py
    }
    "2" {
        Write-Host "Running Flash Loan Example..." -ForegroundColor Yellow
        Write-Host ""
        python flash_loan_example.py
    }
    "3" {
        Write-Host "Running MEV Protection Example..." -ForegroundColor Yellow
        Write-Host ""
        python mev_protection_example.py
    }
    "4" {
        Write-Host "Starting Monitoring Dashboard..." -ForegroundColor Yellow
        Write-Host "The dashboard will be available at http://localhost:8080" -ForegroundColor Green
        Write-Host ""
        
        # Create directory if it doesn't exist
        if (-not (Test-Path "monitoring_data")) {
            New-Item -ItemType Directory -Path "monitoring_data" | Out-Null
        }
        
        # Open browser
        Start-Process "http://localhost:8080"
        
        # Start dashboard
        python -m dashboard.arbitrage_monitor
    }
    "5" {
        Write-Host "Running Tests..." -ForegroundColor Yellow
        Write-Host ""
        pytest tests/flashbots_flash_loan_test.py -v
    }
    default {
        Write-Host "Invalid choice. Please try again." -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Press Enter to exit..." -ForegroundColor Yellow
Read-Host