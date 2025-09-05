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
import secrets
import base64
import re

# BMW API Configuration - Updated to match bimmer_connected implementation
BMW_SERVER_URL = "https://cocoapi.bmwgroup.com"  # Rest of World server
OAUTH_CONFIG_PATH = "/eadrax-ucs/v1/presentation/oauth/config"
BMW_CLIENT_ID = "dbf0a542-ebd1-4ff0-a9a7-55172fbfce35"

def _get_system_uuid() -> str:
    """
    Get system UUID exactly as PR #743 does, adapted for Cloud Functions
    Replicate bimmer_connected PR #743 _get_system_uuid() function
    """
    import os
    import platform
    
    # For Cloud Functions, create a stable ID based on function metadata
    # This ensures same x-user-agent across requests in same deployment
    function_name = os.environ.get('K_SERVICE', 'bmw_api_stateless')
    function_revision = os.environ.get('K_REVISION', 'default')
    region = os.environ.get('FUNCTION_REGION', 'europe-west6')
    
    # Create stable system identifier for this Cloud Function deployment
    stable_id = f"{function_name}-{function_revision}-{region}"
    
    # Try to get actual system UUID as fallback (PR #743 method)
    try:
        system = platform.system().lower()
        if system == 'linux':
            # Try to read machine-id (PR #743 method)
            try:
                with open('/etc/machine-id', 'r') as f:
                    machine_id = f.read().strip()
                if machine_id:
                    return machine_id
            except:
                pass
                
        # Fallback to MAC address (PR #743 fallback)
        mac_address = uuid.getnode()
        if mac_address:
            return str(mac_address)
            
    except:
        pass
        
    # Final fallback: use our stable Cloud Function ID
    return stable_id

def generate_user_agent() -> str:
    """
    Generate x-user-agent exactly as PR #743 does
    Replicate bimmer_connected PR #743 user agent generation
    """
    
    # Get system UUID using PR #743 method
    system_uuid = _get_system_uuid()
    
    # Use SHA1 as PR #743 does (not SHA256)
    digest = hashlib.sha1(system_uuid.encode()).hexdigest().upper()
    print(f"🔧 System UUID: {system_uuid}")
    print(f"🔧 SHA1 digest: {digest}")
    
    # Extract numeric digits from hash (PR #743 method)
    numeric_chars = re.findall(r'\d', digest)
    if len(numeric_chars) < 9:
        # Pad with zeros if not enough digits
        numeric_chars.extend(['0'] * (9 - len(numeric_chars)))
    
    # Create build string components
    middle_part = ''.join(numeric_chars[:6])
    build_part = ''.join(numeric_chars[6:9])
    
    # Platform-specific prefix (PR #743 approach)
    import platform
    system = platform.system().lower()
    if system == 'linux':
        prefix = 'LP1A'
    elif system == 'darwin':  # macOS
        prefix = 'DP1A'
    elif system == 'windows':
        prefix = 'WP1A'
    else:
        prefix = 'XP1A'
    
    # Build string in PR #743 format
    build_string = f"{prefix}.{middle_part}.{build_part}"
    
    # Return full user agent matching BMW + PR #743 expectations
    user_agent = f"android({build_string});bmw;2.20.3;row"
    print(f"🔧 Generated PR #743 user agent: {user_agent}")
    return user_agent

async def get_oauth_settings() -> Dict[str, Any]:
    """Get OAuth settings from BMW API"""
    headers = {
        'ocp-apim-subscription-key': '4f1c85a3-758f-a37d-bbb6-f8704494acfa',  # REST_OF_WORLD key
        'x-user-agent': generate_user_agent(),
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
    }
    
    oauth_config_url = f"{BMW_SERVER_URL}{OAUTH_CONFIG_PATH}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(oauth_config_url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to get OAuth settings: {response.status}")

def generate_pkce_pair() -> tuple:
    """Generate PKCE code verifier and challenge"""
    
    # Generate random code verifier
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    # Generate code challenge using S256 method
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode('utf-8').rstrip('=')
    
    return code_verifier, code_challenge

