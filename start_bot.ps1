# Stop any running Python processes
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force

# Clean up secure directory
Remove-Item -Path "secure" -Recurse -Force -ErrorAction SilentlyContinue

# Set master key
$env:MASTER_KEY = $env:MASTER_KEY

Write-Host "Starting Arbitrage Bot and Dashboard in LIVE MODE..."

# Load environment variables from .env.production
Get-Content .env.production | ForEach-Object {
    if ($_ -match '^[^#].*=.*$') {
        $key, $value = $_ -split '=', 2
        $key = $key.Trim()
        $value = $value.Trim()
        [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        # Also store in secure environment
        python -c "from arbitrage_bot.utils.secure_env import SecureEnvironment; SecureEnvironment().secure_store('$key', '$value')"
    }
}

# Initialize secure environment
python init_secure.py

# Start the bot
python -m arbitrage_bot.dashboard.run

Write-Host "Bot and dashboard started in LIVE MODE. Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
