"""
BMW API with Integrated Fingerprint Patch for Quota Isolation
Self-contained version for Cloud Functions deployment
"""
import hashlib
import platform
import os
import re
import sys

# ===== FINGERPRINT PATCH SECTION =====
def apply_fingerprint_patch():
    """Apply fingerprint patch to bimmer_connected for quota isolation"""
    print("🔧 Applying BMW fingerprint patch for quota isolation...")
    
    class FingerprintGenerator:
        @staticmethod
        def get_x_user_agent():
            """Generate unique x-user-agent using PR #743 algorithm"""
            system_uuid = _get_system_uuid()
            build_string = _generate_build_string(system_uuid)
            x_user_agent = f"android({build_string});bmw;2.20.3;row"
            print(f"  → Generated x-user-agent: {x_user_agent}")
            return x_user_agent
    
    # Pre-emptive import hook for bimmer_connected modules
    original_import = __builtins__.__import__
    
    def custom_import(name, *args, **kwargs):
        module = original_import(name, *args, **kwargs)
        
        # Patch constants module when imported
        if name == 'bimmer_connected.const':
            if hasattr(module, 'X_USER_AGENT'):
                module.X_USER_AGENT = FingerprintGenerator.get_x_user_agent()
                print("  ✅ Patched bimmer_connected.const.X_USER_AGENT")
        
        return module
    
    __builtins__.__import__ = custom_import
    print("  ✅ Fingerprint patch installed successfully")

def _get_system_uuid():
    """Get stable system UUID for this deployment"""
    # Use Cloud Function/Run environment variables for uniqueness
    service_name = os.environ.get('K_SERVICE', 'bmw-api')
    revision = os.environ.get('K_REVISION', 'default')
    region = os.environ.get('FUNCTION_REGION', 'europe-west6')
    
    # Try to get container ID for additional uniqueness
    container_id = 'default'
    try:
        with open('/proc/self/cgroup', 'r') as f:
            for line in f:
                if 'docker' in line or 'containerd' in line:
                    container_id = line.split('/')[-1].strip()[:12]
                    break
    except:
        pass
    
    # Create stable deployment identifier
    deployment_id = f"{service_name}-{revision}-{region}-{container_id}"
    
    # Try to get machine ID as additional entropy
    try:
        with open('/etc/machine-id', 'r') as f:
            machine_id = f.read().strip()
            if machine_id:
                deployment_id = f"{machine_id}-{deployment_id}"
    except:
        pass
    
    return deployment_id

def _generate_build_string(system_uuid):
    """Generate Android-style build string using PR #743 algorithm"""
    # Use SHA1 as per PR #743 (not SHA256)
    digest = hashlib.sha1(system_uuid.encode()).hexdigest().upper()
    
    # Extract numeric digits from hash
    numeric_chars = re.findall(r'\d', digest)
    if len(numeric_chars) < 9:
        numeric_chars.extend(['0'] * (9 - len(numeric_chars)))
    
    # Build components
    middle_part = ''.join(numeric_chars[:6])
    build_part = ''.join(numeric_chars[6:9])
    
    # Platform prefix
    system = platform.system().lower()
    if system == 'linux':
        prefix = 'LP1A'
    elif system == 'darwin':
        prefix = 'DP1A'
    elif system == 'windows':
        prefix = 'WP1A'
    else:
        prefix = 'AP1A'
    
    return f"{prefix}.{middle_part}.{build_part}"

# Apply the patch before importing bimmer_connected
apply_fingerprint_patch()

# ===== MAIN BMW API SECTION =====
import json
import asyncio
from pathlib import Path
from google.cloud import storage
from flask import request, jsonify
import functions_framework
from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import Regions
from bimmer_connected.cli import load_oauth_store_from_file, store_oauth_store_to_file
from bimmer_connected.vehicle.remote_services import RemoteServices, Services

# Configuration for GCS Bucket & OAuth Token File Details
BUCKET_NAME = "bmw-api-bucket"
OAUTH_FILENAME = "bmw_oauth.json"
LOCAL_TOKEN_FILE = "/tmp/bmw_oauth.json"

