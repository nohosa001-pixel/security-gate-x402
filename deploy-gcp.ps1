# ==============================================================================
# Google Cloud Run Deployment Script (PowerShell) for agent-security-gate-x402
# ==============================================================================
$ErrorActionPreference = "Stop"

# Load local .env file if present
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $k = $parts[0].Trim()
            $v = $parts[1].Trim()
            if (-not (Get-Item "env:$k" -ErrorAction SilentlyContinue)) {
                [System.Environment]::SetEnvironmentVariable($k, $v, "Process")
            }
        }
    }
}

$SERVICE_NAME = "agent-security-gate-x402"
$REGION = if ($env:GCP_REGION) { $env:GCP_REGION } else { "asia-northeast3" }
$SERVER_WALLET = if ($env:SERVER_WALLET_ADDRESS) { $env:SERVER_WALLET_ADDRESS } else { "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf" }
$SERVER_ENV = if ($env:ENV) { $env:ENV } else { "production" }

Write-Host "🚀 [GCP Deployment] Starting deployment for $SERVICE_NAME to region $REGION..." -ForegroundColor Cyan

# 1. Verify gcloud CLI
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: 'gcloud' CLI is not found. Please install the Google Cloud SDK (https://cloud.google.com/sdk)." -ForegroundColor Red
    exit 1
}

$PROJECT_ID = (gcloud config get-value project 2>$null).Trim()
if (-not $PROJECT_ID) {
    Write-Host "❌ Error: No active GCP project configured. Run 'gcloud config set project <PROJECT_ID>'." -ForegroundColor Red
    exit 1
}

Write-Host "📦 GCP Project: $PROJECT_ID" -ForegroundColor Yellow
Write-Host "💰 Settlement Wallet: $SERVER_WALLET" -ForegroundColor Yellow
Write-Host "🌐 Target Environment: $SERVER_ENV" -ForegroundColor Yellow

# 2. Enable Google Cloud APIs
Write-Host "⚙️ Enabling Cloud Run, Cloud Build, and Artifact Registry APIs..." -ForegroundColor Cyan
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project $PROJECT_ID

# 3. Build & Deploy to Cloud Run
Write-Host "🏗️ Building and deploying container to Google Cloud Run..." -ForegroundColor Cyan
gcloud run deploy $SERVICE_NAME `
  --source . `
  --region $REGION `
  --platform managed `
  --allow-unauthenticated `
  --port 8080 `
  --memory 512Mi `
  --cpu 1 `
  --min-instances 0 `
  --max-instances 100 `
  --set-env-vars "ENV=$SERVER_ENV,SERVER_WALLET_ADDRESS=$SERVER_WALLET,BASE_CHAIN_ID=8453" `
  --project $PROJECT_ID

# 4. Fetch service URL
$SERVICE_URL = (gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID).Trim()

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "🎉 DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "📡 Service URL: $SERVICE_URL" -ForegroundColor White
Write-Host "🔍 Health Check: $SERVICE_URL/health" -ForegroundColor White
Write-Host "📜 Terms of Service: $SERVICE_URL/terms" -ForegroundColor White
Write-Host "🛡️ AP2 Manifest: $SERVICE_URL/.well-known/ap2" -ForegroundColor White
Write-Host "🚀 Inspection API: $SERVICE_URL/api/v1/inspect" -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Green
