# GCP Deployment Commands for BMW API Stateless

Copy and paste these commands into your Google Cloud Console (Cloud Shell) or local terminal.

## 🚀 Quick Deploy (Copy All & Run)

```bash
# ============================================
# COMPLETE DEPLOYMENT SCRIPT - COPY ALL BELOW
# ============================================

# 1. Set your project ID
export PROJECT_ID="miavia-422212"
export FUNCTION_NAME="bmw_api_stateless"
export REGION="us-central1"

# 2. Set the project
gcloud config set project $PROJECT_ID

# 3. Enable required APIs
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# 4. Create deployment directory
mkdir -p /tmp/bmw-deploy
cd /tmp/bmw-deploy

# 5. Create main.py (the stateless implementation)
cat > main.py << 'PYTHON_EOF'
"""
BMW API Stateless Cloud Function
"""

import asyncio
from flask import Flask, request, jsonify
import functions_framework
from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import Regions
from bimmer_connected.vehicle.remote_services import RemoteServices, Services

app = Flask(__name__)

@functions_framework.http
def bmw_api(request):
    """
    Stateless Cloud Function for BMW Connected Drive API.
    """
    
    # Handle CORS (Preflight Requests)
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return ("", 204, headers)

    # Parse and validate ALL required fields (including hCaptcha)
    try:
        data = request.get_json()
        
        # Validate all required fields are present
        required_fields = ["email", "password", "wkn", "hcaptcha"]
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "required": required_fields
            }), 400
            
    except Exception as e:
        return jsonify({
            "error": "Invalid JSON format",
            "details": str(e)
        }), 400

    # Extract request parameters
    provided_email = data["email"]
    provided_password = data["password"]
    wkn = data["wkn"]
    hcaptcha_token = data["hcaptcha"]
    action = data.get("action", "default")

    # ALWAYS authenticate fresh with hCaptcha (no token storage/reuse)
    print(f"Stateless authentication for {provided_email} with hCaptcha...")
    
    try:
        # Create new account instance with hCaptcha for fresh authentication
        account = MyBMWAccount(
            provided_email, 
            provided_password, 
            Regions.REST_OF_WORLD, 
            hcaptcha_token=hcaptcha_token
        )
        
        # Fetch vehicles from BMW servers
        print("Fetching vehicle data...")
        asyncio.run(account.get_vehicles())
        
        # Get specific vehicle by WKN
        vehicle = account.get_vehicle(wkn)
        
        if not vehicle:
            return jsonify({
                "error": f"Vehicle with WKN '{wkn}' not found",
                "available_vehicles": [v.wkn for v in account.vehicles]
            }), 404
        
        # Initialize RemoteServices for remote commands
        remote_services = RemoteServices(vehicle)

        # Build base response with vehicle information
        response_data = {
            "brand": vehicle.brand,
            "vehicle_name": vehicle.name,
            "vin": vehicle.vin,
            "wkn": vehicle.wkn,
            "model": getattr(vehicle, "model", "Unknown"),
        }

        # Initialize action result
        action_result = None

        # Handle Remote Actions Based on Request
        
        if action == "lock":
            print("Executing remote door lock...")
            try:
                result = asyncio.run(
                    asyncio.wait_for(
                        remote_services.trigger_remote_door_lock(), 
                        timeout=90
                    )
                )
                action_result = {
                    "status": result.state.value if result and hasattr(result, "state") else "Unknown",
                    "message": "Door lock command sent successfully"
                }
            except asyncio.TimeoutError:
                action_result = {
                    "status": "timeout",
                    "message": "Locking operation timed out after 90 seconds"
                }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"Lock operation failed: {str(e)}"
                }
                
        elif action == "unlock":
            print("Executing remote door unlock...")
            try:
                result = asyncio.run(
                    asyncio.wait_for(
                        remote_services.trigger_remote_door_unlock(), 
                        timeout=90
                    )
                )
                action_result = {
                    "status": result.state.value if result and hasattr(result, "state") else "Unknown",
                    "message": "Door unlock command sent successfully"
                }
            except asyncio.TimeoutError:
                action_result = {
                    "status": "timeout",
                    "message": "Unlocking operation timed out after 90 seconds"
                }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"Unlock operation failed: {str(e)}"
                }
                
        elif action == "flash":
            print("Executing remote light flash...")
            try:
                result = asyncio.run(remote_services.trigger_remote_light_flash())
                action_result = {
                    "status": result.state.value if result and hasattr(result, "state") else "Unknown",
                    "message": "Light flash command sent successfully"
                }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"Flash operation failed: {str(e)}"
                }
            
        elif action == "fuel":
            print("Retrieving fuel and battery information...")
            try:
                fuel_and_battery = vehicle.fuel_and_battery
                action_result = {
                    "remaining_fuel": getattr(fuel_and_battery, "remaining_fuel", None),
                    "remaining_fuel_percent": getattr(fuel_and_battery, "remaining_fuel_percent", None),
                    "remaining_range_fuel": getattr(fuel_and_battery, "remaining_range_fuel", None),
                    "remaining_range_electric": getattr(fuel_and_battery, "remaining_range_electric", None),
                    "remaining_range_total": getattr(fuel_and_battery, "remaining_range_total", None),
                }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"Failed to retrieve fuel data: {str(e)}"
                }
            
        elif action == "location":
            print("Retrieving vehicle location...")
            try:
                location = vehicle.location
                if location and location.location:
                    action_result = {
                        "latitude": location.location.latitude,
                        "longitude": location.location.longitude,
                        "heading": getattr(location, "heading", None),
                        "timestamp": location.vehicle_update_timestamp.isoformat() if hasattr(location, "vehicle_update_timestamp") and location.vehicle_update_timestamp else None,
                    }
                else:
                    action_result = {
                        "status": "unavailable",
                        "message": "Location data not available"
                    }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"Failed to retrieve location: {str(e)}"
                }
            
        elif action == "mileage":
            print("Retrieving mileage information...")
            try:
                mileage = vehicle.mileage
                action_result = {
                    "value": mileage.value if hasattr(mileage, "value") else mileage,
                    "unit": mileage.unit if hasattr(mileage, "unit") else "km"
                }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"Failed to retrieve mileage: {str(e)}"
                }
            
        elif action == "lock_status":
            print("Retrieving detailed door lock status...")
            try:
                if hasattr(vehicle, "doors_windows") and vehicle.doors_windows:
                    lock_state = vehicle.doors_windows.lock_state
                    action_result = {
                        "lock_state": lock_state.value if lock_state and hasattr(lock_state, "value") else "Unknown",
                        "message": "Lock status retrieved successfully"
                    }
                else:
                    action_result = {
                        "status": "unavailable",
                        "message": "Lock status not available"
                    }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"Failed to retrieve lock status: {str(e)}"
                }
            
        elif action == "is_locked":
            print("Checking if vehicle is locked...")
            try:
                if hasattr(vehicle, "doors_windows") and vehicle.doors_windows:
                    lock_state = vehicle.doors_windows.lock_state
                    if lock_state and hasattr(lock_state, "value"):
                        if lock_state.value == "LOCKED":
                            action_result = {
                                "is_locked": True,
                                "state": "locked",
                                "message": "Vehicle is locked"
                            }
                        elif lock_state.value == "UNLOCKED":
                            action_result = {
                                "is_locked": False,
                                "state": "unlocked",
                                "message": "Vehicle is unlocked"
                            }
                        else:
                            action_result = {
                                "is_locked": None,
                                "state": lock_state.value,
                                "message": f"Vehicle in intermediate state: {lock_state.value}"
                            }
                    else:
                        action_result = {
                            "status": "unknown",
                            "message": "Unable to determine lock state"
                        }
                else:
                    action_result = {
                        "status": "unavailable",
                        "message": "Lock state information not available"
                    }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"Failed to check lock state: {str(e)}"
                }
                
        else:
            print(f"No specific action requested or unknown action: {action}")
            action_result = {
                "status": "info",
                "message": "No valid action specified. Vehicle details returned.",
                "available_actions": [
                    "lock", "unlock", "flash", "fuel", 
                    "location", "mileage", "lock_status", "is_locked"
                ]
            }

        # Add action result to response
        response_data["action_result"] = action_result
        response_data["authentication_method"] = "stateless_hcaptcha"

        # Set CORS headers for response
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        }
        
        return (jsonify(response_data), 200, headers)

    except Exception as e:
        # Handle authentication or other errors
        error_message = str(e)
        
        # Check for specific error types
        if "authentication" in error_message.lower():
            return jsonify({
                "error": "Authentication failed",
                "details": error_message,
                "hint": "Ensure email, password, and valid hCaptcha token are provided"
            }), 401
        elif "vehicle" in error_message.lower():
            return jsonify({
                "error": "Vehicle operation failed",
                "details": error_message
            }), 500
        else:
            return jsonify({
                "error": "Request processing failed",
                "details": error_message,
                "authentication_method": "stateless_hcaptcha"
            }), 500


# For local testing only
if __name__ == "__main__":
    app.run(debug=True, port=8080)
PYTHON_EOF

# 6. Create requirements.txt
cat > requirements.txt << 'REQ_EOF'
bimmer-connected==0.16.4
flask==3.0.3
functions-framework==3.8.2
aiohttp==3.10.10
REQ_EOF

# 7. Deploy the function
echo "Deploying BMW API Stateless to Google Cloud Functions..."
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=bmw_api \
    --trigger-http \
    --allow-unauthenticated \
    --memory=256MB \
    --timeout=90s \
    --max-instances=100 \
    --set-env-vars="ENVIRONMENT=production"

# 8. Get the function URL
echo ""
echo "Getting function URL..."
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME \
    --region=$REGION \
    --gen2 \
    --format="value(serviceConfig.uri)")

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "=========================================="
echo ""
echo "Function URL: $FUNCTION_URL"
echo ""
echo "Test CORS with:"
echo "curl -X OPTIONS $FUNCTION_URL"
echo ""
echo "View logs with:"
echo "gcloud functions logs read $FUNCTION_NAME --region=$REGION"
echo ""

# ============================================
# END OF DEPLOYMENT SCRIPT
# ============================================
```

