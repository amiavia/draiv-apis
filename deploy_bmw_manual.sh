#!/bin/bash
# Manual deployment script for BMW API Stateless
# Run this from Google Cloud Shell

echo "🚀 Deploying BMW API Stateless to Google Cloud Functions"
echo "================================================"

# Configuration
PROJECT_ID="${GCP_PROJECT:-miavia-422212}"
FUNCTION_NAME="bmw_api_stateless"
REGION="${GCP_REGION:-europe-west6}"
RUNTIME="python311"

# Set project
echo "📌 Setting project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Create deployment directory
echo "📦 Preparing deployment files..."
mkdir -p /tmp/bmw_deploy
cd /tmp/bmw_deploy

# Download files from GitHub
echo "⬇️ Downloading latest code from GitHub..."
curl -s https://raw.githubusercontent.com/amiavia/draiv-apis/master/apis/bmw/src/main_stateless.py > main.py
curl -s https://raw.githubusercontent.com/amiavia/draiv-apis/master/apis/bmw/requirements-stateless.txt > requirements.txt

# Show file sizes to confirm download
echo "📋 Files prepared:"
ls -lh

# Deploy function
echo "☁️ Deploying to Google Cloud Functions..."
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=$RUNTIME \
    --region=$REGION \
    --source=. \
    --entry-point=bmw_api \
    --trigger-http \
    --allow-unauthenticated \
    --memory=256MB \
    --timeout=300s \
    --max-instances=100

# Get function URL
echo "🔗 Getting function URL..."
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME \
    --region=$REGION \
    --gen2 \
    --format="value(serviceConfig.uri)")

echo ""
echo "✅ Deployment complete!"
echo "================================"
echo "Function URL: $FUNCTION_URL"
echo ""
echo "📊 View logs with:"
echo "gcloud functions logs read $FUNCTION_NAME --region=$REGION"
echo ""
echo "🧪 Test CORS with:"
echo "curl -X OPTIONS $FUNCTION_URL"