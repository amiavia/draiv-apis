"""
BMW API Stateless - No OAuth token storage, fresh authentication every request
Clean implementation using bimmer_connected 0.17.3
"""
import asyncio
from flask import request, jsonify
import functions_framework
from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import Regions
from bimmer_connected.vehicle.remote_services import RemoteServices

@functions_framework.http
def bmw_api(request):
    """
    BMW API Cloud Function - Completely stateless version
    Requires hCaptcha token for every request
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
            "service": "bmw-api-stateless",
            "version": "1.0.0",
            "library": "bimmer_connected==0.17.3",
            "features": {
                "stateless": True,
                "oauth_storage": "disabled",
                "hcaptcha_required": True
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
        hcaptcha_token = data.get("hcaptcha")
        
        if not all([email, password, wkn, hcaptcha_token]):
            return jsonify({
                "error": "Missing required fields",
                "required": ["email", "password", "wkn", "hcaptcha"],
                "message": "hCaptcha token is required for every request in stateless mode"
            }), 400
            
    except Exception as e:
        return jsonify({"error": f"Invalid request: {str(e)}"}), 400
    
    # Optional fields
    action = data.get("action", "status")
    
    print(f"📋 Processing stateless BMW API request: action={action}, vehicle={wkn}")
    
    try:
        # Always authenticate fresh with hCaptcha
        print(f"🔐 Fresh authentication for {email} with hCaptcha...")
        account = MyBMWAccount(email, password, Regions.REST_OF_WORLD, hcaptcha_token=hcaptcha_token)
        
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
            
        elif action == "climate" or action == "ac":
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
                
        elif action == "mileage":
            mileage = vehicle.mileage
            response["result"] = {
                "value": mileage.value if hasattr(mileage, "value") else mileage,
                "unit": mileage.unit if hasattr(mileage, "unit") else "km"
            }
            
        elif action == "lock_status":
            lock_state = vehicle.doors_windows.lock_state if hasattr(vehicle, "doors_windows") else None
            response["result"] = lock_state.value if lock_state and hasattr(lock_state, "value") else "Unknown"
            
        elif action == "is_locked":
            lock_state = vehicle.doors_windows.lock_state if hasattr(vehicle, "doors_windows") else None
            if lock_state and hasattr(lock_state, "value"):
                if lock_state.value == "LOCKED":
                    response["result"] = "locked"
                elif lock_state.value == "UNLOCKED":
                    response["result"] = "unlocked"
                else:
                    response["result"] = f"Intermediate state: {lock_state.value}"
            else:
                response["result"] = "Unknown"
                
        elif action == "check_control":
            report = vehicle.check_control_message_report
            response["result"] = {
                "has_check_control_messages": report.has_check_control_messages if report else False,
                "messages": [msg.to_dict() for msg in report.messages] if report and report.messages else []
            }
            
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
                "message": "Invalid credentials or hCaptcha token",
                "hint": "Ensure hCaptcha token is valid and credentials are correct"
            }), 401
        elif "429" in error_msg or "quota" in error_msg.lower():
            return jsonify({
                "error": "Rate limited",
                "message": "BMW API quota exceeded",
                "hint": "Please try again later"
            }), 429
        elif "hcaptcha" in error_msg.lower():
            return jsonify({
                "error": "hCaptcha required",
                "message": "Valid hCaptcha token is required for stateless authentication",
                "hint": "Provide 'hcaptcha' field with valid token"
            }), 400
        else:
            return jsonify({
                "error": "Request failed",
                "message": error_msg,
                "service": "bmw-api-stateless"
            }), 500

if __name__ == "__main__":
    # Local testing
    from flask import Flask
    app = Flask(__name__)
    app.run(debug=True, port=8080)