## 🔧 Alternative: Step-by-Step Commands

If you prefer to run commands one by one:

### Step 1: Setup Project
```bash
gcloud config set project miavia-422212
```

### Step 2: Enable APIs
```bash
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### Step 3: Deploy Function Directly from GitHub
```bash
# If your code is in GitHub, deploy directly:
gcloud functions deploy bmw_api_stateless \
    --gen2 \
    --runtime=python311 \
    --region=us-central1 \
    --source=https://github.com/draiv/draiv-apis/apis/bmw/src \
    --entry-point=bmw_api \
    --trigger-http \
    --allow-unauthenticated \
    --memory=256MB \
    --timeout=90s
```

## 🔐 Authentication Setup Commands

### Create Service Account (Optional)
```bash
# Create service account for CI/CD
gcloud iam service-accounts create bmw-api-deployer \
    --display-name="BMW API Cloud Function Deployer"

# Grant permissions
gcloud projects add-iam-policy-binding miavia-422212 \
    --member="serviceAccount:bmw-api-deployer@miavia-422212.iam.gserviceaccount.com" \
    --role="roles/cloudfunctions.developer"

# Create key (for GitHub Actions)
gcloud iam service-accounts keys create ~/bmw-api-sa-key.json \
    --iam-account=bmw-api-deployer@miavia-422212.iam.gserviceaccount.com
