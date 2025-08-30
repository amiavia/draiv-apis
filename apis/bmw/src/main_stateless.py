"""
BMW API Stateless Cloud Function
=================================
This cloud function provides a stateless interface to BMW Connected Drive API.
It requires hCaptcha verification for EVERY request and never stores OAuth tokens.

Key Features:
- No token persistence (no GCS, no local storage)
- Always requires fresh hCaptcha verification
- Completely stateless operation
- Enhanced security through ephemeral authentication

Deployment:
-----------
gcloud functions deploy bmw_api_stateless \
    --runtime python311 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point bmw_api \
    --source . \
    --region europe-west6
    --timeout 300

Requirements:
-------------
bimmer-connected>=0.14.0
flask>=2.0.0
functions-framework>=3.0.0
"""

import asyncio
import traceback
from flask import Flask, request, jsonify
import functions_framework
from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import Regions
from bimmer_connected.vehicle.remote_services import RemoteServices, Services

app = Flask(__name__)

# 🔹 Main Cloud Function Handler - Stateless Version

@functions_framework.http
def bmw_api(request):
    """
    Stateless Cloud Function for BMW Connected Drive API.
    
    This function:
      - Requires hCaptcha token for EVERY request (no token storage)
      - Handles CORS preflight requests
      - Validates and parses JSON input
      - Authenticates fresh with BMW servers using hCaptcha
      - Executes the requested remote action
      - Returns vehicle data and action status
      
    Required Request Body:
    {
        "email": "user@example.com",
        "password": "user_password",
        "wkn": "vehicle_wkn",
        "hcaptcha": "hcaptcha_token",
        "action": "lock|unlock|flash|ac|fuel|location|mileage|lock_status|is_locked"
    }
    """
    
    # ✅ Handle CORS (Preflight Requests)
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return ("", 204, headers)

    # ✅ Parse and validate ALL required fields (including hCaptcha)
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

    # ✅ ALWAYS authenticate fresh with hCaptcha (no token storage/reuse)
    print(f"🔑 Stateless authentication for {provided_email} with hCaptcha...")
    
    try:
        # Create new account instance with hCaptcha for fresh authentication
        account = MyBMWAccount(
            provided_email, 
            provided_password, 
            Regions.REST_OF_WORLD, 
            hcaptcha_token=hcaptcha_token
        )
        
        # ✅ Fetch vehicles from BMW servers with timeout
        print("🚗 Fetching vehicle data...")
        try:
            await_task = asyncio.wait_for(
                account.get_vehicles(),
                timeout=60
            )
            asyncio.run(await_task)
            print(f"✅ Found {len(account.vehicles)} vehicles")
        except asyncio.TimeoutError:
            print("⏱️ Vehicle fetch timed out")
            return jsonify({
                "error": "BMW servers took too long to respond",
                "hint": "Please try again. BMW servers may be slow.",
                "timeout": "60 seconds"
            }), 504
        except Exception as e:
            print(f"❌ Failed to fetch vehicles: {str(e)}")
            return jsonify({
                "error": "Failed to fetch vehicles",
                "details": str(e),
                "hint": "Check credentials and hCaptcha token"
            }), 500
        
        # Get specific vehicle by WKN
        vehicle = account.get_vehicle(wkn)
        
        if not vehicle:
            return jsonify({
                "error": f"Vehicle with WKN '{wkn}' not found",
                "available_vehicles": [v.wkn for v in account.vehicles]
            }), 404
        
        print(f"🚙 Found vehicle: {vehicle.name} (WKN: {vehicle.wkn})")
        
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

        # ✅ Handle Remote Actions Based on Request
        
        if action == "lock":
            print("🔒 Executing remote door lock...")
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
            print("🔓 Executing remote door unlock...")
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
            print("💡 Executing remote light flash...")
            try:
                result = asyncio.run(
                    asyncio.wait_for(
                        remote_services.trigger_remote_light_flash(),
                        timeout=30
                    )
                )
                action_result = {
                    "status": result.state.value if result and hasattr(result, "state") else "Unknown",
                    "message": "Light flash command sent successfully"
                }
            except asyncio.TimeoutError:
                action_result = {
                    "status": "timeout",
                    "message": "Flash operation timed out"
                }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"Flash operation failed: {str(e)}"
                }
            
        elif action == "ac":
            print("❄️ Executing remote air conditioning activation...")
            try:
                result = asyncio.run(
                    asyncio.wait_for(
                        remote_services.trigger_remote_service(Services.AIR_CONDITIONING),
                        timeout=60
                    )
                )
                action_result = {
                    "status": result.state.value if result and hasattr(result, "state") else "Unknown",
                    "message": "Air conditioning command sent successfully"
                }
            except asyncio.TimeoutError:
                action_result = {
                    "status": "timeout",
                    "message": "AC operation timed out"
                }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"AC operation failed: {str(e)}"
                }
            
        elif action == "fuel":
            print("⛽ Retrieving fuel and battery information...")
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
            print("📍 Retrieving vehicle location...")
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
            
        elif action == "check_control":
            print("🔍 Retrieving check control messages...")
            try:
                report = vehicle.check_control_message_report
                action_result = {
                    "has_check_control_messages": report.has_check_control_messages if report else False,
                    "messages": [msg.to_dict() for msg in report.messages] if report and report.messages else []
                }
            except Exception as e:
                action_result = {
                    "status": "error",
                    "message": f"Failed to retrieve check control messages: {str(e)}"
                }
            
        elif action == "mileage":
            print("📏 Retrieving mileage information..."
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
            print("🔍 Retrieving detailed door lock status...")
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
            print("🔐 Checking if vehicle is locked...")
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
            print(f"ℹ️ No specific action requested or unknown action: {action}")
            action_result = {
                "status": "info",
                "message": "No valid action specified. Vehicle details returned.",
                "available_actions": [
                    "lock", "unlock", "flash", "ac", "fuel", 
                    "location", "check_control", "mileage", 
                    "lock_status", "is_locked"
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
        
        print(f"✅ Request completed successfully for {vehicle.name}")
        return (jsonify(response_data), 200, headers)

    except Exception as e:
        # Handle authentication or other errors
        error_message = str(e)
        print(f"❌ Error: {error_message}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Check for specific error types
        if "authentication" in error_message.lower():
            return jsonify({
                "error": "Authentication failed",
                "details": error_message,
                "hint": "Check email, password, and hCaptcha token validity"
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
                "authentication_method": "stateless_hcaptcha",
                "traceback": traceback.format_exc() if request.args.get('debug') else None
            }), 500


# For local testing only
if __name__ == "__main__":
    app.run(debug=True, port=8080)