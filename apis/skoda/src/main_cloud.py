"""
Skoda API Cloud Function
========================
This cloud function provides interface to Skoda Connect (MySkoda) API.
Follows the same pattern as BMW API for consistency.

Key Features:
- S-PIN authentication for privileged operations
- Session-based authentication with MySkoda
- Support for lock/unlock, status, location, climate control
- Compatible with test account: Info@miavia.ai

Deployment:
-----------
gcloud functions deploy skoda_api \
    --runtime python311 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point skoda_api \
    --source . \
    --region europe-west6
    --timeout 90

Test Credentials:
-----------------
Email: Info@miavia.ai
Password: wozWi9-matvah-xonmyq
S-PIN: 2405
VIN: TMBJJ7NX5MY061741
"""

import asyncio
import traceback
import json
import logging
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime

import functions_framework
from flask import jsonify, Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import MySkoda library
try:
    from myskoda import MySkoda
    from myskoda.models.info import InfoStatus
    MYSKODA_AVAILABLE = True
except ImportError:
    logger.warning("MySkoda library not available - will return mock data")
    MYSKODA_AVAILABLE = False
    # Create dummy class for type hints
    class MySkoda:
        pass

# Configuration
PROJECT_ID = os.environ.get("GCP_PROJECT", "miavia-422212")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")

# S-PIN validation
def validate_spin(spin: str) -> bool:
    """Validate S-PIN format (4 digits, not simple patterns)"""
    if not spin or len(spin) != 4 or not spin.isdigit():
        return False
    # Reject simple patterns
    if spin in ["0000", "1111", "2222", "3333", "4444", "5555", "6666", "7777", "8888", "9999", "1234", "4321"]:
        return False
    return True

# Mock data for testing when MySkoda is not available
def get_mock_vehicle_data(vin: str) -> Dict[str, Any]:
    """Return mock vehicle data for testing"""
    return {
        "vin": vin,
        "model": "Skoda Octavia",
        "year": 2024,
        "status": {
            "locked": True,
            "doors": {
                "driver": "closed",
                "passenger": "closed",
                "rear_left": "closed",
                "rear_right": "closed"
            },
            "windows": {
                "driver": "closed",
                "passenger": "closed",
                "rear_left": "closed",
                "rear_right": "closed"
            },
            "fuel": {
                "level": 65,
                "range_km": 520
            },
            "mileage_km": 15234,
            "location": {
                "latitude": 47.3769,
                "longitude": 8.5417,
                "address": "Zürich, Switzerland",
                "updated_at": datetime.utcnow().isoformat()
            }
        },
        "capabilities": {
            "remote_lock": True,
            "climate_control": True,
            "location_tracking": True
        },
        "last_updated": datetime.utcnow().isoformat()
    }

async def authenticate_myskoda(email: str, password: str) -> Optional[MySkoda]:
    """Authenticate with MySkoda API"""
    if not MYSKODA_AVAILABLE:
        logger.info("MySkoda not available - using mock mode")
        return None
        
    try:
        logger.info(f"Authenticating with MySkoda for user: {email}")
        myskoda = MySkoda(email, password)
        await myskoda.connect()
        await myskoda.load_vehicles()
        logger.info("Successfully authenticated with MySkoda")
        return myskoda
    except Exception as e:
        logger.error(f"MySkoda authentication failed: {str(e)}")
        raise Exception(f"Authentication failed: {str(e)}")

