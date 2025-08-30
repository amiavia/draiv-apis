# BMW API Stateless - Cloud Function

## Overview

This is a **completely stateless** implementation of the BMW Connected Drive API designed for maximum security and simplicity. Unlike the standard version, this implementation:

- **Never stores OAuth tokens** (no GCS, no local storage)
- **Requires hCaptcha verification for EVERY request**
- **Performs fresh authentication on each API call**
- **Has zero persistence layer**

## Key Features

- 🔐 **Enhanced Security**: No token storage means no token leakage risk
- 🚀 **Simple Deployment**: No storage buckets or databases needed
- 🌍 **Global Scale**: Completely stateless, scales infinitely
- ⚡ **Low Latency**: Optimized for quick response times
- 🛡️ **CORS Enabled**: Ready for browser-based applications

## API Endpoints

### Base URL
```
https://us-central1-[PROJECT_ID].cloudfunctions.net/bmw_api_stateless
```

### CORS Preflight
```http
OPTIONS /
```
Returns: `204 No Content` with CORS headers

### Main Endpoint
```http
POST /
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "user_password",
  "wkn": "vehicle_wkn",
  "hcaptcha": "hcaptcha_token_from_client",
  "action": "lock"
}
```

## Available Actions

| Action | Description | Response Time |
|--------|-------------|---------------|
| `lock` | Lock vehicle doors | ~5-90s |
| `unlock` | Unlock vehicle doors | ~5-90s |
| `flash` | Flash vehicle lights | ~3-10s |
| `ac` | Start air conditioning | ~5-15s |
| `fuel` | Get fuel/battery status | ~1-3s |
| `location` | Get vehicle GPS location | ~1-3s |
| `mileage` | Get current mileage | ~1-3s |
| `lock_status` | Get detailed lock state | ~1-3s |
| `is_locked` | Check if vehicle is locked | ~1-3s |
| `check_control` | Get check control messages | ~1-3s |

## Response Format

### Success Response
```json
{
  "brand": "BMW",
  "vehicle_name": "330i",
  "vin": "WBA...",
  "wkn": "ABC123",
  "model": "3 Series",
  "action_result": {
    "status": "completed",
    "message": "Door lock command sent successfully"
  },
  "authentication_method": "stateless_hcaptcha"
}
```

### Error Response
```json
{
  "error": "Authentication failed",
  "details": "Invalid credentials or hCaptcha token",
  "hint": "Ensure email, password, and valid hCaptcha token are provided"
}
```

## Deployment

### Prerequisites

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and configured
3. **Service Account** with Cloud Functions Admin role

### Quick Deploy

```bash
# Clone the repository
git clone https://github.com/draiv/draiv-apis.git
cd draiv-apis/apis/bmw

# Deploy to Google Cloud
./deploy_stateless.sh

# For production deployment
./deploy_stateless.sh --production
```

### Manual Deployment

```bash
# Deploy the function
gcloud functions deploy bmw_api_stateless \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point bmw_api \
  --source src/ \
  --region us-central1 \
  --memory 256MB \
  --timeout 90s \
  --max-instances 100 \
  --gen2
```

## Local Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-stateless.txt
```

### Run Locally

```bash
# Using functions-framework
functions-framework --target=bmw_api --port=8080

# Or directly with Python
python src/main_stateless.py
```

### Test Locally

```bash
# Test CORS preflight
curl -X OPTIONS http://localhost:8080

# Test with sample request (you'll need valid credentials and hCaptcha token)
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "wkn": "TEST123",
    "hcaptcha": "test-token",
    "action": "lock"
  }'
```

## hCaptcha Integration

### Frontend Implementation

```javascript
// Include hCaptcha script
<script src="https://js.hcaptcha.com/1/api.js" async defer></script>

// Add hCaptcha widget
<div class="h-captcha" 
     data-sitekey="YOUR_SITE_KEY"
     data-callback="onHCaptchaSuccess">
</div>

// Handle hCaptcha response
function onHCaptchaSuccess(token) {
  // Use token in API request
  fetch('https://your-function-url', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: 'user@example.com',
      password: 'password',
      wkn: 'vehicle_wkn',
      hcaptcha: token,
      action: 'lock'
    })
  });
}
```

## Security Considerations

1. **No Token Storage**: This implementation never stores OAuth tokens
2. **Fresh Authentication**: Every request performs fresh BMW authentication
3. **hCaptcha Required**: Protects against automated attacks
4. **HTTPS Only**: Always use HTTPS in production
5. **Rate Limiting**: Consider implementing rate limiting at the API Gateway level
6. **Input Validation**: All inputs are validated before processing

## Monitoring

### View Logs

```bash
# View recent logs
gcloud functions logs read bmw_api_stateless --limit=50

# Stream logs in real-time
gcloud functions logs read bmw_api_stateless --follow
```

### Metrics

Monitor in Google Cloud Console:
- Invocations
- Execution time
- Memory usage
- Error rate

## Cost Estimation

Based on Google Cloud Functions pricing (as of 2025):

| Metric | Free Tier | Price After Free Tier |
|--------|-----------|----------------------|
| Invocations | 2M/month | $0.40 per million |
| Compute Time | 400,000 GB-seconds | $0.0000025 per GB-second |
| Memory | 200,000 GB-seconds | $0.0000100 per GB-second |

**Estimated cost for 100,000 requests/month**: ~$5-10

## Troubleshooting

### Common Issues

1. **"Missing required fields" error**
   - Ensure all required fields are provided: email, password, wkn, hcaptcha

2. **"Authentication failed" error**
   - Verify BMW credentials are correct
   - Ensure hCaptcha token is valid and fresh (tokens expire quickly)

3. **CORS errors in browser**
   - Function is configured for CORS, check browser console for specific error
   - Ensure you're using the correct HTTP method (POST)

4. **Timeout errors**
   - Some vehicle operations (lock/unlock) can take up to 90 seconds
   - Consider implementing async patterns in your frontend

## Comparison with Stateful Version

| Feature | Stateless | Stateful |
|---------|-----------|----------|
| Token Storage | ❌ None | ✅ GCS Bucket |
| hCaptcha per request | ✅ Required | ❌ Optional |
| Setup Complexity | Low | Medium |
| Response Time | ~2-3s slower | Faster |
| Security | Higher | Standard |
| Cost | Lower | Higher |
| Scalability | Infinite | High |

## Support

For issues or questions:
1. Check the [troubleshooting section](#troubleshooting)
2. Review [Google Cloud Functions docs](https://cloud.google.com/functions/docs)
3. Open an issue in the repository

## License

Copyright 2025 DRAIV. All rights reserved.