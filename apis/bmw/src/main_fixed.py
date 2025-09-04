"""
BMW API Fixed Cloud Function - Direct Implementation
=====================================================
This bypasses bimmer_connected library issues by implementing
BMW authentication directly with proper user agent handling.
"""

import asyncio
import json
import functions_framework
from flask import jsonify, Response

# Import our fixed authentication
from bmw_auth_fix import BMWAuthFixed

@functions_framework.http
def bmw_api_fixed(request):
    """
    Fixed BMW API endpoint that properly handles user agent
    """
    
    # Handle CORS
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return ("", 204, headers)
    
    # Parse request
    try:
        data = request.get_json()
        
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
    
    email = data["email"]
    password = data["password"]
    wkn = data["wkn"]
    hcaptcha_token = data["hcaptcha"]
    
    print(f"🔑 Fixed authentication for {email}...")
    print(f"📝 hCaptcha token (first 50 chars): {hcaptcha_token[:50]}...")
    
    # Use our fixed authentication
    auth = BMWAuthFixed()
    
    try:
        # Run async authentication
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Authenticate with BMW
        success = loop.run_until_complete(
            auth.authenticate_with_hcaptcha(email, password, hcaptcha_token)
        )
        
        if not success:
            return jsonify({
                "error": "Authentication failed",
                "details": "BMW rejected the credentials or hCaptcha token",
                "hint": "Ensure hCaptcha token is fresh (expires in 2 minutes)"
            }), 401
        
        # Get vehicles
        vehicles = loop.run_until_complete(auth.get_vehicles())
        
        # Find the specific vehicle by WKN
        target_vehicle = None
        for vehicle in vehicles:
            if vehicle.get('vin') == wkn or vehicle.get('wkn') == wkn:
                target_vehicle = vehicle
                break
        
        if not target_vehicle:
            return jsonify({
                "error": f"Vehicle with WKN '{wkn}' not found",
                "available_vehicles": [v.get('vin', 'unknown') for v in vehicles]
            }), 404
        
        # Return success response
        response_data = {
            "success": True,
            "message": "Authentication successful with fixed implementation",
            "vehicle": target_vehicle,
            "implementation": "direct_api",
            "user_agent_fix": "active"
        }
        
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        }
        
        return (jsonify(response_data), 200, headers)
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ Error: {error_message}")
        
        return jsonify({
            "error": "Request failed",
            "details": error_message,
            "implementation": "direct_api"
        }), 500
        
    finally:
        # Clean up
        loop.run_until_complete(auth.close())
        loop.close()