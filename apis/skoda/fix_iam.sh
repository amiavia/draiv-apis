#!/bin/bash

# Fix IAM permissions for Skoda API Cloud Function
# Run this script if you have gcloud CLI access

set -e

PROJECT_ID="miavia-422212"
FUNCTION_NAME="skoda_api_stateless"
REGION="europe-west6"

echo "🔧 Fixing IAM permissions for Skoda API..."

# Make the function publicly accessible
echo "Setting IAM policy to allow all users..."
gcloud functions add-iam-policy-binding $FUNCTION_NAME \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/cloudfunctions.invoker" \
    --project=$PROJECT_ID

echo "✅ IAM permissions fixed!"

# Test the function
echo "🧪 Testing function access..."
FUNCTION_URL="https://$REGION-$PROJECT_ID.cloudfunctions.net/$FUNCTION_NAME"

curl -s -X OPTIONS "$FUNCTION_URL" -w "\nHTTP Status: %{http_code}\n"

echo "📋 Function is now accessible at: $FUNCTION_URL"