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
Write-Host "[1/3] Building source distribution and wheel..." -ForegroundColor Yellow
python -m build

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Build failed!" -ForegroundColor Red
    exit 1
}

# 3. Check with twine
Write-Host "[2/3] Verifying distribution packages with twine..." -ForegroundColor Yellow
twine check dist/*

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Twine verification failed!" -ForegroundColor Red
    exit 1
}

# 4. Upload to PyPI
Write-Host "[3/3] Ready to upload to PyPI." -ForegroundColor Green
$confirm = Read-Host "Proceed with uploading to PyPI? (y/n)"
if ($confirm -eq "y" -or $confirm -eq "Y") {
    twine upload dist/*
    Write-Host "[SUCCESS] Published successfully to PyPI!" -ForegroundColor Green
} else {
    Write-Host "[INFO] Upload skipped." -ForegroundColor Yellow
}
