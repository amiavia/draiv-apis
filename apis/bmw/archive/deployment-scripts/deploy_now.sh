#!/bin/bash

# Quick deployment script for BMW API with fingerprint
echo "=================================================="
echo "BMW API Fingerprint Deployment Instructions"
echo "=================================================="
echo ""
echo "The BMW API with dynamic fingerprint has been prepared."
echo "To deploy it, run ONE of these commands:"
echo ""
echo "Option 1: Deploy to draiv-427115 (Staging):"
echo "----------------------------------------"
cat << 'EOF'
gcloud functions deploy bmw_api_fixed \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point bmw_api_fixed \
  --source apis/bmw/src \
  --region europe-west6 \
  --project draiv-427115 \
  --timeout 120 \
  --memory 512MB \
  --set-env-vars ENVIRONMENT=staging,K_SERVICE=bmw_api_fixed
EOF

echo ""
echo "Option 2: Deploy to miavia-422212 (Production):"
echo "----------------------------------------"
cat << 'EOF'
gcloud functions deploy bmw_api_fixed \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point bmw_api_fixed \
  --source apis/bmw/src \
  --region europe-west6 \
  --project miavia-422212 \
  --timeout 120 \
  --memory 512MB \
  --set-env-vars ENVIRONMENT=production,K_SERVICE=bmw_api_fixed
EOF

echo ""
echo "Option 3: Test locally first:"
echo "----------------------------------------"
echo "cd apis/bmw && python3 src/main_fixed.py"
echo ""
echo "After deployment, test with:"
echo "----------------------------------------"
echo 'curl https://europe-west6-[PROJECT].cloudfunctions.net/bmw_api_fixed/health | jq .'
echo ""
echo "The fingerprint in the response should be unique per deployment!"