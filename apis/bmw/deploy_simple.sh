#!/bin/bash

# Deploy BMW API Simple - Docker Workaround Approach
# Uses bimmer_connected with Android fingerprint patching

echo "🚀 Deploying BMW API Simple (Docker Workaround + bimmer_connected)..."

# Set deployment configuration
FUNCTION_NAME="bmw_api_simple"
REGION="europe-west6"
SOURCE_DIR="src"
ENTRY_POINT="bmw_api_simple"
RUNTIME="python310"
MEMORY="1Gi"
TIMEOUT="120s"
MAX_INSTANCES="10"

echo "📋 Deployment Configuration:"
echo "   Function: $FUNCTION_NAME"
echo "   Region: $REGION"
echo "   Source: $SOURCE_DIR"
echo "   Entry Point: $ENTRY_POINT"
echo "   Runtime: $RUNTIME"
echo ""

# Copy requirements file to source directory
echo "📦 Copying requirements file..."
cp requirements-simple.txt src/requirements.txt

# Deploy the function
echo "🔧 Deploying to Google Cloud Functions..."
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime $RUNTIME \
    --source $SOURCE_DIR \
    --entry-point $ENTRY_POINT \
    --trigger-http \
    --allow-unauthenticated \
    --region $REGION \
    --memory $MEMORY \
    --timeout $TIMEOUT \
    --max-instances $MAX_INSTANCES \
    --set-env-vars ENVIRONMENT=production

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment successful!"
    echo ""
    echo "🔗 Function URL:"
    echo "   https://$REGION-miavia-422212.cloudfunctions.net/$FUNCTION_NAME"
    echo ""
    echo "🩺 Health Check:"
    echo "   curl https://$REGION-miavia-422212.cloudfunctions.net/$FUNCTION_NAME/health"
    echo ""
    echo "🧪 Test Command:"
    echo "   curl -X POST \"https://$REGION-miavia-422212.cloudfunctions.net/$FUNCTION_NAME\" \\"
    echo "     -H \"Content-Type: application/json\" \\"
    echo "     -d '{"
    echo "       \"email\": \"Info@miavia.ai\","
    echo "       \"password\": \"qegbe6-ritdoz-vikDeK\","
    echo "       \"wkn\": \"WBA3K51040K175114\","
    echo "       \"action\": \"status\","
    echo "       \"hcaptcha\": \"FRESH_HCAPTCHA_TOKEN\""
    echo "     }'"
    echo ""
    echo "🎯 This implementation uses:"
    echo "   - Docker workaround approach (proven to work)"
    echo "   - Dynamic PR #743 Android fingerprints (unique per deployment)"
    echo "   - Standard bimmer_connected authentication (maintained library)"
    echo "   - Cloud Function infrastructure (scalable)"
else
    echo ""
    echo "❌ Deployment failed!"
    echo "Check the error messages above for details."
    exit 1
fi