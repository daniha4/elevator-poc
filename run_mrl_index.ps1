# run_mrl_index.ps1 — builds data/mrl_index.json from Google Drive
# Double-click or run from PowerShell. API key is never shown on screen.

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host ""
Write-Host "=== MRL Index Builder ===" -ForegroundColor Cyan
Write-Host "Google Drive folder: 15RR-PsCux4QJcW4IzCLIyeKqGjplqo6G" -ForegroundColor Gray
Write-Host ""

# Read key securely (hidden input)
$secure = Read-Host "הדבק את מפתח ה-API" -AsSecureString
$env:GOOGLE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
)

Write-Host ""
Write-Host "מריץ build_mrl_index.py..." -ForegroundColor Yellow

Set-Location $PSScriptRoot
python build_mrl_index.py

Write-Host ""
Write-Host "לחץ Enter לסגירה" -ForegroundColor Gray
Read-Host
