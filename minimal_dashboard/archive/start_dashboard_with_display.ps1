# Start Xvfb
$env:DISPLAY = ":99"
Start-Process -FilePath "Xvfb" -ArgumentList ":99 -screen 0 1280x800x24" -NoNewWindow

# Wait for Xvfb to start
Start-Sleep -Seconds 2

# Start the dashboard
python start_dashboard.py