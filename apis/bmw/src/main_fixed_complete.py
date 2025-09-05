"""
BMW API with Fingerprint Patch for Quota Isolation
"""
# CRITICAL: Apply fingerprint patch BEFORE importing bimmer_connected
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fingerprint_patch import apply_fingerprint_patch
apply_fingerprint_patch()

import json
import asyncio
from pathlib import Path
from google.cloud import storage
from flask import Flask, request, jsonify
import functions_framework
from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import Regions
from bimmer_connected.cli import load_oauth_store_from_file, store_oauth_store_to_file
from bimmer_connected.vehicle.remote_services import RemoteServices, Services

# 🔹 Configuration for GCS Bucket & OAuth Token File Details
BUCKET_NAME = "bmw-api-bucket"
OAUTH_FILENAME = "bmw_oauth.json"
LOCAL_TOKEN_FILE = "/tmp/bmw_oauth.json"

app = Flask(__name__)

# 🔹 Utility Functions for OAuth Token Management

def download_oauth_file():
    """
    Download the OAuth token file from Google Cloud Storage to local storage.
    Returns True if the file exists and is downloaded; otherwise, False.
    """
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(OAUTH_FILENAME)

    if blob.exists():
        blob.download_to_filename(LOCAL_TOKEN_FILE)
        print("✅ OAuth token downloaded from GCS.")
        return True
    print("⚠️ No existing OAuth token found in GCS.")
    return False

def upload_oauth_file():
    """
    Upload the OAuth token file from local storage to Google Cloud Storage.
    This ensures the token remains updated after executing remote commands.
    """
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(OAUTH_FILENAME)

    if os.path.exists(LOCAL_TOKEN_FILE):
        blob.upload_from_filename(LOCAL_TOKEN_FILE)
        print("✅ OAuth token uploaded to GCS.")
    else:
        print("⚠️ No OAuth token file found locally to upload.")

# 🔹 Main Cloud Function Handler