async def get_vehicle_status(myskoda: MySkoda, vin: str) -> Dict[str, Any]:
    """Get vehicle status from MySkoda"""
    if not myskoda:
        return get_mock_vehicle_data(vin)
        
    try:
        # Find vehicle by VIN
        vehicle = None
        for v in myskoda.vehicles:
            if v.info.vin == vin:
                vehicle = v
                break
                
        if not vehicle:
            raise Exception(f"Vehicle not found: {vin}")
            
        # Get vehicle status
        await vehicle.update_info()
        
        # Convert to standardized format
        return {
            "vin": vehicle.info.vin,
            "model": vehicle.info.model_name,
            "year": vehicle.info.model_year,
            "status": {
                "locked": vehicle.status.doors_locked if hasattr(vehicle.status, 'doors_locked') else True,
                "fuel_level": vehicle.status.fuel_level if hasattr(vehicle.status, 'fuel_level') else 0,
                "battery_level": vehicle.status.battery_level if hasattr(vehicle.status, 'battery_level') else None,
                "mileage": vehicle.status.odometer if hasattr(vehicle.status, 'odometer') else 0,
                "range_km": vehicle.status.range if hasattr(vehicle.status, 'range') else 0
            },
            "location": {
                "latitude": vehicle.position.latitude if hasattr(vehicle, 'position') else 0,
                "longitude": vehicle.position.longitude if hasattr(vehicle, 'position') else 0,
                "updated_at": datetime.utcnow().isoformat()
            },
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get vehicle status: {str(e)}")
        # Return mock data as fallback
        return get_mock_vehicle_data(vin)

async def execute_vehicle_action(myskoda: MySkoda, vin: str, action: str, s_pin: str = None) -> Dict[str, Any]:
    """Execute a vehicle action"""
    # Actions that require S-PIN
    spin_required_actions = ["lock", "unlock", "climate_start", "climate_stop", "charge_start", "charge_stop"]
    
    if action in spin_required_actions:
        if not s_pin or not validate_spin(s_pin):
            raise Exception("Valid S-PIN required for this operation")
            
    if not myskoda:
        # Mock mode response
        return {
            "success": True,
            "action": action,
            "message": f"Mock: {action} command executed",
            "vin": vin,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    try:
        # Find vehicle
        vehicle = None
        for v in myskoda.vehicles:
            if v.info.vin == vin:
                vehicle = v
                break
                
        if not vehicle:
            raise Exception(f"Vehicle not found: {vin}")
            
        # Execute action based on type
        result = None
        if action == "lock":
            result = await vehicle.lock(pin=s_pin)
        elif action == "unlock":
            result = await vehicle.unlock(pin=s_pin)
        elif action == "flash":
            result = await vehicle.flash()
        elif action == "climate_start":
            temperature = 22  # Default temperature
            result = await vehicle.start_climatisation(temperature=temperature, pin=s_pin)
        elif action == "climate_stop":
            result = await vehicle.stop_climatisation()
        else:
            raise Exception(f"Unknown action: {action}")
            
        return {
            "success": True,
            "action": action,
            "result": str(result) if result else "Command sent",
            "vin": vin,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to execute action {action}: {str(e)}")
        raise Exception(f"Action failed: {str(e)}")

# Main Cloud Function Handler
@functions_framework.http
def skoda_api(request):
    """
    Cloud Function for Skoda Connect API.
    
    This function:
      - Handles CORS preflight requests
      - Validates and parses JSON input
      - Authenticates with MySkoda API
      - Executes the requested action
      - Returns vehicle data and action status
      
    Required Request Body:
    {
        "email": "user@example.com",
        "password": "user_password", 
        "vin": "vehicle_vin",
        "s_pin": "1234",  // Required for lock/unlock
        "action": "status|lock|unlock|flash|climate_start|climate_stop"
    }
    
    Test with:
    curl -X POST "https://europe-west6-miavia-422212.cloudfunctions.net/skoda_api" \
      -H "Content-Type: application/json" \
      -d '{
        "email": "Info@miavia.ai",
        "password": "wozWi9-matvah-xonmyq",
        "vin": "TMBJJ7NX5MY061741",
        "s_pin": "2405",
        "action": "status"
      }'
    """
    
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600"
        }
        return ("", 204, headers)
    
    # CORS headers for all responses
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    }
    
    # Parse and validate request
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["email", "password", "vin", "action"]
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "required": required_fields,
                "optional": ["s_pin"]
            }), 400, cors_headers
            
    except Exception as e:
        return jsonify({
            "error": "Invalid JSON format",
            "details": str(e)
        }), 400, cors_headers
    
    # Extract parameters
    email = data["email"]
    password = data["password"]
    vin = data["vin"]
    action = data["action"]
    s_pin = data.get("s_pin")
    
    logger.info(f"Processing request - Action: {action}, VIN: {vin}, User: {email}")
    
    # Process the request
    try:
        # Run async code in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Authenticate with MySkoda
        myskoda = loop.run_until_complete(authenticate_myskoda(email, password))
        
        # Execute action
        if action == "status":
            result = loop.run_until_complete(get_vehicle_status(myskoda, vin))
        elif action == "health":
            # Return health and MySkoda availability status
            result = {
                "service": "skoda_api_stateless",
                "version": "1.0.0",
                "environment": ENVIRONMENT,
                "myskoda_available": MYSKODA_AVAILABLE,
                "timestamp": datetime.utcnow().isoformat(),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            }
        elif action in ["lock", "unlock", "flash", "climate_start", "climate_stop"]:
            result = loop.run_until_complete(execute_vehicle_action(myskoda, vin, action, s_pin))
        else:
            return jsonify({
                "error": f"Unknown action: {action}",
                "available_actions": ["status", "health", "lock", "unlock", "flash", "climate_start", "climate_stop"]
            }), 400, cors_headers
        
        # Close connection if available
        if myskoda:
            try:
                loop.run_until_complete(myskoda.disconnect())
            except:
                pass
                
        return jsonify({
            "success": True,
            "data": result,
            "action": action,
            "vin": vin,
            "timestamp": datetime.utcnow().isoformat()
        }), 200, cors_headers
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Request failed: {error_msg}")
        logger.error(traceback.format_exc())
        
        # Check for specific error types
        if "authentication" in error_msg.lower():
            status_code = 401
            error_type = "AUTHENTICATION_ERROR"
        elif "not found" in error_msg.lower():
            status_code = 404
            error_type = "VEHICLE_NOT_FOUND"
        elif "s-pin" in error_msg.lower():
            status_code = 403
            error_type = "SPIN_REQUIRED"
        else:
            status_code = 500
            error_type = "INTERNAL_ERROR"
            
        return jsonify({
            "success": False,
            "error": error_type,
            "message": error_msg,
            "action": action,
            "vin": vin,
            "timestamp": datetime.utcnow().isoformat()
        }), status_code, cors_headers