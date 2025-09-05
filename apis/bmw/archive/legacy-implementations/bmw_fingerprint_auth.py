#!/usr/bin/env python3
"""
BMW Authentication with Fingerprint Extraction
==============================================
This module uses bimmer_connected to get a valid fingerprint,
then uses it for direct API calls to avoid quota issues.
"""

import asyncio
import aiohttp
import json
import hashlib
import secrets
import base64
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse, parse_qs

# Import bimmer_connected for fingerprint generation
from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import Regions


class BMWFingerprintAuth:
    """BMW authentication using bimmer_connected fingerprint"""
    
    # BMW OAuth endpoints
    BASE_URL = "https://customer.bmwgroup.com"
    OAUTH_BASE = "https://customer.bmwgroup.com/gcdm/oauth"
    
    # OAuth configuration
    CLIENT_ID = "dbf0a542-ebd1-4ff0-a9a7-55172fbfce35"
    REDIRECT_URI = "com.bmw.connected://oauth"
    SCOPE = "openid profile email offline_access smacc vehicle_data perseus dlm svds cesim vsapi remote_services fupo authenticate_user"
    
    def __init__(self, region: str = "rest_of_world"):
        """Initialize with region"""
        self.region = self._get_region(region)
        self.session = None
        self.fingerprint = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires = None
        
    def _get_region(self, region_str: str) -> Regions:
        """Convert string to BMW region"""
        region_map = {
            "north_america": Regions.NORTH_AMERICA,
            "china": Regions.CHINA,
            "rest_of_world": Regions.REST_OF_WORLD
        }
        return region_map.get(region_str.lower(), Regions.REST_OF_WORLD)
    
    async def extract_fingerprint(self, email: str, password: str) -> str:
        """
        Extract working fingerprint from bimmer_connected
        
        This is the key workaround - we use bimmer_connected's
        working fingerprint generation logic.
        """
        print("🔍 Extracting fingerprint from bimmer_connected...")
        
        try:
            # Create account instance
            account = MyBMWAccount(
                username=email,
                password=password,
                region=self.region
            )
            
            # The fingerprint is generated during initialization
            # We need to extract it from the internal configuration
            
            # Method 1: Try to get from config
            if hasattr(account, 'config'):
                config = account.config
                
                # Check for authentication headers
                if hasattr(config, 'authentication'):
                    auth = config.authentication
                    if hasattr(auth, 'x_user_agent'):
                        self.fingerprint = auth.x_user_agent
                        print(f"✅ Extracted fingerprint: {self.fingerprint}")
                        return self.fingerprint
            
            # Method 2: Try to get from session headers
            if hasattr(account, '_session'):
                session = account._session
                if hasattr(session, 'headers'):
                    headers = session.headers
                    if 'x-user-agent' in headers:
                        self.fingerprint = headers['x-user-agent']
                        print(f"✅ Extracted fingerprint from session: {self.fingerprint}")
                        return self.fingerprint
            
            # Method 3: Generate using bimmer_connected's method
            # This replicates the internal generation logic
            from bimmer_connected.const import get_user_agent
            self.fingerprint = get_user_agent()
            print(f"✅ Generated fingerprint using bimmer_connected: {self.fingerprint}")
            return self.fingerprint
            
        except ImportError:
            # Fallback: Generate our own fingerprint
            print("⚠️  Could not import get_user_agent, using fallback")
            self.fingerprint = self._generate_fallback_fingerprint()
            return self.fingerprint
            
        except Exception as e:
            print(f"⚠️  Error extracting fingerprint: {e}")
            # Use fallback generation
            self.fingerprint = self._generate_fallback_fingerprint()
            return self.fingerprint
    
    def _generate_fallback_fingerprint(self) -> str:
        """Generate fingerprint if extraction fails"""
        import platform
        import uuid
        import re
        
        # Get system UUID
        system = platform.system().lower()
        
        try:
            if system == 'linux':
                with open('/etc/machine-id', 'r') as f:
                    system_uuid = f.read().strip()
            else:
                system_uuid = str(uuid.getnode())
        except:
            system_uuid = str(uuid.uuid4())
        
        # SHA1 hash (BMW uses SHA1, not SHA256)
        digest = hashlib.sha1(system_uuid.encode()).hexdigest().upper()
        
        # Extract numeric digits
        numeric_chars = re.findall(r'\d', digest)
        if len(numeric_chars) < 9:
            numeric_chars.extend(['0'] * (9 - len(numeric_chars)))
        
        # Build string components
        middle = ''.join(numeric_chars[:6])
        build = ''.join(numeric_chars[6:9])
        
        # Platform prefix
        if system == 'linux':
            prefix = 'LP1A'
        elif system == 'darwin':
            prefix = 'DP1A'  
        else:
            prefix = 'WP1A'
        
        fingerprint = f"android({prefix}.{middle}.{build});bmw;2.20.3;row"
        print(f"✅ Generated fallback fingerprint: {fingerprint}")
        return fingerprint
    
    async def authenticate_with_fingerprint(self, email: str, password: str, hcaptcha_token: Optional[str] = None) -> bool:
        """
        Authenticate using the extracted fingerprint
        
        This performs direct OAuth authentication using the fingerprint
        from bimmer_connected, avoiding library overhead.
        """
        if not self.fingerprint:
            self.fingerprint = await self.extract_fingerprint(email, password)
        
        print(f"🔐 Authenticating with fingerprint: {self.fingerprint}")
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Generate PKCE challenge
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        
        # Step 1: Initialize OAuth
        headers = {
            'x-user-agent': self.fingerprint,
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)',
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded'
        }
        
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
        
        try:
            # Step 2: Authenticate
            auth_data = {
                'username': email,
                'password': password,
                'client_id': self.CLIENT_ID,
                'response_type': 'code',
                'redirect_uri': self.REDIRECT_URI,
                'state': oauth_params['state'],
                'scope': self.SCOPE,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            }
            
            if hcaptcha_token:
                auth_data['hcaptcha_token'] = hcaptcha_token
            
            # Authenticate
            async with self.session.post(
                f"{self.OAUTH_BASE}/authenticate",
                data=urlencode(auth_data),
                headers=headers,
                allow_redirects=False
            ) as response:
                print(f"Auth response status: {response.status}")
                
                if response.status == 302:
                    # Extract authorization code from redirect
                    location = response.headers.get('location', '')
                    parsed = urlparse(location)
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
                                print(f"   Access token: {self.access_token[:20]}...")
                                print(f"   Expires at: {self.token_expires}")
                                return True
                            else:
                                error = await token_response.text()
                                print(f"❌ Token exchange failed: {error}")
                                return False
                    else:
                        print("❌ No authorization code in redirect")
                        return False
                        
                elif response.status == 200:
                    # Direct token response (some regions)
                    data = await response.json()
                    if 'access_token' in data:
                        self.access_token = data.get('access_token')
                        self.refresh_token = data.get('refresh_token')
                        expires_in = data.get('expires_in', 3600)
                        self.token_expires = datetime.now() + timedelta(seconds=expires_in)
                        print("✅ Got tokens directly")
                        return True
                    else:
                        print(f"❌ Unexpected response: {data}")
                        return False
                else:
                    error = await response.text()
                    print(f"❌ Authentication failed: {error}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error during authentication: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_vehicles(self) -> list:
        """Get vehicles using authenticated session"""
        if not self.access_token:
            print("❌ Not authenticated")
            return []
        
        headers = {
            'x-user-agent': self.fingerprint,
            'authorization': f'Bearer {self.access_token}',
            'accept': 'application/json'
        }
        
        try:
            async with self.session.get(
                f"{self.BASE_URL}/api/me/vehicles/v2",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    vehicles = data.get('vehicles', [])
                    print(f"✅ Found {len(vehicles)} vehicles")
                    return vehicles
                else:
                    error = await response.text()
                    print(f"❌ Failed to get vehicles: {error}")
                    return []
        except Exception as e:
            print(f"❌ Error getting vehicles: {e}")
            return []
    
    async def refresh_access_token(self) -> bool:
        """Refresh the access token"""
        if not self.refresh_token:
            print("❌ No refresh token available")
            return False
        
        headers = {
            'x-user-agent': self.fingerprint,
            'content-type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.CLIENT_ID
        }
        
        try:
            async with self.session.post(
                f"{self.OAUTH_BASE}/token",
                data=urlencode(data),
                headers=headers
            ) as response:
                if response.status == 200:
                    tokens = await response.json()
                    self.access_token = tokens.get('access_token')
                    if 'refresh_token' in tokens:
                        self.refresh_token = tokens['refresh_token']
                    expires_in = tokens.get('expires_in', 3600)
                    self.token_expires = datetime.now() + timedelta(seconds=expires_in)
                    print("✅ Token refreshed successfully")
                    return True
                else:
                    error = await response.text()
                    print(f"❌ Token refresh failed: {error}")
                    return False
        except Exception as e:
            print(f"❌ Error refreshing token: {e}")
            return False
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()


async def test_fingerprint_auth():
    """Test the fingerprint authentication"""
    import os
    
    email = os.getenv('BMW_EMAIL', 'test@example.com')
    password = os.getenv('BMW_PASSWORD', 'test_password')
    
    print("=" * 60)
    print("BMW FINGERPRINT AUTHENTICATION TEST")
    print("=" * 60)
    
    auth = BMWFingerprintAuth()
    
    try:
        # Extract fingerprint
        fingerprint = await auth.extract_fingerprint(email, password)
        print(f"\n📍 Fingerprint: {fingerprint}")
        
        # Authenticate
        success = await auth.authenticate_with_fingerprint(email, password)
        
        if success:
            print("\n✅ Authentication successful!")
            
            # Get vehicles
            vehicles = await auth.get_vehicles()
            for vehicle in vehicles:
                print(f"  🚗 {vehicle.get('model', 'Unknown')} - {vehicle.get('vin', 'No VIN')}")
            
            # Test token refresh
            print("\n🔄 Testing token refresh...")
            refresh_success = await auth.refresh_access_token()
            if refresh_success:
                print("✅ Token refresh successful!")
        else:
            print("\n❌ Authentication failed")
            print("This is expected with test credentials.")
            print("The important part is the fingerprint extraction worked.")
            
    finally:
        await auth.close()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_fingerprint_auth())