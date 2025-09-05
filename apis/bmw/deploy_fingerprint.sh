#!/bin/bash

# BMW API Fingerprint Deployment Script for Google Cloud Run
# ==========================================================
# Deploys the BMW API with dynamic fingerprint generation (PR #743)

set -e

# Configuration
PROJECT_ID="draiv-427115"
REGION="europe-west6"
SERVICE_NAME="bmw-api-fingerprint"
MEMORY="512Mi"
CPU="1"
TIMEOUT="60s"
MAX_INSTANCES="100"
MIN_INSTANCES="0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}BMW API Fingerprint Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    exit 1
fi

# Set project
echo -e "${YELLOW}Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}

# Check current authentication
echo -e "${YELLOW}Checking authentication...${NC}"
CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
echo -e "Deploying as: ${GREEN}${CURRENT_ACCOUNT}${NC}"

# Ask for confirmation
read -p "Deploy BMW API with fingerprint to Cloud Run? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment cancelled.${NC}"
    exit 1
fi

# Create requirements file specifically for Cloud Run
echo -e "${YELLOW}Creating requirements file...${NC}"
cat > requirements-fingerprint.txt << EOF
functions-framework==3.8.2
flask==3.0.3
aiohttp==3.10.10
google-cloud-storage==2.18.2
google-cloud-secret-manager==2.20.2
python-dotenv==1.0.1
EOF

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"

gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --entry-point bmw_api_fingerprint \
    --region ${REGION} \
    --platform managed \
    --memory ${MEMORY} \
    --cpu ${CPU} \
    --timeout ${TIMEOUT} \
    --max-instances ${MAX_INSTANCES} \
    --min-instances ${MIN_INSTANCES} \
    --allow-unauthenticated \
    --set-env-vars="FUNCTION_NAME=${SERVICE_NAME}" \
    --set-env-vars="BMW_REGION=rest_of_world" \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --format='value(status.url)')

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Service URL: ${GREEN}${SERVICE_URL}${NC}"
echo ""

# Test the health endpoint
echo -e "${YELLOW}Testing health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s "${SERVICE_URL}/health" | python3 -m json.tool 2>/dev/null || echo "Failed to parse JSON")

if [[ $HEALTH_RESPONSE == *"fingerprint"* ]]; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
    echo "$HEALTH_RESPONSE" | head -20
else
    echo -e "${RED}❌ Health check failed or unexpected response${NC}"
    echo "$HEALTH_RESPONSE"
fi

echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Test authentication with real BMW credentials:"
echo "   curl -X POST ${SERVICE_URL} \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"email\":\"your-email\",\"password\":\"your-password\",\"action\":\"status\"}'"
echo ""
echo "2. Check the unique fingerprint for this deployment:"
echo "   curl ${SERVICE_URL}/health | jq .fingerprint"
echo ""
echo "3. Monitor logs:"
echo "   gcloud run logs read --service ${SERVICE_NAME} --region ${REGION}"
echo ""
echo "4. View metrics:"
echo "   gcloud run services describe ${SERVICE_NAME} --region ${REGION}"

# Clean up temporary requirements file
rm -f requirements-fingerprint.txt

echo -e "${GREEN}Deployment script complete!${NC}"