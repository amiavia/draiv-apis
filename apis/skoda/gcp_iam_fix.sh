#!/bin/bash
# GCP IAM Fix Commands for Skoda API
# Copy and paste these commands into Google Cloud Shell or your local gcloud CLI

set -e

echo "🔧 Fixing IAM permissions for Skoda API deployment..."

# Set project variables
PROJECT_ID="miavia-422212"
FUNCTION_NAME="skoda_api_stateless"
REGION="europe-west6"

echo "Project: $PROJECT_ID"
echo "Function: $FUNCTION_NAME"
echo "Region: $REGION"

# 1. Fix GitHub Actions Service Account Permissions
echo ""
echo "📋 Step 1: Finding GitHub Actions service account..."

# List service accounts to find the GitHub Actions one
gcloud iam service-accounts list --project=$PROJECT_ID --format="table(email,displayName)"

echo ""
echo "🔧 Step 2: Adding required roles to GitHub Actions service account..."
echo "Replace 'github-actions@miavia-422212.iam.gserviceaccount.com' with your actual service account email from above"

# Add Cloud Run Admin role (gives setIamPolicy permission)
echo "Adding Cloud Run Admin role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@miavia-422212.iam.gserviceaccount.com" \
    --role="roles/run.admin"

# Add Cloud Functions Admin role (if not already present)
echo "Adding Cloud Functions Admin role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions@miavia-422212.iam.gserviceaccount.com" \
    --role="roles/cloudfunctions.admin"

echo ""
echo "🚀 Step 3: Fixing existing function IAM (if function exists)..."

# Check if function exists and fix its IAM policy
if gcloud functions describe $FUNCTION_NAME --region=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Function exists, setting public access..."
    gcloud functions add-iam-policy-binding $FUNCTION_NAME \
        --region=$REGION \
        --member="allUsers" \
        --role="roles/cloudfunctions.invoker" \
        --project=$PROJECT_ID
    
    echo "✅ Function is now publicly accessible!"
    
    # Test the function
    FUNCTION_URL="https://$REGION-$PROJECT_ID.cloudfunctions.net/$FUNCTION_NAME"
    echo "🧪 Testing function..."
    curl -s -X OPTIONS "$FUNCTION_URL" -w "\nHTTP Status: %{http_code}\n"
    
    echo "📋 Function URL: $FUNCTION_URL"
else
    echo "Function doesn't exist yet - will be fixed on next deployment"
fi

echo ""
echo "✅ IAM permissions have been configured!"
echo ""
echo "🚀 Next steps:"
echo "1. Re-run the GitHub Actions deployment"
echo "2. The deployment should now complete successfully"
echo "3. Test the API with:"
echo ""
echo "curl -X POST 'https://$REGION-$PROJECT_ID.cloudfunctions.net/$FUNCTION_NAME' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"email\":\"Info@miavia.ai\",\"password\":\"wozWi9-matvah-xonmyq\",\"vin\":\"TMBJJ7NX5MY061741\",\"action\":\"status\"}'"