def download_oauth_file():
    """Download the OAuth token file from Google Cloud Storage to local storage."""
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
    """Upload the OAuth token file from local storage to Google Cloud Storage."""
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(OAUTH_FILENAME)

    if os.path.exists(LOCAL_TOKEN_FILE):
        blob.upload_from_filename(LOCAL_TOKEN_FILE)
        print("✅ OAuth token uploaded to GCS.")
    else:
        print("⚠️ No OAuth token file found locally to upload.")

@functions_framework.http
def bmw_api(request):
    """Cloud Function entry point for BMW API with fingerprint patch."""
    # Handle CORS
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return ("", 204, headers)
    
    # Handle health check
    if request.method == "GET" and request.path == "/health":
        system_uuid = _get_system_uuid()
        build_string = _generate_build_string(system_uuid)
        x_user_agent = f"android({build_string});bmw;2.20.3;row"
        
        health_data = {
            "status": "healthy",
            "service": "bmw-api-fingerprint",
            "version": "2.0.0",
            "fingerprint": {
                "enabled": True,
                "system_uuid": system_uuid,
                "build_string": build_string,
                "x_user_agent": x_user_agent
            }
        }
        
        headers = {"Access-Control-Allow-Origin": "*"}
        return (jsonify(health_data), 200, headers)

    # Parse request
    try:
        data = request.get_json()
        if not data or "email" not in data or "password" not in data or "wkn" not in data:
            return jsonify({"error": "Email, password, and WKN are required"}), 400
    except Exception:
        return jsonify({"error": "Invalid JSON format"}), 400

    provided_email = data["email"]
    provided_password = data["password"]
    wkn = data["wkn"]
    action = data.get("action", "status")
    hcaptcha_token = data.get("hcaptcha")

    # Load existing OAuth token if available
    has_token_file = download_oauth_file()

    # Initialize BMW account
    if has_token_file:
        print("🔄 Re-authenticating using stored OAuth token...")
        account = MyBMWAccount(provided_email, provided_password, Regions.REST_OF_WORLD)
        load_oauth_store_from_file(Path(LOCAL_TOKEN_FILE), account)
    elif not hcaptcha_token:
        return jsonify({"error": "Missing hCaptcha token on first authentication"}), 400
    else:
        print("🔑 First-time authentication...")
        account = MyBMWAccount(provided_email, provided_password, Regions.REST_OF_WORLD)

    try:
        # Fetch vehicles
        asyncio.run(account.get_vehicles())
        vehicle = account.get_vehicle(wkn)
        remote_services = RemoteServices(vehicle)

        # Update OAuth token
        store_oauth_store_to_file(Path(LOCAL_TOKEN_FILE), account)
        upload_oauth_file()

        # Prepare response
        response_data = {
            "brand": vehicle.brand,
            "vehicle_name": vehicle.name,
            "vin": vehicle.vin,
        }

        # Handle actions
        action_result = None
        
        if action == "status":
            action_result = {
                "locked": vehicle.doors_windows.lock_state.value if hasattr(vehicle, "doors_windows") else "Unknown",
                "mileage": vehicle.mileage.value if hasattr(vehicle.mileage, "value") else vehicle.mileage
            }
        elif action == "lock":
            print("🔒 Locking vehicle...")
            result = asyncio.run(remote_services.trigger_remote_door_lock())
            action_result = "lock_initiated"
        elif action == "unlock":
            print("🔓 Unlocking vehicle...")
            result = asyncio.run(remote_services.trigger_remote_door_unlock())
            action_result = "unlock_initiated"
        elif action == "fuel":
            fuel_and_battery = vehicle.fuel_and_battery
            action_result = {
                "remaining_fuel_percent": fuel_and_battery.remaining_fuel_percent,
                "remaining_range_total": fuel_and_battery.remaining_range_total,
            }
        elif action == "location":
            location = vehicle.location
            action_result = {
                "latitude": location.location.latitude if location and location.location else None,
                "longitude": location.location.longitude if location and location.location else None,
            }
        else:
            action_result = "Action not implemented"

        response_data["action"] = action
        response_data["action_result"] = action_result

        headers = {"Access-Control-Allow-Origin": "*"}
        return (jsonify(response_data), 200, headers)

    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500