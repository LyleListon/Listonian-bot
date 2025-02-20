Set-Location -Path $PSScriptRoot
npm run compile
if ($LASTEXITCODE -eq 0) {
    npm run deploy:flash
}
