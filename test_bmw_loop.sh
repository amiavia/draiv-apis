#!/bin/bash

# BMW API Testing Loop
# This script tests the BMW API with a provided hCaptcha token

if [ $# -eq 0 ]; then
    echo "Usage: $0 <hcaptcha_token>"
    echo "Get token from: https://bimmer-connected.readthedocs.io/en/stable/captcha/rest_of_world.html"
    exit 1
fi

HCAPTCHA_TOKEN="$1"
BMW_API_URL="https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless"

echo "🧪 Testing BMW API with fresh hCaptcha token..."
echo "🔗 Token (first 50 chars): ${HCAPTCHA_TOKEN:0:50}..."

# Test the API
RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"Info@miavia.ai\",
    \"password\": \"qegbe6-ritdoz-vikDeK\",
    \"wkn\": \"WBA3K51040K175114\",
    \"hcaptcha\": \"$HCAPTCHA_TOKEN\"
  }" \
  "$BMW_API_URL")

echo "📡 BMW API Response:"
echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"

# Check if authentication was successful
if echo "$RESPONSE" | grep -q '"success": true'; then
    echo "✅ SUCCESS! BMW authentication working!"
    exit 0
else
    echo "❌ Authentication failed. Analyzing error..."
    # Extract error details for analysis
    echo "$RESPONSE" | jq '.bmw_raw_error // .error // .details' 2>/dev/null
    exit 1
fi