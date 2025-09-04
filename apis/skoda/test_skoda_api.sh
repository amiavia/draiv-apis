#!/bin/bash

# Test script for Skoda API Cloud Function
# Run this after deployment to test all functions

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
FUNCTION_URL="https://europe-west6-miavia-422212.cloudfunctions.net/skoda_api_stateless"
VIN="TMBJJ7NX5MY061741"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚗 Testing Skoda API Stateless Cloud Function${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${BLUE}Function URL: ${NC}$FUNCTION_URL"
echo -e "${BLUE}Test VIN: ${NC}$VIN"
echo -e "${BLUE}Test Credentials: ${NC}Info@miavia.ai / 2405"

# Test 1: Health check (OPTIONS request)
echo -e "\n${BLUE}Test 1: CORS Preflight${NC}"
RESPONSE=$(curl -s -X OPTIONS -w "\n%{http_code}" "$FUNCTION_URL")
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "204" ]; then
    echo -e "${GREEN}✓ CORS preflight passed${NC}"
else
    echo -e "${YELLOW}⚠ CORS preflight: $HTTP_CODE${NC}"
fi

# Test 2: Get vehicle status
echo -e "\n${BLUE}Test 2: Get Vehicle Status${NC}"
STATUS_RESPONSE=$(curl -s -X POST "$FUNCTION_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "Info@miavia.ai",
        "password": "wozWi9-matvah-xonmyq", 
        "vin": "'$VIN'",
        "action": "status"
    }')

if echo "$STATUS_RESPONSE" | jq -r '.success' 2>/dev/null | grep -q "true"; then
    echo -e "${GREEN}✓ Status retrieval successful${NC}"
    echo "Vehicle Model: $(echo "$STATUS_RESPONSE" | jq -r '.data.model' 2>/dev/null || echo 'N/A')"
    echo "Locked Status: $(echo "$STATUS_RESPONSE" | jq -r '.data.status.locked' 2>/dev/null || echo 'N/A')"
else
    echo -e "${YELLOW}⚠ Status response:${NC}"
    echo "$STATUS_RESPONSE" | jq . 2>/dev/null || echo "$STATUS_RESPONSE"
fi

# Test 3: Lock vehicle
echo -e "\n${BLUE}Test 3: Lock Vehicle (with S-PIN)${NC}"
LOCK_RESPONSE=$(curl -s -X POST "$FUNCTION_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "Info@miavia.ai",
        "password": "wozWi9-matvah-xonmyq",
        "vin": "'$VIN'",
        "s_pin": "2405",
        "action": "lock"
    }')

if echo "$LOCK_RESPONSE" | jq -r '.success' 2>/dev/null | grep -q "true"; then
    echo -e "${GREEN}✓ Lock command successful${NC}"
    echo "Action: $(echo "$LOCK_RESPONSE" | jq -r '.data.action' 2>/dev/null || echo 'N/A')"
else
    echo -e "${YELLOW}⚠ Lock response:${NC}"
    echo "$LOCK_RESPONSE" | jq . 2>/dev/null || echo "$LOCK_RESPONSE"
fi

# Test 4: Unlock vehicle
echo -e "\n${BLUE}Test 4: Unlock Vehicle (with S-PIN)${NC}"
UNLOCK_RESPONSE=$(curl -s -X POST "$FUNCTION_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "Info@miavia.ai",
        "password": "wozWi9-matvah-xonmyq",
        "vin": "'$VIN'",
        "s_pin": "2405",
        "action": "unlock"
    }')

if echo "$UNLOCK_RESPONSE" | jq -r '.success' 2>/dev/null | grep -q "true"; then
    echo -e "${GREEN}✓ Unlock command successful${NC}"
    echo "Action: $(echo "$UNLOCK_RESPONSE" | jq -r '.data.action' 2>/dev/null || echo 'N/A')"
else
    echo -e "${YELLOW}⚠ Unlock response:${NC}"
    echo "$UNLOCK_RESPONSE" | jq . 2>/dev/null || echo "$UNLOCK_RESPONSE"
fi

# Test 5: Flash lights (no S-PIN required)
echo -e "\n${BLUE}Test 5: Flash Lights${NC}"
FLASH_RESPONSE=$(curl -s -X POST "$FUNCTION_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "Info@miavia.ai",
        "password": "wozWi9-matvah-xonmyq",
        "vin": "'$VIN'",
        "action": "flash"
    }')

if echo "$FLASH_RESPONSE" | jq -r '.success' 2>/dev/null | grep -q "true"; then
    echo -e "${GREEN}✓ Flash lights successful${NC}"
else
    echo -e "${YELLOW}⚠ Flash response:${NC}"
    echo "$FLASH_RESPONSE" | jq . 2>/dev/null || echo "$FLASH_RESPONSE"
fi

# Test 6: Error handling (missing S-PIN)
echo -e "\n${BLUE}Test 6: Error Handling (Lock without S-PIN)${NC}"
ERROR_RESPONSE=$(curl -s -X POST "$FUNCTION_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "Info@miavia.ai",
        "password": "wozWi9-matvah-xonmyq",
        "vin": "'$VIN'",
        "action": "lock"
    }')

if echo "$ERROR_RESPONSE" | jq -r '.success' 2>/dev/null | grep -q "false"; then
    ERROR_TYPE=$(echo "$ERROR_RESPONSE" | jq -r '.error' 2>/dev/null)
    echo -e "${GREEN}✓ Error handling works: $ERROR_TYPE${NC}"
else
    echo -e "${YELLOW}⚠ Expected error but got:${NC}"
    echo "$ERROR_RESPONSE" | jq . 2>/dev/null || echo "$ERROR_RESPONSE"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Testing Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${BLUE}Manual Test Commands:${NC}"
echo ""
echo "# Get vehicle status:"
echo "curl -X POST '$FUNCTION_URL' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo '    "email": "Info@miavia.ai",'
echo '    "password": "wozWi9-matvah-xonmyq",'
echo '    "vin": "'$VIN'",'
echo '    "action": "status"'
echo "  }'"
echo ""
echo "# Lock vehicle:"
echo "curl -X POST '$FUNCTION_URL' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo '    "email": "Info@miavia.ai",'
echo '    "password": "wozWi9-matvah-xonmyq",'
echo '    "vin": "'$VIN'",'
echo '    "s_pin": "2405",'
echo '    "action": "lock"'
echo "  }'"