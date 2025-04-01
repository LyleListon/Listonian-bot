# PowerShell script to uninstall Python
Write-Host "This script will:"
Write-Host "1. Uninstall pip from system Python"
Write-Host "2. Open Programs and Features for Python uninstallation"
Write-Host ""
Write-Host "Press any key to continue or Ctrl+C to cancel..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')

Write-Host "`nUninstalling pip..."
Start-Process -FilePath "C:\Program Files\Python312\python.exe" -ArgumentList "-m", "pip", "uninstall", "pip", "-y" -Wait -NoNewWindow

Write-Host "`nOpening Programs and Features..."
Start-Process "appwiz.cpl"

Write-Host "`nPlease uninstall Python 3.12 from Programs and Features."
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')