Write-Host "`n=== Starting Verification ===`n" -ForegroundColor Green

# Run the verification script
$output = node scripts/verify-wallet.js 2>&1
Write-Host $output

# Check for log file
Write-Host "`n=== Checking Log File ===`n" -ForegroundColor Green
if (Test-Path wallet-verification.log) {
    Get-Content wallet-verification.log | ForEach-Object {
        Write-Host $_
    }
} else {
    Write-Host "Log file not found" -ForegroundColor Red
}

Write-Host "`n=== Verification Complete ===`n" -ForegroundColor Green