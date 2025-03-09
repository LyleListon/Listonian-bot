# PowerShell script to install Python 3.12
Write-Host "This script will:"
Write-Host "1. Download Python 3.12.2 installer"
Write-Host "2. Install Python 3.12.2 for current user only"
Write-Host ""
Write-Host "Press any key to continue or Ctrl+C to cancel..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')

# Generate unique temp file name
$tempFile = [System.IO.Path]::GetTempFileName()
$installerPath = [System.IO.Path]::ChangeExtension($tempFile, "exe")
Remove-Item $tempFile -Force
Write-Host "`nTemporary file path: $installerPath"

try {
    # Download Python installer
    Write-Host "`nDownloading Python 3.12.2 installer..."
    $url = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
    
    # Use .NET WebClient for download
    $webClient = New-Object System.Net.WebClient
    $webClient.DownloadFile($url, $installerPath)

    # Install Python
    Write-Host "`nInstalling Python 3.12.2..."
    $arguments = @(
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=1",
        "Include_test=0",
        "Include_launcher=1"
    )
    Start-Process -FilePath $installerPath -ArgumentList $arguments -Wait -NoNewWindow

} catch {
    Write-Host "Error: $_"
} finally {
    # Cleanup
    Write-Host "`nCleaning up..."
    if (Test-Path $installerPath) {
        Remove-Item $installerPath -Force
    }
}

Write-Host "`nPython 3.12.2 installation complete!"
Write-Host "Please restart your terminal for the changes to take effect."
Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')