```

## 📊 Monitoring Commands

### View Logs
```bash
# Stream logs
gcloud functions logs read bmw_api_stateless \
    --region=us-central1 \
    --limit=50

# Follow logs in real-time
gcloud functions logs read bmw_api_stateless \
    --region=us-central1 \
    --follow
```

### Check Function Status
```bash
# Describe function
gcloud functions describe bmw_api_stateless \
    --region=us-central1

# List all functions
gcloud functions list --regions=us-central1
```

## 🧪 Testing Commands

### Test CORS
```bash
# Get function URL
FUNCTION_URL=$(gcloud functions describe bmw_api_stateless \
    --region=us-central1 \
    --gen2 \
    --format="value(serviceConfig.uri)")

# Test CORS preflight
curl -X OPTIONS $FUNCTION_URL -v
```

### Test with Sample Request
```bash
curl -X POST $FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password",
    "wkn": "TEST123",
    "hcaptcha": "test-token",
    "action": "fuel"
  }'
```

## 🗑️ Cleanup Commands

### Delete Function
```bash
gcloud functions delete bmw_api_stateless \
    --region=us-central1 \
    --quiet
```

### Delete Service Account
```bash
gcloud iam service-accounts delete \
    bmw-api-deployer@miavia-422212.iam.gserviceaccount.com \
    --quiet
```

## 🚨 Troubleshooting Commands

### Check Deployment Errors
```bash
# View build logs
gcloud builds list --limit=5

# View specific build
gcloud builds describe [BUILD_ID]

# Check function errors
gcloud functions logs read bmw_api_stateless \
    --region=us-central1 \
    --filter="severity>=ERROR" \
    --limit=20
```

### Update Function
```bash
# Update environment variables
gcloud functions deploy bmw_api_stateless \
    --update-env-vars KEY=VALUE \
    --region=us-central1

# Update memory/timeout
gcloud functions deploy bmw_api_stateless \
    --memory=512MB \
    --timeout=120s \
    --region=us-central1
```

## 💡 Tips

1. **First Time Setup**: Run the complete script at the top
2. **Updates**: Use the update commands to modify existing function
3. **Monitoring**: Keep logs open in another terminal while testing
4. **Costs**: Monitor usage in GCP Console > Billing

---

**Note**: Replace `miavia-422212` with your actual GCP project ID if different.