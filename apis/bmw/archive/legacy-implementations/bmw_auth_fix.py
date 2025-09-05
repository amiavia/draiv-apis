"""
BMW Authentication Fix - Direct Implementation
==============================================
This module provides a fixed authentication approach for BMW API
that bypasses the bimmer_connected library's problematic user agent.
"""

import aiohttp
import asyncio
import json
import hashlib
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class BMWAuthFixed:
    """Fixed BMW authentication that handles user agent properly"""
    
    # BMW API endpoints
    BASE_URL = "https://customer.bmwgroup.com"
    AUTH_URL = f"{BASE_URL}/gcdm/oauth"
    VEHICLES_URL = f"{BASE_URL}/api/me/vehicles/v2"
    
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.token_expires = None
        self.session = None
        
    def _generate_user_agent(self) -> str:
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
        
        # Return full user agent
        user_agent = f"android({build_string});bmw;2.20.3;row"
        print(f"Generated user agent: {user_agent}")
        return user_agent
    
    async def authenticate_with_hcaptcha(self, email: str, password: str, hcaptcha_token: str) -> bool:
        """
        Authenticate with BMW using hCaptcha token
        
        Returns:
            bool: True if authentication successful
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Set our custom headers
        headers = {
            'x-user-agent': self._generate_user_agent(),
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)',
            'content-type': 'application/json',
            'accept': 'application/json'
        }
        
        # Prepare auth payload
        auth_data = {
            'username': email,
            'password': password,
            'client_id': 'dbf0a542-ebd1-4ff0-a9a7-55172fbfce35',  # BMW client ID
            'response_type': 'token',
            'redirect_uri': 'com.bmw.connected://oauth',
            'scope': 'authenticate_user vehicle_data remote_services',
            'hcaptcha_token': hcaptcha_token
        }
        
        try:
            # Attempt authentication
            async with self.session.post(
                f"{self.AUTH_URL}/authenticate",
                json=auth_data,
                headers=headers
            ) as response:
                print(f"Auth response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get('access_token')
                    self.refresh_token = data.get('refresh_token')
                    expires_in = data.get('expires_in', 3600)
                    self.token_expires = datetime.now() + timedelta(seconds=expires_in)
                    
                    print("Authentication successful!")
                    return True
                else:
                    error_text = await response.text()
                    print(f"Authentication failed: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    async def get_vehicles(self) -> list:
        """Get list of vehicles"""
        if not self.access_token:
            raise Exception("Not authenticated")
        
        headers = {
            'authorization': f'Bearer {self.access_token}',
            'x-user-agent': self._generate_user_agent(),
            'accept': 'application/json'
        }
        
        async with self.session.get(self.VEHICLES_URL, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to get vehicles: {response.status}")
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()


# Test function for direct BMW API access
async def test_bmw_auth(email: str, password: str, hcaptcha_token: str) -> Dict[str, Any]:
    """
    Test BMW authentication with custom implementation
    
    Returns:
        Dict with success status and data or error
    """
    auth = BMWAuthFixed()
    
    try:
        # Authenticate
        success = await auth.authenticate_with_hcaptcha(email, password, hcaptcha_token)
        
        if success:
            # Get vehicles
            vehicles = await auth.get_vehicles()
            return {
                'success': True,
                'message': 'Authentication successful',
                'vehicles': vehicles
            }
        else:
            return {
                'success': False,
                'error': 'Authentication failed'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
        
    finally:
        await auth.close()