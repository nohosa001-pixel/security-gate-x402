Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  PyPI Release Packager - Security Gate  " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Clean previous build artifacts
if (Test-Path "dist") {
    Remove-Item -Path "dist" -Recurse -Force
}
if (Test-Path "build") {
    Remove-Item -Path "build" -Recurse -Force
}
Get-ChildItem -Path . -Filter "*.egg-info" -Directory | Remove-Item -Recurse -Force

# 2. Build distributions
Write-Host "[1/2] Building source distribution and wheel with uv..." -ForegroundColor Yellow
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv build
} else {
    python -m build
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Build failed!" -ForegroundColor Red
    exit 1
}

# 3. Upload to PyPI
Write-Host "[2/2] Ready to upload to PyPI." -ForegroundColor Green
$confirm = Read-Host "Proceed with uploading to PyPI? (y/n)"
if ($confirm -eq "y" -or $confirm -eq "Y") {
    if (-not $env:UV_PUBLISH_TOKEN -and -not $env:TWINE_PASSWORD) {
        $token = Read-Host "Enter PyPI API Token (pypi-...)" -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($token)
        $tokenPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        $env:UV_PUBLISH_TOKEN = $tokenPlain
    }
    
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv publish
    } else {
        twine upload dist/*
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Published successfully to PyPI!" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Publish failed. Check your token and version." -ForegroundColor Red
    }
} else {
    Write-Host "[INFO] Upload skipped." -ForegroundColor Yellow
}
