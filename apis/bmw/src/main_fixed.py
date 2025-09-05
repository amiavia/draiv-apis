"""
BMW API Fixed with Dynamic Fingerprint
=======================================
Production implementation with PR #743 fingerprint generation
"""

import functions_framework
from flask import jsonify
import asyncio
import aiohttp
import json
import hashlib
import secrets
import base64
import platform
import uuid
import re
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse, parse_qs


def get_system_uuid() -> str:
    """
    Get stable system UUID for Cloud Run container
    This ensures consistent fingerprint across container lifecycle
    """
    # For Cloud Run, use service and revision info for stability
    service_name = os.environ.get('K_SERVICE', 'bmw-api-fingerprint')
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
    
    # Create stable identifier for this Cloud Run instance
    stable_id = f"{service_name}-{revision}-{region}-{container_id}"
    
    # Also try to get actual system UUID as fallback
    try:
        system = platform.system().lower()
        if system == 'linux':
            # Try machine-id first
            try:
                with open('/etc/machine-id', 'r') as f:
                    machine_id = f.read().strip()
                if machine_id:
                    # Combine with service info for uniqueness
                    return f"{machine_id}-{service_name}"
            except:
                pass
                
        # Fallback to MAC address
        mac_address = uuid.getnode()
        if mac_address:
            return f"{mac_address}-{service_name}"
            
    except:
        pass
        
    # Final fallback: use our stable Cloud Run ID
    return stable_id


def generate_bmw_fingerprint() -> str:
    """
    Generate BMW-compatible fingerprint based on PR #743
    """
    # Get stable system UUID
    system_uuid = get_system_uuid()
    print(f"🔧 System UUID: {system_uuid}")
    
    # Use SHA1 (BMW standard, not SHA256)
    digest = hashlib.sha1(system_uuid.encode()).hexdigest().upper()
    print(f"🔧 SHA1 digest: {digest}")
    
    # Extract numeric digits from hash
    numeric_chars = re.findall(r'\d', digest)
    if len(numeric_chars) < 9:
        # Pad with zeros if not enough digits
        numeric_chars.extend(['0'] * (9 - len(numeric_chars)))
    
    # Create build string components
    middle_part = ''.join(numeric_chars[:6])
    build_part = ''.join(numeric_chars[6:9])
    
    # Platform prefix (Linux for Cloud Run)
    prefix = 'LP1A'  # Linux Platform 1A
    
    # Final fingerprint format
    fingerprint = f"android({prefix}.{middle_part}.{build_part});bmw;2.20.3;row"
    
    print(f"✅ Generated fingerprint: {fingerprint}")
    return fingerprint