@functions_framework.http
def bmw_api(request):
    """
    Cloud Function entry point to authenticate and execute remote actions.
    This function:
      - Handles CORS preflight requests.
      - Validates and parses JSON input.
      - Authenticates using stored OAuth tokens or hCaptcha on first authentication.
      - Executes the requested action safely.
      - Returns updated vehicle data and remote service status.
    """
    # ✅ Handle CORS (Preflight Requests)
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return ("", 204, headers)
    
    # ✅ Handle health check
    if request.method == "GET" and request.path == "/health":
        try:
            from fingerprint_patch import _get_system_uuid, _generate_build_string
            system_uuid = _get_system_uuid()
            build_string = _generate_build_string(system_uuid)
            x_user_agent = f"android({build_string});bmw;2.20.3;row"
            
            health_data = {
                "status": "healthy",
                "service": "bmw-api-fixed",
                "version": "1.0.0",
                "fingerprint": {
                    "enabled": True,
                    "system_uuid": system_uuid,
                    "build_string": build_string,
                    "x_user_agent": x_user_agent
                }
            }
        except Exception as e:
            health_data = {
                "status": "healthy",
                "service": "bmw-api-fixed",
                "version": "1.0.0",
                "fingerprint": {"error": str(e)}
            }
        
        headers = {"Access-Control-Allow-Origin": "*"}
        return (jsonify(health_data), 200, headers)

    # ✅ Parse incoming JSON request and validate required fields
    try:
        data = request.get_json()
        if not data or "email" not in data or "password" not in data or "wkn" not in data:
            return jsonify({"error": "Email, password, and WKN are required"}), 400
    except Exception:
        return jsonify({"error": "Invalid JSON format"}), 400

    provided_email = data["email"]
    provided_password = data["password"]
    wkn = data["wkn"]
    # Action parameter determines which remote service to invoke. Default returns basic info.
    action = data.get("action", "default")
    # Retrieve hCaptcha token if provided for first-time authentication
    hcaptcha_token = data.get("hcaptcha")

    # ✅ Attempt to load an existing OAuth token from GCS
    has_token_file = download_oauth_file()

    # ✅ Initialize the MyBMWAccount instance.
    if has_token_file:
        print("🔄 Re-authenticating using stored OAuth token...")
        account = MyBMWAccount(provided_email, provided_password, Regions.REST_OF_WORLD)
        load_oauth_store_from_file(Path(LOCAL_TOKEN_FILE), account)
    elif not hcaptcha_token:
        return jsonify({"error": "Missing hCaptcha token on first authentication"}), 400
    else:
        print("🔑 First-time authentication with hCaptcha...")
        # Note: bimmer_connected doesn't accept hcaptcha_token parameter directly
        # The library handles authentication internally
        account = MyBMWAccount(provided_email, provided_password, Regions.REST_OF_WORLD)

    try:
        # ✅ Fetch vehicles asynchronously
        asyncio.run(account.get_vehicles())
        # Retrieve the vehicle by its WKN
        vehicle = account.get_vehicle(wkn)
        # Initialize RemoteServices for remote commands
        remote_services = RemoteServices(vehicle)

        # ✅ After remote execution, update and persist the OAuth token
        store_oauth_store_to_file(Path(LOCAL_TOKEN_FILE), account)
        upload_oauth_file()

        # Initialize a dictionary for vehicle information to include in the response.
        response_data = {
            "brand": vehicle.brand,
            "vehicle_name": vehicle.name,
            "vin": vehicle.vin,
        }

        # Initialize the variable to store action results.
        action_result = None

        # ✅ Handle Remote Actions Based on the "action" parameter.
        if action == "lock":
            print("🔒 Locking vehicle...")
            try:
                result = asyncio.run(asyncio.wait_for(remote_services.trigger_remote_door_lock(), timeout=90))
                action_result = result.state.value if result and hasattr(result, "state") else "Unknown lock status"
            except asyncio.TimeoutError:
                action_result = "Locking operation timed out after 90 seconds"
        elif action == "unlock":
            print("🔓 Unlocking vehicle...")
            try:
                result = asyncio.run(asyncio.wait_for(remote_services.trigger_remote_door_unlock(), timeout=90))
                action_result = result.state.value if result and hasattr(result, "state") else "Unknown unlock status"
            except asyncio.TimeoutError:
                action_result = "Unlocking operation timed out after 90 seconds"
        elif action == "flash":
            print("💡 Flashing headlights...")
            result = asyncio.run(remote_services.trigger_remote_light_flash())
            action_result = result.state.value if result and hasattr(result, "state") else "Unknown flash status"
        elif action == "ac":
            print("❄️ Activating air conditioning...")
            result = asyncio.run(remote_services.trigger_remote_service(Services.AIR_CONDITIONING))
            action_result = result.state.value if result and hasattr(result, "state") else "Unknown AC status"
        elif action == "fuel":
            fuel_and_battery = vehicle.fuel_and_battery
            action_result = {
                "remaining_fuel": fuel_and_battery.remaining_fuel,
                "remaining_fuel_percent": fuel_and_battery.remaining_fuel_percent,
                "remaining_range_fuel": fuel_and_battery.remaining_range_fuel,
                "remaining_range_electric": fuel_and_battery.remaining_range_electric,
                "remaining_range_total": fuel_and_battery.remaining_range_total,
            }
        elif action == "location":
            location = vehicle.location
            action_result = {
                "latitude": location.location.latitude if location and location.location else None,
                "longitude": location.location.longitude if location and location.location else None,
                "heading": location.heading,
                "timestamp": location.vehicle_update_timestamp.isoformat() if location and location.vehicle_update_timestamp else None,
            }
        elif action == "check_control":
            report = vehicle.check_control_message_report
            action_result = {
                "has_check_control_messages": report.has_check_control_messages,
                "messages": [msg.to_dict() for msg in report.messages] if report.messages else []
            }
        elif action == "mileage":
            mileage = vehicle.mileage
            action_result = {
                "value": mileage.value if hasattr(mileage, "value") else mileage,
                "unit": mileage.unit if hasattr(mileage, "unit") else "unknown"
            }
        elif action == "lock_status":
            # Return the full door lock state as provided by the API.
            print("🔍 Retrieving door lock status...")
            lock_state = vehicle.doors_windows.lock_state if hasattr(vehicle, "doors_windows") else None
            action_result = lock_state.value if lock_state and hasattr(lock_state, "value") else "Unknown"
        elif action == "is_locked":
            # New Action: Return only whether the doors are locked or unlocked.
            print("🔍 Checking if doors are strictly locked or unlocked...")
            lock_state = vehicle.doors_windows.lock_state if hasattr(vehicle, "doors_windows") else None
            if lock_state and hasattr(lock_state, "value"):
                if lock_state.value == "LOCKED":
                    action_result = "locked"
                elif lock_state.value == "UNLOCKED":
                    action_result = "unlocked"
                else:
                    action_result = f"Intermediate state: {lock_state.value}"
            else:
                action_result = "Unknown"
        else:
            print("🚗 No valid remote action specified. Returning vehicle details.")
            action_result = "No valid action specified. Returning vehicle details."

        # Include the remote action result in the response data.
        response_data["action_result"] = action_result

        headers = {
            "Access-Control-Allow-Origin": "*"
        }
        return (jsonify(response_data), 200, headers)

    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)