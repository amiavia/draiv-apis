#!/usr/bin/env python3
"""
BMW API Standalone Test - Implementing the Workaround
======================================================
This implements the workaround approach from the screenshot:
1. Generate proper fingerprint (x-user-agent)
2. Use it for authentication
3. Store and reuse tokens
"""

import asyncio
import aiohttp
import json
import hashlib
import secrets
import base64
import os
import platform
import uuid
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse, parse_qs


def generate_bmw_fingerprint() -> str:
    """
    Generate BMW-compatible fingerprint (x-user-agent)
    Based on bimmer_connected PR #743 implementation
    """
    # Get stable system identifier
    system = platform.system().lower()
    
    try:
        if system == 'linux':
            # Try to read machine-id (most stable on Linux)
            try:
                with open('/etc/machine-id', 'r') as f:
                    system_uuid = f.read().strip()
            except:
                # Fallback to DMI product UUID
                try:
                    with open('/sys/class/dmi/id/product_uuid', 'r') as f:
                        system_uuid = f.read().strip()
                except:
                    # Final fallback to MAC address
                    system_uuid = str(uuid.getnode())
        elif system == 'darwin':  # macOS
            # Use hardware UUID on macOS
            import subprocess
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True,
                text=True
            )
            # Extract Hardware UUID
            for line in result.stdout.split('\n'):
                if 'Hardware UUID' in line:
                    system_uuid = line.split(':')[1].strip()
                    break
            else:
                system_uuid = str(uuid.getnode())
        else:  # Windows or other
            system_uuid = str(uuid.getnode())
    except:
        # Ultimate fallback
        system_uuid = str(uuid.uuid4())
    
    print(f"🔧 System UUID: {system_uuid}")
    
    # Use SHA1 (not SHA256) as per bimmer_connected
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
    
    # Platform-specific prefix
    if system == 'linux':
        prefix = 'LP1A'
    elif system == 'darwin':  # macOS
        prefix = 'DP1A'
    elif system == 'windows':
        prefix = 'WP1A'
    else:
        prefix = 'AP1A'  # Android default
    
    # Final fingerprint format
    fingerprint = f"android({prefix}.{middle_part}.{build_part});bmw;2.20.3;row"
    
    print(f"✅ Generated fingerprint: {fingerprint}")
    return fingerprint


