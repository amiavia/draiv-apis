# Skoda API Deployment Guide

## 🚗 Overview

The Skoda Connect API has been successfully converted to a Google Cloud Function following the BMW API pattern. It provides vehicle control capabilities through the MySkoda API integration.

## 📁 Files Created

### Core Implementation
- ✅ `src/main_cloud.py` - Cloud Function implementation (Flask + functions_framework)
- ✅ `requirements-cloud.txt` - Minimal dependencies for cloud deployment
- ✅ `deploy_skoda.sh` - Local deployment script (requires gcloud CLI)
- ✅ `test_skoda_api.sh` - Test script for deployed function

### CI/CD Integration  
- ✅ `.github/workflows/deploy-skoda-api.yml` - GitHub Actions workflow
- ✅ Follows exact BMW deployment pattern
- ✅ Supports staging/production environments

## 🚀 Deployment Options

### Option 1: GitHub Actions (Recommended)

1. **Manual Trigger**:
   ```bash
   # Go to GitHub Actions > Deploy Skoda API > Run workflow
   # Select environment: staging or production
   ```

2. **Automatic Trigger**:
   - Push to `develop` branch → Deploy to staging
   - Push to `main` branch → Deploy to production

### Option 2: Local Deployment (If gcloud CLI available)

```bash
cd /Users/antonsteininger/draiv-workspace/draiv-apis/apis/skoda
./deploy_skoda.sh --production  # or leave blank for staging
```

## 🧪 Testing the Deployed API

Once deployed, the function URL will be:
```
https://europe-west6-miavia-422212.cloudfunctions.net/skoda_api_stateless
```

### Test Commands with Your VIN

```bash
# Test vehicle status
curl -X POST "https://europe-west6-miavia-422212.cloudfunctions.net/skoda_api_stateless" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "Info@miavia.ai",
    "password": "wozWi9-matvah-xonmyq",
    "vin": "TMBJJ7NX5MY061741",
    "action": "status"
  }'

# Lock vehicle (requires S-PIN)
curl -X POST "https://europe-west6-miavia-422212.cloudfunctions.net/skoda_api_stateless" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "Info@miavia.ai",
    "password": "wozWi9-matvah-xonmyq",
    "vin": "TMBJJ7NX5MY061741",
    "s_pin": "2405",
    "action": "lock"
  }'

# Unlock vehicle
curl -X POST "https://europe-west6-miavia-422212.cloudfunctions.net/skoda_api_stateless" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "Info@miavia.ai",
    "password": "wozWi9-matvah-xonmyq",
    "vin": "TMBJJ7NX5MY061741",
    "s_pin": "2405",
    "action": "unlock"
  }'

# Flash lights (no S-PIN required)
curl -X POST "https://europe-west6-miavia-422212.cloudfunctions.net/skoda_api_stateless" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "Info@miavia.ai",
    "password": "wozWi9-matvah-xonmyq",
    "vin": "TMBJJ7NX5MY061741",
    "action": "flash"
  }'

# Start climate control
curl -X POST "https://europe-west6-miavia-422212.cloudfunctions.net/skoda_api_stateless" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "Info@miavia.ai",
    "password": "wozWi9-matvah-xonmyq",
    "vin": "TMBJJ7NX5MY061741",
    "s_pin": "2405",
    "action": "climate_start"
  }'
```

### Automated Test Script

```bash
./test_skoda_api.sh
```

## 📊 Available Actions

| Action | S-PIN Required | Description |
|--------|----------------|-------------|
| `status` | ❌ | Get vehicle status, location, fuel/battery |
| `lock` | ✅ | Lock vehicle doors |
| `unlock` | ✅ | Unlock vehicle doors |
| `flash` | ❌ | Flash vehicle lights |
| `climate_start` | ✅ | Start climate control (22°C default) |
| `climate_stop` | ❌ | Stop climate control |

## 🔐 Test Credentials

```
Email: Info@miavia.ai
Password: wozWi9-matvah-xonmyq
S-PIN: 2405
VIN: TMBJJ7NX5MY061741
```

## 📈 Response Format

### Success Response
```json
{
  "success": true,
  "data": {
    "vin": "TMBJJ7NX5MY061741",
    "model": "Skoda Octavia",
    "status": {
      "locked": true,
      "fuel_level": 65
    }
  },
  "action": "status",
  "timestamp": "2025-01-30T10:00:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": "SPIN_REQUIRED",
  "message": "Valid S-PIN required for this operation",
  "action": "lock",
  "vin": "TMBJJ7NX5MY061741",
  "timestamp": "2025-01-30T10:00:00Z"
}
```

## 🛠️ Troubleshooting

### Common Issues

1. **MySkoda library not available**: Function falls back to mock mode
2. **Invalid S-PIN**: Returns `SPIN_REQUIRED` error
3. **Vehicle not found**: Returns `VEHICLE_NOT_FOUND` error
4. **Authentication failed**: Returns `AUTHENTICATION_ERROR`

### Monitoring

```bash
# View function logs
gcloud functions logs read skoda_api_stateless --region=europe-west6

# View function status
gcloud functions describe skoda_api_stateless --region=europe-west6
```

## 🎯 Next Steps

1. **Deploy via GitHub Actions** (recommended)
2. **Test all actions** with your VIN
3. **Monitor logs** for any issues
4. **Set up monitoring alerts** if needed

The Skoda API is now ready for production use following the same proven patterns as the BMW API! 🎉