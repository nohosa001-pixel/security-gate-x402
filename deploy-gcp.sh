#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Run Deployment Script for agent-security-gate-x402
# ==============================================================================
set -e

# Load local .env file if present
if [ -f .env ]; then
  # Export variables without overriding existing environment
  set -a
  source <(grep -v '^#' .env | sed -e 's/\r$//')
  set +a
fi

# Configuration
SERVICE_NAME="agent-security-gate-x402"
REGION="${GCP_REGION:-asia-northeast3}"
SERVER_WALLET="${SERVER_WALLET_ADDRESS:-0x255F9991233f86B29dB847c8d5b8CB9915e80dCf}"
SERVER_ENV="${ENV:-production}"

echo "🚀 [GCP Deployment] Starting deployment for $SERVICE_NAME to region $REGION..."

# 1. Verify gcloud CLI is authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: 'gcloud' CLI is not installed. Please install Google Cloud SDK."
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project 2> /dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No active GCP project configured. Run 'gcloud config set project <PROJECT_ID>'."
    exit 1
fi

echo "📦 GCP Project: $PROJECT_ID"
echo "💰 Settlement Wallet: $SERVER_WALLET"
echo "🌐 Target Environment: $SERVER_ENV"

# 2. Enable necessary Google Cloud APIs
echo "⚙️ Enabling Cloud Run, Cloud Build, and Artifact Registry APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project "$PROJECT_ID"

# 3. Build & Deploy directly via Cloud Run source build
echo "🏗️ Building and deploying container to Google Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --command="" \
  --args="" \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 100 \
  --set-env-vars "ENV=$SERVER_ENV,SERVER_WALLET_ADDRESS=$SERVER_WALLET,BASE_CHAIN_ID=${BASE_CHAIN_ID:-8453},FACILITATOR_URL=${FACILITATOR_URL:-https://facilitator.x402.org/v2/verify},FREE_TRIAL_LIMIT=3,RATE_LIMIT_PER_MINUTE=120" \
  --project "$PROJECT_ID"





# 4. Fetch service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format 'value(status.url)' --project "$PROJECT_ID")

echo ""
echo "=============================================================================="
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "📡 Service URL: $SERVICE_URL"
echo "🔍 Health Check: $SERVICE_URL/health"
echo "📜 Terms of Service: $SERVICE_URL/terms"
echo "🛡️ AP2 Manifest: $SERVICE_URL/.well-known/ap2"
echo "🚀 Inspection API: $SERVICE_URL/api/v1/inspect"
echo "=============================================================================="
