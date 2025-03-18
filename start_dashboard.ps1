# Stop any existing Python processes running the dashboard
Get-Process python | Where-Object { $_.CommandLine -like '*final_dashboard.py*' } | Stop-Process -Force

# Wait a moment for the port to be released
Start-Sleep -Seconds 1

# Start the dashboard and open it in the default browser
Start-Process python -ArgumentList "final_dashboard.py" -NoNewWindow
Start-Sleep -Seconds 2  # Give the server time to start
Start-Process "http://localhost:9095"