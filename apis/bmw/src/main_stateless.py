"""
BMW API Stateless Cloud Function - DIRECT IMPLEMENTATION
=========================================================
CRITICAL FIX: This bypasses bimmer_connected library entirely
and implements BMW authentication directly to avoid quota issues.
"""

import asyncio
import json
import aiohttp
import hashlib
import uuid
import functions_framework
from flask import jsonify, Response
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# BMW API Configuration
BMW_BASE_URL = "https://customer.bmwgroup.com"
BMW_AUTH_URL = f"{BMW_BASE_URL}/gcdm/oauth"
BMW_VEHICLES_URL = f"{BMW_BASE_URL}/api/me/vehicles/v2"
BMW_CLIENT_ID = "dbf0a542-ebd1-4ff0-a9a7-55172fbfce35"

def generate_user_agent() -> str:
    """Generate a dynamic user agent that BMW won't block"""
    # Get stable system ID
    system_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bmw-{uuid.getnode()}"))
    
    # Create hash for build string
    hash_obj = hashlib.sha256(system_id.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Generate Android-style build string
    prefix = ''.join([
        hash_hex[0].upper() if hash_hex[0].isalpha() else 'L',
        hash_hex[1].upper() if hash_hex[1].isalpha() else 'P',
        '1',
        hash_hex[2].upper() if hash_hex[2].isalpha() else 'A'
    ])
    
    middle_num = int(hash_hex[3:9], 16) % 1000000
    end_num = int(hash_hex[9:12], 16) % 1000
    
    build_string = f"{prefix}.{middle_num:06d}.{end_num:03d}"
    
    # Return full user agent matching BMW expectations
    user_agent = f"android({build_string});bmw;2.20.3;row"
    print(f"🔧 Generated user agent: {user_agent}")
    return user_agent

async def authenticate_bmw(email: str, password: str, hcaptcha_token: str) -> Dict[str, Any]:
    """
    Authenticate directly with BMW API
    
    Returns:
        Dict with access_token and refresh_token or error
    """
    # Generate unique session ID for BMW
    import uuid
    session_id = str(uuid.uuid4())
    
    headers = {
        'x-user-agent': generate_user_agent(),
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded',
        'accept': 'application/json',
        'ocp-apim-subscription-key': '4f1c85a3-758f-a37d-bbb6-f8704494acfa',  # REST_OF_WORLD key
        'bmw-session-id': session_id,
        'hcaptchatoken': hcaptcha_token
    }
    
    auth_data = {
        'username': email,
        'password': password,
        'client_id': BMW_CLIENT_ID,
        'response_type': 'token',
        'redirect_uri': 'com.bmw.connected://oauth',
        'scope': 'authenticate_user vehicle_data remote_services',
        'state': 'bmw_oauth_state'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BMW_AUTH_URL}/authenticate",
                data=auth_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                print(f"📡 Auth response status: {response.status}")
                response_text = await response.text()
                
                if response.status == 200:
                    data = json.loads(response_text)
                    print("✅ Authentication successful!")
                    return {
                        'success': True,
                        'access_token': data.get('access_token'),
                        'refresh_token': data.get('refresh_token'),
                        'expires_in': data.get('expires_in', 3600)
                    }
                else:
                    print(f"❌ Authentication failed: {response_text}")
                    return {
                        'success': False,
                        'error': response_text,
                        'status': response.status
                    }
                    
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': 'BMW authentication timeout'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

async def get_vehicles(access_token: str) -> Dict[str, Any]:
    """Get vehicles from BMW API"""
    headers = {
        'authorization': f'Bearer {access_token}',
        'x-user-agent': generate_user_agent(),
        'accept': 'application/json'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                BMW_VEHICLES_URL,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    vehicles = await response.json()
                    return {
                        'success': True,
                        'vehicles': vehicles
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Failed to get vehicles: {response.status}'
                    }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

async def execute_remote_service(access_token: str, vin: str, service: str) -> Dict[str, Any]:
    """Execute remote service on vehicle"""
    service_map = {
        'lock': 'door-lock',
        'unlock': 'door-unlock',
        'flash': 'light-flash',
        'climate': 'climate-now'
    }
    
    service_endpoint = service_map.get(service, service)
    url = f"{BMW_BASE_URL}/api/vehicle/remoteservices/v1/{vin}/{service_endpoint}"
    
    headers = {
        'authorization': f'Bearer {access_token}',
        'x-user-agent': generate_user_agent(),
        'accept': 'application/json',
        'content-type': 'application/json'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url,
                headers=headers,
                json={},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status in [200, 201, 202]:
                    return {
                        'success': True,
                        'message': f'Remote service {service} initiated'
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Remote service failed: {response.status}'
                    }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

@functions_framework.http
def bmw_api(request):
    """
    CRITICAL FIX: Direct BMW API implementation
    Bypasses bimmer_connected library quota issues
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
    action = data.get("action", "status")
    
    print(f"🔑 DIRECT API authentication for {email}...")
    print(f"📝 hCaptcha token (first 50 chars): {hcaptcha_token[:50]}...")
    
    try:
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Step 1: Authenticate with BMW
        print("🚀 Step 1: Authenticating with BMW...")
        auth_result = loop.run_until_complete(
            authenticate_bmw(email, password, hcaptcha_token)
        )
        
        if not auth_result.get('success'):
            error_msg = auth_result.get('error', 'Unknown error')
            print(f"❌ Authentication failed: {error_msg}")
            
            # Check for specific error patterns
            if "invalid_client" in str(error_msg).lower():
                return jsonify({
                    "error": "Authentication failed",
                    "details": "BMW rejected the credentials. This might be due to an expired or already-used hCaptcha token.",
                    "hint": "Please generate a fresh hCaptcha token (they expire in 2 minutes)",
                    "implementation": "direct_api"
                }), 401
            
            return jsonify({
                "error": "Authentication failed",
                "details": str(error_msg),
                "implementation": "direct_api"
            }), 401
        
        access_token = auth_result['access_token']
        print("✅ Authentication successful!")
        
        # Step 2: Get vehicles
        print("🚗 Step 2: Fetching vehicles...")
        vehicles_result = loop.run_until_complete(
            get_vehicles(access_token)
        )
        
        if not vehicles_result.get('success'):
            return jsonify({
                "error": "Failed to fetch vehicles",
                "details": vehicles_result.get('error'),
                "implementation": "direct_api"
            }), 500
        
        vehicles = vehicles_result.get('vehicles', [])
        print(f"✅ Found {len(vehicles)} vehicles")
        
        # Step 3: Find specific vehicle
        target_vehicle = None
        for vehicle in vehicles:
            if vehicle.get('vin') == wkn:
                target_vehicle = vehicle
                break
        
        if not target_vehicle:
            return jsonify({
                "error": f"Vehicle with WKN '{wkn}' not found",
                "available_vehicles": [v.get('vin', 'unknown') for v in vehicles],
                "implementation": "direct_api"
            }), 404
        
        print(f"✅ Found vehicle: {target_vehicle.get('model', 'Unknown')} ({wkn})")
        
        # Step 4: Execute action if requested
        action_result = None
        if action in ['lock', 'unlock', 'flash', 'climate']:
            print(f"🔧 Step 4: Executing {action}...")
            service_result = loop.run_until_complete(
                execute_remote_service(access_token, wkn, action)
            )
            action_result = service_result
        
        # Build response
        response_data = {
            "success": True,
            "vehicle": target_vehicle,
            "action": action,
            "action_result": action_result,
            "implementation": "direct_api",
            "message": "CRITICAL FIX: Using direct BMW API implementation"
        }
        
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        }
        
        print("✅ Request completed successfully!")
        return (jsonify(response_data), 200, headers)
        
    except Exception as e:
        import traceback
        error_message = str(e)
        print(f"💥 Critical error: {error_message}")
        print(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            "error": "Request processing failed",
            "details": error_message,
            "implementation": "direct_api",
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500
    
    finally:
        # Clean up event loop
        try:
            loop.close()
        except:
            pass