async def authenticate_bmw(email: str, password: str, hcaptcha_token: str) -> Dict[str, Any]:
    """
    Authenticate with BMW API using OAuth Authorization Code flow with PKCE
    Following bimmer_connected PR #743 implementation
    
    Returns:
        Dict with access_token and refresh_token or error
    """
    try:
        # Step 1: Get OAuth configuration
        print("🚀 Step 1: Getting OAuth configuration...")
        oauth_settings = await get_oauth_settings()
        
        auth_endpoint = oauth_settings.get('authenticateEndpoint')
        token_endpoint = oauth_settings.get('tokenEndpoint')
        
        if not auth_endpoint or not token_endpoint:
            return {
                'success': False,
                'error': 'Missing OAuth endpoints in configuration'
            }
        
        # Step 2: Generate PKCE parameters
        print("🔧 Step 2: Generating PKCE parameters...")
        code_verifier, code_challenge = generate_pkce_pair()
        state = str(uuid.uuid4())
        nonce = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # Step 3: Authenticate to get authorization code
        print("🔐 Step 3: Authenticating to get authorization code...")
        
        auth_headers = {
            'ocp-apim-subscription-key': '4f1c85a3-758f-a37d-bbb6-f8704494acfa',  # REST_OF_WORLD key
            'bmw-session-id': session_id,
            'x-user-agent': generate_user_agent(),
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
            'content-type': 'application/x-www-form-urlencoded',
            'accept': 'application/json',
            'hcaptchatoken': hcaptcha_token
        }
        
        auth_data = {
            'client_id': BMW_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': 'com.bmw.connected://oauth',
            'scope': 'authenticate_user vehicle_data remote_services',
            'state': state,
            'nonce': nonce,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'username': email,
            'password': password
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                auth_endpoint,
                data=auth_data,
                headers=auth_headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                print(f"📡 Auth response status: {response.status}")
                auth_response_text = await response.text()
                print(f"📡 Auth response: {auth_response_text}")
                
                if response.status != 200:
                    return {
                        'success': False,
                        'error': auth_response_text,
                        'status': response.status
                    }
                
                # Parse authorization code from response
                auth_result = json.loads(auth_response_text)
                authorization_code = auth_result.get('authorization_code')
                
                if not authorization_code:
                    return {
                        'success': False,
                        'error': 'No authorization code in response',
                        'response': auth_result
                    }
        
        # Step 4: Exchange authorization code for tokens
        print("🎟️ Step 4: Exchanging code for tokens...")
        
        token_headers = {
            'ocp-apim-subscription-key': '4f1c85a3-758f-a37d-bbb6-f8704494acfa',
            'bmw-session-id': session_id,
            'x-user-agent': generate_user_agent(),
            'content-type': 'application/x-www-form-urlencoded'
        }
        
        token_data = {
            'client_id': BMW_CLIENT_ID,
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': 'com.bmw.connected://oauth',
            'code_verifier': code_verifier
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_endpoint,
                data=token_data,
                headers=token_headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                print(f"📡 Token response status: {response.status}")
                token_response_text = await response.text()
                print(f"📡 Token response: {token_response_text}")
                
                if response.status == 200:
                    tokens = json.loads(token_response_text)
                    print("✅ OAuth authentication successful!")
                    return {
                        'success': True,
                        'access_token': tokens.get('access_token'),
                        'refresh_token': tokens.get('refresh_token'),
                        'expires_in': tokens.get('expires_in', 3600)
                    }
                else:
                    return {
                        'success': False,
                        'error': token_response_text,
                        'status': response.status
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
    
    vehicles_url = f"{BMW_SERVER_URL}/eadrax-vcs/v5/vehicle-list"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                vehicles_url,
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
    # Map our service endpoints to BMW's remote command types
    service_map = {
        'lock': 'door-lock',
        'unlock': 'door-unlock',
        'flash': 'light-flash',
        'honk': 'horn-blow',
        'climate': 'climate-now'
    }
    service_type = service_map.get(service_endpoint, service_endpoint)
    url = f"{BMW_SERVER_URL}/eadrax-vrccs/v4/presentation/remote-commands/{service_type}"
    
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
        print("🔧 EXTREME DEBUG: Creating event loop...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Step 1: Authenticate with BMW
        print("🚀 EXTREME DEBUG: Step 1: Authenticating with BMW...")
        print(f"🔧 EXTREME DEBUG: About to call authenticate_bmw function...")
        auth_result = loop.run_until_complete(
            authenticate_bmw(email, password, hcaptcha_token)
        )
        print(f"🔧 EXTREME DEBUG: authenticate_bmw returned: {auth_result}")
        
        if not auth_result.get('success'):
            error_msg = auth_result.get('error', 'Unknown error')
            status_code = auth_result.get('status', 'unknown')
            print(f"❌ Authentication failed: {error_msg}")
            
            # Return raw BMW error response for debugging
            return jsonify({
                "error": "BMW Authentication Failed",
                "bmw_raw_error": str(error_msg),
                "bmw_status_code": status_code,
                "auth_result_full": auth_result,
                "implementation": "direct_api",
                "debug_info": "Raw BMW API response for troubleshooting"
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
        print(f"💥 EXTREME DEBUG: Critical error: {error_message}")
        print(f"🔧 EXTREME DEBUG: Full traceback: {traceback.format_exc()}")
        
        return jsonify({
            "error": "EXTREME DEBUG: Request processing failed",
            "details": error_message,
            "implementation": "direct_api_with_debug",
            "full_traceback": traceback.format_exc(),
            "debug_info": "This is our OAuth PKCE implementation with extreme debugging"
        }), 500
    
    finally:
        # Clean up event loop
        try:
            loop.close()
        except:
            pass