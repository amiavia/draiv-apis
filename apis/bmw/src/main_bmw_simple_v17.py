"""
BMW API using bimmer_connected 0.17.3 with built-in fingerprint fix
Clean implementation without manual patching needed
"""
import os
import json
import asyncio
from pathlib import Path
from google.cloud import storage
from flask import request, jsonify
import functions_framework
from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import Regions
from bimmer_connected.cli import load_oauth_store_from_file, store_oauth_store_to_file
from bimmer_connected.vehicle.remote_services import RemoteServices

# Configuration
BUCKET_NAME = "bmw-api-bucket"
OAUTH_FILENAME = "bmw_oauth.json"
LOCAL_TOKEN_FILE = "/tmp/bmw_oauth.json"

def download_oauth_file():
    """Download OAuth token from GCS"""
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(OAUTH_FILENAME)
        
        if blob.exists():
            blob.download_to_filename(LOCAL_TOKEN_FILE)
            print("✅ OAuth token downloaded from GCS")
            return True
    except Exception as e:
        print(f"⚠️ Could not download OAuth token: {e}")
    return False

def upload_oauth_file():
    """Upload OAuth token to GCS"""
    try:
        if os.path.exists(LOCAL_TOKEN_FILE):
            client = storage.Client()
            bucket = client.bucket(BUCKET_NAME)
            blob = bucket.blob(OAUTH_FILENAME)
            blob.upload_from_filename(LOCAL_TOKEN_FILE)
            print("✅ OAuth token uploaded to GCS")
    except Exception as e:
        print(f"⚠️ Could not upload OAuth token: {e}")