class BMWDirectAPI:
    """Direct BMW API implementation with proper fingerprint"""
    
    # BMW OAuth endpoints (Rest of World)
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
        """Get headers with proper fingerprint"""
        headers = {
            'x-user-agent': self.fingerprint,  # Critical for BMW API
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
    
    async def authenticate(self, email: str, password: str) -> bool:
        """
        Authenticate with BMW using PKCE OAuth flow
        """
        print(f"\n🔐 Authenticating with BMW API...")
        print(f"📧 Email: {email}")
        
        # Generate PKCE challenge
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        
        # Step 1: Initiate OAuth flow
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
        
        # Step 2: Authenticate with username/password
        auth_data = {
            **oauth_params,
            'username': email,
            'password': password
        }
        
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
                    # Extract authorization code from redirect
                    location = response.headers.get('location', '')
                    parsed = urlparse(location)
                    
                    # Handle both query and fragment parameters
                    if parsed.fragment:
                        # Some regions return code in fragment
                        params = parse_qs(parsed.fragment)
                    else:
                        params = parse_qs(parsed.query)
                    
                    if 'code' in params:
                        auth_code = params['code'][0]
                        print("✅ Got authorization code")
                        
                        # Step 3: Exchange code for tokens
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
                                print(f"   Access token: {self.access_token[:30]}...")
                                print(f"   Token expires: {self.token_expires}")
                                
                                # Save tokens to file (for reuse)
                                self._save_tokens()
                                
                                return True
                            else:
                                error_text = await token_response.text()
                                print(f"❌ Token exchange failed: {error_text}")
                                return False
                    else:
                        print(f"❌ No code in redirect: {location}")
                        return False
                        
                elif response.status == 200:
                    # Some regions might return tokens directly
                    data = await response.json()
                    if 'access_token' in data:
                        self.access_token = data['access_token']
                        self.refresh_token = data.get('refresh_token')
                        expires_in = data.get('expires_in', 3600)
                        self.token_expires = datetime.now() + timedelta(seconds=expires_in)
                        
                        print("✅ Got tokens directly!")
                        self._save_tokens()
                        return True
                    else:
                        print(f"❌ Unexpected response: {data}")
                        return False
                        
                elif response.status == 429:
                    print("❌ Rate limited (quota exceeded)")
                    print("   Wait before retrying...")
                    return False
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Authentication failed ({response.status}): {error_text}")
                    
                    # Check for specific error types
                    if 'quota' in error_text.lower():
                        print("   → Quota limit hit. The fingerprint might be rate-limited.")
                    elif 'invalid_client' in error_text.lower():
                        print("   → Invalid client credentials.")
                    elif 'invalid_grant' in error_text.lower():
                        print("   → Invalid username/password.")
                        
                    return False
                    
        except Exception as e:
            print(f"❌ Error during authentication: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _save_tokens(self):
        """Save tokens to file for reuse"""
        token_data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expires': self.token_expires.isoformat() if self.token_expires else None,
            'fingerprint': self.fingerprint
        }
        
        with open('bmw_tokens.json', 'w') as f:
            json.dump(token_data, f, indent=2)
        print("💾 Tokens saved to bmw_tokens.json")
    
    def _load_tokens(self) -> bool:
        """Load tokens from file"""
        try:
            with open('bmw_tokens.json', 'r') as f:
                data = json.load(f)
                
            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token')
            
            if data.get('token_expires'):
                self.token_expires = datetime.fromisoformat(data['token_expires'])
                
                # Check if token is still valid
                if self.token_expires > datetime.now():
                    print("✅ Loaded valid tokens from file")
                    return True
                else:
                    print("⚠️  Tokens expired, need to refresh")
                    return False
            return False
            
        except FileNotFoundError:
            print("📄 No saved tokens found")
            return False
        except Exception as e:
            print(f"❌ Error loading tokens: {e}")
            return False
    
    async def get_vehicles(self) -> list:
        """Get list of vehicles"""
        if not self.access_token:
            print("❌ Not authenticated")
            return []
        
        headers = self._get_headers(authenticated=True)
        
        try:
            async with self.session.get(
                self.VEHICLES_URL,
                headers=headers
            ) as response:
                
                print(f"📡 Vehicles response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    vehicles = data.get('vehicles', [])
                    print(f"✅ Found {len(vehicles)} vehicles")
                    
                    for vehicle in vehicles:
                        print(f"  🚗 {vehicle.get('model', 'Unknown')} - VIN: {vehicle.get('vin', 'N/A')}")
                        
                    return vehicles
                    
                elif response.status == 401:
                    print("❌ Authentication expired, need to refresh token")
                    return []
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to get vehicles: {error_text}")
                    return []
                    
        except Exception as e:
            print(f"❌ Error getting vehicles: {e}")
            return []


async def main():
    """Test the BMW API with proper fingerprint"""
    
    print("=" * 60)
    print("BMW API STANDALONE TEST")
    print("Implementing the workaround with proper fingerprint")
    print("=" * 60)
    
    # Get credentials from environment
    email = os.getenv('BMW_EMAIL')
    password = os.getenv('BMW_PASSWORD')
    
    if not email or not password:
        print("\n⚠️  No credentials found in environment")
        print("Set BMW_EMAIL and BMW_PASSWORD environment variables")
        print("\nRunning in demo mode to show fingerprint generation...")
        
        # Just show the fingerprint generation
        fingerprint = generate_bmw_fingerprint()
        print(f"\n📍 Your system's BMW fingerprint: {fingerprint}")
        print("\nThis fingerprint should remain stable for your system.")
        print("BMW uses it to track API quota limits.")
        return
    
    async with BMWDirectAPI() as api:
        # Try to load existing tokens first
        if api._load_tokens():
            print("📂 Using saved tokens...")
            
            # Test with saved tokens
            vehicles = await api.get_vehicles()
            
            if not vehicles:
                print("⚠️  Saved tokens might be expired, re-authenticating...")
                success = await api.authenticate(email, password)
                
                if success:
                    vehicles = await api.get_vehicles()
        else:
            # Fresh authentication
            success = await api.authenticate(email, password)
            
            if success:
                vehicles = await api.get_vehicles()
            else:
                print("\n⚠️  Authentication failed")
                print("Possible reasons:")
                print("1. Invalid credentials")
                print("2. API quota exceeded for this fingerprint")
                print("3. BMW API changes")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())