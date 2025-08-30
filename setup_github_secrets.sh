#!/bin/bash

# Setup GitHub Secrets for Automated Deployment
# This script needs to be run from your Google Cloud Shell where the service account key was created

echo "=========================================="
echo "GitHub Secrets Setup for BMW API Deployment"
echo "=========================================="

# Check if we're in the right place
if [ ! -f ~/bmw-api-sa-key.json ]; then
    echo "❌ Service account key not found at ~/bmw-api-sa-key.json"
    echo "Please run this from Google Cloud Shell where you created the key"
    exit 1
fi

# Read the service account key
SA_KEY=$(cat ~/bmw-api-sa-key.json | base64 -w 0)

echo "Adding GitHub secrets..."

# Add the service account key as a GitHub secret
gh secret set GCP_SA_KEY_PRODUCTION --body="$(cat ~/bmw-api-sa-key.json)" --repo amiavia/draiv-apis

# Add other useful secrets
gh secret set GCP_PROJECT_ID --body="miavia-422212" --repo amiavia/draiv-apis
gh secret set GCP_REGION --body="us-central1" --repo amiavia/draiv-apis

echo "✅ GitHub secrets added successfully!"
echo ""
echo "The following secrets have been added:"
echo "  - GCP_SA_KEY_PRODUCTION (service account key)"
echo "  - GCP_PROJECT_ID (miavia-422212)"
echo "  - GCP_REGION (us-central1)"
echo ""
echo "Your GitHub Actions workflow is now ready to deploy automatically!"