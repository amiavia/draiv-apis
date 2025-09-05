#!/usr/bin/env python3
"""
BMW API Workaround Test Script
Using bimmer_connected library directly to get fingerprint and tokens
Based on the workaround approach shown in the screenshot
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

async def test_bimmer_connected_cli():
    """Test using bimmer_connected as a module to get fingerprint"""
    
    print("=" * 60)
    print("BMW API WORKAROUND TEST")
    print("Using bimmer_connected CLI approach")
    print("=" * 60)
    
    # Import bimmer_connected
    try:
        from bimmer_connected.account import MyBMWAccount
        from bimmer_connected.api.regions import Regions
        print("✅ Successfully imported bimmer_connected v0.17.2")
    except ImportError as e:
        print(f"❌ Failed to import bimmer_connected: {e}")
        print("Please install: pip install bimmer-connected==0.17.2")
        return False
    
    # Get credentials from environment or prompt
    email = os.getenv('BMW_EMAIL')
    password = os.getenv('BMW_PASSWORD')
    
    if not email or not password:
        print("\n⚠️  No credentials in environment, using test mode")
        print("Set BMW_EMAIL and BMW_PASSWORD environment variables for real test")
        email = "test@example.com"
        password = "test_password"
    
    print(f"\n📧 Email: {email}")
    print(f"🔑 Password: {'*' * len(password)}")
    
    # Test 1: Get fingerprint using the CLI method
    print("\n" + "=" * 40)
    print("TEST 1: Get Fingerprint via CLI")
    print("=" * 40)
    
    try:
        # Create account instance
        account = MyBMWAccount(
            username=email,
            password=password,
            region=Regions.REST_OF_WORLD  # or Regions.NORTH_AMERICA, Regions.CHINA
        )
        
        print(f"✅ Created MyBMWAccount instance")
        print(f"   Region: {account.region.name}")
        
        # Get the fingerprint (x-user-agent)
        if hasattr(account, 'config'):
            if hasattr(account.config, 'authentication'):
                auth = account.config.authentication
                if hasattr(auth, 'x_user_agent'):
                    fingerprint = auth.x_user_agent
                    print(f"✅ Fingerprint: {fingerprint}")
                else:
                    # Try alternative methods
                    print("⚠️  x_user_agent not found in expected location")
        
        # Try to authenticate
        print("\n" + "=" * 40)
        print("TEST 2: Authenticate and Get Tokens")
        print("=" * 40)
        
        try:
            await account.get_vehicles()
            print("✅ Authentication successful!")
            
            # Try to get tokens
            if hasattr(account.config, 'authentication'):
                auth = account.config.authentication
                if hasattr(auth, 'access_token'):
                    token = auth.access_token
                    print(f"✅ Access token: {token[:20]}...")
                if hasattr(auth, 'refresh_token'):
                    refresh = auth.refresh_token  
                    print(f"✅ Refresh token: {refresh[:20]}...")
                    
        except Exception as auth_error:
            print(f"❌ Authentication failed: {auth_error}")
            print("\nThis is expected with test credentials.")
            print("The important part is getting the fingerprint format.")
    
    except Exception as e:
        print(f"❌ Error creating account: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Show how to use the fingerprint in direct API calls
    print("\n" + "=" * 40)
    print("TEST 3: Direct API Call with Fingerprint")
    print("=" * 40)
    
    print("""
The workaround approach:
1. Use bimmer_connected to generate valid fingerprint
2. Extract the fingerprint (x-user-agent header)
3. Use this fingerprint in direct API calls
4. Store and reuse tokens to avoid re-authentication

Example direct API call:
```python
headers = {
    'x-user-agent': fingerprint,  # From bimmer_connected
    'authorization': f'Bearer {access_token}',
    'accept': 'application/json'
}
```
""")
    
    return True


async def test_fingerprint_generation():
    """Test different fingerprint generation methods"""
    
    print("\n" + "=" * 40)
    print("TEST 4: Fingerprint Generation Methods")
    print("=" * 40)
    
    # Method 1: From bimmer_connected PR #743
    import hashlib
    import uuid
    import platform
    import re
    
    def generate_fingerprint_v1():
        """Generate fingerprint using PR #743 method"""
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
        
        # SHA1 hash (not SHA256)
        digest = hashlib.sha1(system_uuid.encode()).hexdigest().upper()
        
        # Extract numeric digits
        numeric_chars = re.findall(r'\d', digest)
        if len(numeric_chars) < 9:
            numeric_chars.extend(['0'] * (9 - len(numeric_chars)))
        
        # Build string
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
        return fingerprint
    
    # Method 2: Simple UUID-based
    def generate_fingerprint_v2():
        """Simple UUID-based fingerprint"""
        unique_id = str(uuid.uuid4()).replace('-', '')[:16].upper()
        return f"android(LP1A.{unique_id[:6]}.{unique_id[6:9]});bmw;2.20.3;row"
    
    print("Fingerprint v1 (PR #743):", generate_fingerprint_v1())
    print("Fingerprint v2 (UUID):", generate_fingerprint_v2())
    
    return True


async def main():
    """Run all tests"""
    
    # Test bimmer_connected CLI approach
    success = await test_bimmer_connected_cli()
    
    # Test fingerprint generation
    await test_fingerprint_generation()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print("""
Key findings from the workaround:
1. bimmer_connected v0.17.2 has working fingerprint generation
2. The fingerprint must match specific format expected by BMW
3. Once authenticated, tokens can be reused to avoid quota issues
4. The fingerprint should remain stable for the same system

Next steps:
1. Extract working fingerprint from bimmer_connected
2. Use it in our direct API implementation
3. Cache and reuse tokens to minimize authentication calls
""")
    
    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)