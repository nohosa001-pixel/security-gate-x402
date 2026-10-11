Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  NPM Release Packager - Security Gate   " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$pluginDir = Join-Path $PSScriptRoot "packages\plugin-security-gate"
Push-Location $pluginDir

try {
    # 1. Verify code formatting and linting
    Write-Host "[1/4] Running linter with biome..." -ForegroundColor Yellow
    bun run lint
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Linting failed!" -ForegroundColor Red
        exit 1
    }

    # 2. Run unit and integration tests
    Write-Host "[2/4] Running test suite..." -ForegroundColor Yellow
    bun test
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Tests failed!" -ForegroundColor Red
        exit 1
    }

    # 3. Clean and build TypeScript distribution
    Write-Host "[3/4] Building bundle and TypeScript declarations..." -ForegroundColor Yellow
    bun run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Build failed!" -ForegroundColor Red
        exit 1
    }

    # 4. Publish to npm
    Write-Host "[4/4] Ready to publish to npm registry." -ForegroundColor Green
    $pkgJson = Get-Content "package.json" | ConvertFrom-Json
    Write-Host "Package: $($pkgJson.name) @ v$($pkgJson.version)" -ForegroundColor Cyan
    
    $confirm = Read-Host "Proceed with npm publish? (y/n)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Write-Host "Executing npm publish --access public..." -ForegroundColor Yellow
        npm publish --access public
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[SUCCESS] Successfully published to npm!" -ForegroundColor Green
        } else {
            Write-Host "[INFO] If prompted for OTP, run: npm publish --access public --otp=YOUR_CODE" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[INFO] Publish cancelled." -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}
