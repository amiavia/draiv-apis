#!/bin/bash

# BMW API Stateless Deployment Script
# Deploy stateless BMW API to Google Cloud Functions

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT:-miavia-422212}"
FUNCTION_NAME="bmw_api_stateless"
REGION="${GCP_REGION:-europe-west6}"
RUNTIME="python311"
ENTRY_POINT="bmw_api"
SOURCE_DIR="./src"
TIMEOUT="90s"
MEMORY="256MB"
MAX_INSTANCES="100"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}BMW API Stateless Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Please install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Parse command line arguments
ENVIRONMENT="staging"
DEPLOY_PRODUCTION=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --production)
            ENVIRONMENT="production"
            DEPLOY_PRODUCTION=true
            shift
            ;;
        --project)
            PROJECT_ID="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --production    Deploy to production environment"
            echo "  --project ID    Specify GCP project ID"
            echo "  --region REGION Specify deployment region"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Set project-specific configuration
if [ "$DEPLOY_PRODUCTION" = true ]; then
    echo -e "${YELLOW}⚠️  Deploying to PRODUCTION environment${NC}"
    echo -n "Are you sure you want to deploy to production? (yes/no): "
    read -r confirmation
    if [ "$confirmation" != "yes" ]; then
        echo -e "${RED}Deployment cancelled${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}Deploying to STAGING environment${NC}"
    # For staging, you might want to use a different project
    # PROJECT_ID="miavia-staging"
fi

echo -e "\n${GREEN}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Function Name: $FUNCTION_NAME"
echo "  Region: $REGION"
echo "  Runtime: $RUNTIME"
echo "  Environment: $ENVIRONMENT"

# Authenticate with Google Cloud
echo -e "\n${GREEN}Authenticating with Google Cloud...${NC}"
gcloud config set project "$PROJECT_ID"

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}Please authenticate with Google Cloud:${NC}"
    gcloud auth login
fi

# Create a temporary deployment directory
TEMP_DIR=$(mktemp -d)
echo -e "\n${GREEN}Preparing deployment package...${NC}"

# Copy only the stateless implementation
cp main_stateless.py "$TEMP_DIR/main.py"
cp ../requirements-stateless.txt "$TEMP_DIR/requirements.txt"

# Create .gcloudignore if it doesn't exist
cat > "$TEMP_DIR/.gcloudignore" << EOF
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/

# Tests
tests/
test_*.py
*_test.py

# Development
.env
.env.*
*.log
*.md
.git/
.github/
.vscode/
*.swp
*.swo

# Local files
deploy_*.sh
Dockerfile
docker-compose.yml
EOF

echo -e "${GREEN}Deploying function to Google Cloud...${NC}"

# Deploy the function
cd "$TEMP_DIR"

gcloud functions deploy "$FUNCTION_NAME" \
    --region="$REGION" \
    --runtime="$RUNTIME" \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point="$ENTRY_POINT" \
    --source=. \
    --timeout="$TIMEOUT" \
    --memory="$MEMORY" \
    --max-instances="$MAX_INSTANCES" \
    --set-env-vars="ENVIRONMENT=$ENVIRONMENT" \
    --project="$PROJECT_ID" \
    --gen2

# Get the function URL
echo -e "\n${GREEN}Getting function URL...${NC}"
FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(url)" 2>/dev/null || \
    gcloud functions describe "$FUNCTION_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(httpsTrigger.url)" 2>/dev/null)

if [ -z "$FUNCTION_URL" ]; then
    echo -e "${YELLOW}Warning: Could not retrieve function URL automatically${NC}"
    echo "Function URL format: https://$REGION-$PROJECT_ID.cloudfunctions.net/$FUNCTION_NAME"
else
    echo -e "${GREEN}Function deployed successfully!${NC}"
    echo -e "URL: ${GREEN}$FUNCTION_URL${NC}"
    
    # Test the deployment with a simple OPTIONS request
    echo -e "\n${GREEN}Testing CORS preflight...${NC}"
    RESPONSE=$(curl -s -X OPTIONS -w "\n%{http_code}" "$FUNCTION_URL")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    
    if [ "$HTTP_CODE" = "204" ]; then
        echo -e "${GREEN}✓ CORS preflight test passed${NC}"
    else
        echo -e "${YELLOW}⚠ CORS preflight returned: $HTTP_CODE${NC}"
    fi
fi

# Cleanup
cd - > /dev/null
rm -rf "$TEMP_DIR"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

# Display usage instructions
echo -e "\n${GREEN}Test the API with:${NC}"
echo "curl -X POST '$FUNCTION_URL' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo '    "email": "your-email@example.com",'
echo '    "password": "your-password",'
echo '    "wkn": "your-vehicle-wkn",'
echo '    "hcaptcha": "hcaptcha-token",'
echo '    "action": "lock"'
echo "  }'"

echo -e "\n${GREEN}View logs with:${NC}"
echo "gcloud functions logs read $FUNCTION_NAME --region=$REGION"

echo -e "\n${GREEN}Delete function with:${NC}"
echo "gcloud functions delete $FUNCTION_NAME --region=$REGION"