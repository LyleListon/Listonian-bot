@echo off
echo Starting Arbitrage Bot and Dashboard in LIVE MODE...

REM Set master key
set MASTER_KEY=%MASTER_KEY%

REM Initialize secure environment
python init_secure.py

REM Use PowerShell to load environment variables
powershell -Command "Get-Content .env.production | ForEach-Object { if ($_ -match '^[^#].*=.*$') { $key, $value = $_ -split '=', 2; [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), 'Process') } }"

REM Start the bot
python -m arbitrage_bot.dashboard.run

echo Bot and dashboard started in LIVE MODE. Press any key to exit this window...
pause