@functions_framework.http
def bmw_api(request):
    """
    BMW API Cloud Function - v0.17.3 with built-in fingerprint fix
    """
    # Handle CORS
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return ("", 204, headers)
    
    # Health check endpoint
    if request.method == "GET" and request.path == "/health":
        return jsonify({
            "status": "healthy",
            "service": "bmw-api",
            "version": "0.17.3",
            "library": "bimmer_connected",
            "features": {
                "fingerprint": "built-in PR #743",
                "quota_fix": "enabled"
            }
        }), 200, {"Access-Control-Allow-Origin": "*"}
    
    # Parse request
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request must be JSON"}), 400
            
        # Required fields
        email = data.get("email")
        password = data.get("password")
        wkn = data.get("wkn")
        
        if not all([email, password, wkn]):
            return jsonify({
                "error": "Missing required fields",
                "required": ["email", "password", "wkn"]
            }), 400
            
    except Exception as e:
        return jsonify({"error": f"Invalid request: {str(e)}"}), 400
    
    # Optional fields
    action = data.get("action", "status")
    hcaptcha_token = data.get("hcaptcha")
    
    print(f"📋 Processing BMW API request: action={action}, vehicle={wkn}")
    
    try:
        # Check for existing OAuth token
        has_token = download_oauth_file()
        
        # Create account instance
        print(f"🔐 Authenticating as {email}...")
        account = MyBMWAccount(email, password, Regions.REST_OF_WORLD)
        
        # Load existing token if available
        if has_token:
            print("📂 Using stored OAuth token")
            load_oauth_store_from_file(Path(LOCAL_TOKEN_FILE), account)
        elif not hcaptcha_token:
            # For first auth, hCaptcha might be needed
            print("⚠️ First authentication may require hCaptcha token")
        
        # Get vehicles (this triggers authentication)
        print("🚗 Fetching vehicles...")
        asyncio.run(account.get_vehicles())
        
        # Find target vehicle
        vehicle = account.get_vehicle(wkn)
        if not vehicle:
            return jsonify({
                "error": f"Vehicle {wkn} not found",
                "available_vehicles": [v.vin for v in account.vehicles]
            }), 404
        
        # Store updated OAuth token
        store_oauth_store_to_file(Path(LOCAL_TOKEN_FILE), account)
        upload_oauth_file()
        
        # Build base response
        response = {
            "success": True,
            "vehicle": {
                "brand": vehicle.brand,
                "name": vehicle.name,
                "vin": vehicle.vin,
                "model": getattr(vehicle, "model", "Unknown")
            },
            "action": action
        }
        
        # Process actions
        if action == "status":
            # Get comprehensive status
            response["result"] = {
                "doors_locked": vehicle.doors_windows.lock_state.value if hasattr(vehicle, "doors_windows") else None,
                "mileage": {
                    "value": vehicle.mileage.value if hasattr(vehicle.mileage, "value") else vehicle.mileage,
                    "unit": vehicle.mileage.unit if hasattr(vehicle.mileage, "unit") else "km"
                },
                "fuel": {
                    "remaining_percent": vehicle.fuel_and_battery.remaining_fuel_percent if hasattr(vehicle, "fuel_and_battery") else None,
                    "remaining_range": vehicle.fuel_and_battery.remaining_range_total if hasattr(vehicle, "fuel_and_battery") else None
                },
                "location": {
                    "latitude": vehicle.location.location.latitude if hasattr(vehicle, "location") and vehicle.location and vehicle.location.location else None,
                    "longitude": vehicle.location.location.longitude if hasattr(vehicle, "location") and vehicle.location and vehicle.location.location else None
                }
            }
            
        elif action == "lock":
            print("🔒 Sending lock command...")
            remote_services = RemoteServices(vehicle)
            result = asyncio.run(remote_services.trigger_remote_door_lock())
            response["result"] = {
                "command": "lock",
                "status": "initiated",
                "message": "Lock command sent successfully"
            }
            
        elif action == "unlock":
            print("🔓 Sending unlock command...")
            remote_services = RemoteServices(vehicle)
            result = asyncio.run(remote_services.trigger_remote_door_unlock())
            response["result"] = {
                "command": "unlock",
                "status": "initiated",
                "message": "Unlock command sent successfully"
            }
            
        elif action == "flash":
            print("💡 Sending flash lights command...")
            remote_services = RemoteServices(vehicle)
            result = asyncio.run(remote_services.trigger_remote_light_flash())
            response["result"] = {
                "command": "flash",
                "status": "initiated",
                "message": "Flash lights command sent successfully"
            }
            
        elif action == "climate":
            print("❄️ Sending climate control command...")
            remote_services = RemoteServices(vehicle)
            result = asyncio.run(remote_services.trigger_remote_air_conditioning())
            response["result"] = {
                "command": "climate",
                "status": "initiated",
                "message": "Climate control command sent successfully"
            }
            
        elif action == "location":
            location = vehicle.location
            if location and location.location:
                response["result"] = {
                    "latitude": location.location.latitude,
                    "longitude": location.location.longitude,
                    "heading": location.heading,
                    "timestamp": location.vehicle_update_timestamp.isoformat() if location.vehicle_update_timestamp else None
                }
            else:
                response["result"] = {"error": "Location not available"}
                
        elif action == "fuel":
            fuel = vehicle.fuel_and_battery
            if fuel:
                response["result"] = {
                    "remaining_fuel": fuel.remaining_fuel,
                    "remaining_fuel_percent": fuel.remaining_fuel_percent,
                    "remaining_range_fuel": fuel.remaining_range_fuel,
                    "remaining_range_electric": fuel.remaining_range_electric,
                    "remaining_range_total": fuel.remaining_range_total
                }
            else:
                response["result"] = {"error": "Fuel data not available"}
                
        else:
            response["result"] = {"error": f"Unknown action: {action}"}
        
        # Return successful response
        return jsonify(response), 200, {"Access-Control-Allow-Origin": "*"}
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")
        
        # Determine error type and response
        if "unauthorized" in error_msg.lower() or "401" in error_msg:
            return jsonify({
                "error": "Authentication failed",
                "message": "Invalid credentials or expired token",
                "hint": "Check email/password or provide hCaptcha token"
            }), 401
        elif "429" in error_msg or "quota" in error_msg.lower():
            return jsonify({
                "error": "Rate limited",
                "message": "BMW API quota exceeded",
                "hint": "This should be less likely with v0.17.3"
            }), 429
        else:
            return jsonify({
                "error": "Request failed",
                "message": error_msg,
                "service": "bmw-api-v0.17.3"
            }), 500