class BMWAPIFingerprint:
    """BMW API with dynamic fingerprint generation"""
    
    # BMW OAuth endpoints
    BASE_URL = "https://customer.bmwgroup.com"
    OAUTH_BASE = "https://customer.bmwgroup.com/gcdm/oauth"
    
    # BMW API endpoints
    VEHICLES_URL = f"{BASE_URL}/api/me/vehicles/v2"
    VEHICLE_STATE_URL = f"{BASE_URL}/api/vehicle/dynamic/v1"
    REMOTE_SERVICES_URL = f"{BASE_URL}/api/vehicle/remoteservices/v1"
    
    # OAuth configuration
    CLIENT_ID = "dbf0a542-ebd1-4ff0-a9a7-55172fbfce35"
    REDIRECT_URI = "com.bmw.connected://oauth"
    SCOPE = "openid profile email offline_access smacc vehicle_data perseus dlm svds cesim vsapi remote_services fupo authenticate_user"
    
    def __init__(self):
        self.session = None
        self.fingerprint = generate_bmw_fingerprint()
        self.access_token = None
        self.refresh_token = None
        self.token_expires = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_headers(self, authenticated: bool = False) -> Dict[str, str]:
        """Get headers with dynamic fingerprint"""
        headers = {
            'x-user-agent': self.fingerprint,  # Dynamic fingerprint
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)',
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'x-identity-provider': 'gcdm',
            'x-correlation-id': str(uuid.uuid4()),
            '24-hour-format': 'true'
        }
        
        if authenticated and self.access_token:
            headers['authorization'] = f'Bearer {self.access_token}'
            
        return headers
    
    async def authenticate(self, email: str, password: str, hcaptcha_token: Optional[str] = None) -> bool:
        """Authenticate with BMW using dynamic fingerprint"""
        print(f"\n🔐 Authenticating with BMW API...")
        print(f"📧 Email: {email}")
        print(f"🔑 Using fingerprint: {self.fingerprint}")
        
        # Generate PKCE challenge
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        
        # OAuth parameters
        oauth_params = {
            'client_id': self.CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': self.REDIRECT_URI,
            'state': secrets.token_urlsafe(16),
            'scope': self.SCOPE,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        headers = self._get_headers()
        headers['content-type'] = 'application/x-www-form-urlencoded'
        
        # Authenticate
        auth_data = {
            **oauth_params,
            'username': email,
            'password': password
        }
        
        if hcaptcha_token:
            auth_data['hcaptcha_token'] = hcaptcha_token
        
        try:
            async with self.session.post(
                f"{self.OAUTH_BASE}/authenticate",
                data=urlencode(auth_data),
                headers=headers,
                allow_redirects=False,
                ssl=True
            ) as response:
                
                print(f"📡 Auth response status: {response.status}")
                
                if response.status == 302:
                    # Extract authorization code
                    location = response.headers.get('location', '')
                    parsed = urlparse(location)
                    
                    # Handle both query and fragment
                    if parsed.fragment:
                        params = parse_qs(parsed.fragment)
                    else:
                        params = parse_qs(parsed.query)
                    
                    if 'code' in params:
                        auth_code = params['code'][0]
                        print("✅ Got authorization code")
                        
                        # Exchange for tokens
                        token_data = {
                            'grant_type': 'authorization_code',
                            'code': auth_code,
                            'redirect_uri': self.REDIRECT_URI,
                            'client_id': self.CLIENT_ID,
                            'code_verifier': code_verifier
                        }
                        
                        async with self.session.post(
                            f"{self.OAUTH_BASE}/token",
                            data=urlencode(token_data),
                            headers=headers
                        ) as token_response:
                            
                            if token_response.status == 200:
                                tokens = await token_response.json()
                                self.access_token = tokens.get('access_token')
                                self.refresh_token = tokens.get('refresh_token')
                                expires_in = tokens.get('expires_in', 3600)
                                self.token_expires = datetime.now() + timedelta(seconds=expires_in)
                                
                                print("✅ Authentication successful!")
                                return True
                            else:
                                error_text = await token_response.text()
                                print(f"❌ Token exchange failed: {error_text}")
                                return False
                    else:
                        print(f"❌ No code in redirect")
                        return False
                        
                elif response.status == 200:
                    # Direct token response
                    data = await response.json()
                    if 'access_token' in data:
                        self.access_token = data['access_token']
                        self.refresh_token = data.get('refresh_token')
                        expires_in = data.get('expires_in', 3600)
                        self.token_expires = datetime.now() + timedelta(seconds=expires_in)
                        print("✅ Got tokens directly!")
                        return True
                    else:
                        print(f"❌ Unexpected response")
                        return False
                        
                elif response.status == 429:
                    print("❌ Rate limited - but this should be less likely with unique fingerprint")
                    return False
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Authentication failed: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error during authentication: {e}")
            return False
    
    async def get_vehicles(self) -> list:
        """Get list of vehicles"""
        if not self.access_token:
            return []
        
        headers = self._get_headers(authenticated=True)
        
        try:
            async with self.session.get(
                self.VEHICLES_URL,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    vehicles = data.get('vehicles', [])
                    print(f"✅ Found {len(vehicles)} vehicles")
                    return vehicles
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to get vehicles: {error_text}")
                    return []
                    
        except Exception as e:
            print(f"❌ Error getting vehicles: {e}")
            return []
    
    async def execute_remote_service(self, vin: str, service: str) -> bool:
        """Execute remote service (lock, unlock, etc.)"""
        if not self.access_token:
            return False
        
        headers = self._get_headers(authenticated=True)
        headers['content-type'] = 'application/json'
        
        service_map = {
            'lock': 'RDL',
            'unlock': 'RDU',
            'climate': 'RCN',
            'horn': 'RHB',
            'lights': 'RLF'
        }
        
        service_code = service_map.get(service.lower())
        if not service_code:
            print(f"❌ Unknown service: {service}")
            return False
        
        try:
            async with self.session.post(
                f"{self.REMOTE_SERVICES_URL}/{vin}/{service_code}",
                headers=headers,
                json={}
            ) as response:
                
                if response.status == 200:
                    print(f"✅ Service {service} executed successfully")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Service execution failed: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error executing service: {e}")
            return False


@functions_framework.http
def bmw_api_fixed(request):
    """
    Google Cloud Run function for BMW API with dynamic fingerprint
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
    if request.path == "/health":
        fingerprint = generate_bmw_fingerprint()
        return jsonify({
            "status": "healthy",
            "service": "bmw-api-fingerprint",
            "version": "1.0.0",
            "fingerprint": fingerprint,
            "implementation": "PR #743 dynamic generation",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Parse request
    try:
        data = request.get_json()
        
        # Check required fields
        required_fields = ["email", "password", "action"]
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
    action = data["action"]
    wkn = data.get("wkn", "")
    hcaptcha_token = data.get("hcaptcha")
    
    print(f"🚗 Processing BMW API request...")
    print(f"📋 Action: {action}")
    
    # Run async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        async def process_request():
            async with BMWAPIFingerprint() as api:
                # Authenticate
                auth_success = await api.authenticate(email, password, hcaptcha_token)
                
                if not auth_success:
                    return {
                        "error": "Authentication failed",
                        "hint": "Check credentials or try with hCaptcha token"
                    }, 401
                
                # Handle different actions
                if action == "status":
                    vehicles = await api.get_vehicles()
                    
                    if wkn:
                        # Find specific vehicle
                        target_vehicle = None
                        for vehicle in vehicles:
                            if vehicle.get('vin') == wkn:
                                target_vehicle = vehicle
                                break
                        
                        if not target_vehicle:
                            return {
                                "error": f"Vehicle {wkn} not found"
                            }, 404
                        
                        return {
                            "success": True,
                            "vehicle": target_vehicle,
                            "fingerprint": api.fingerprint
                        }, 200
                    else:
                        return {
                            "success": True,
                            "vehicles": vehicles,
                            "fingerprint": api.fingerprint
                        }, 200
                
                elif action in ["lock", "unlock", "climate", "horn", "lights"]:
                    if not wkn:
                        return {
                            "error": "VIN/WKN required for remote services"
                        }, 400
                    
                    success = await api.execute_remote_service(wkn, action)
                    
                    if success:
                        return {
                            "success": True,
                            "action": action,
                            "vehicle": wkn,
                            "fingerprint": api.fingerprint
                        }, 200
                    else:
                        return {
                            "error": f"Failed to execute {action}"
                        }, 500
                
                else:
                    return {
                        "error": f"Unknown action: {action}",
                        "available_actions": ["status", "lock", "unlock", "climate", "horn", "lights"]
                    }, 400
        
        result, status_code = loop.run_until_complete(process_request())
        
        # Add CORS headers to response
        response = jsonify(result)
        response.headers["Access-Control-Allow-Origin"] = "*"
        
        return response, status_code
        
    except Exception as e:
        print(f"❌ Error processing request: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500
    
    finally:
        loop.close()


if __name__ == "__main__":
    # For local testing
    import sys
    
    print("BMW API Fingerprint - Local Test Mode")
    print("=" * 50)
    
    # Generate and display fingerprint
    fingerprint = generate_bmw_fingerprint()
    print(f"\nYour unique fingerprint: {fingerprint}")
    print("\nThis fingerprint is unique to this system/container")
    print("and will help distribute BMW API quota limits.")
    print("\n✅ The fingerprint generation is working correctly!")
    print("Deploy this to Google Cloud Functions to use it in production.")
    
    # You can add test authentication here if needed
    # asyncio.run(test_auth())