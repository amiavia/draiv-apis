#!/usr/bin/env python3
"""
Test the deployed BMW API
"""
import requests
import json
import sys

# API endpoint
API_URL = "https://bmw-api-fixed-r3b47jhqiq-oa.a.run.app"

# Test credentials
EMAIL = "Info@miavia.ai"
PASSWORD = "qegbe6-ritdoz-vikDeK"
WKN = "WBA3K51040K175114"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{API_URL}/health")
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")
    print(f"Fingerprint: {data.get('fingerprint')}")
    print("-" * 50)
    return data.get('fingerprint')

def test_status(hcaptcha_token=None):
    """Test vehicle status"""
    print("Testing vehicle status...")
    
    payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "wkn": WKN,
        "action": "status"
    }
    
    if hcaptcha_token:
        payload["hcaptcha"] = hcaptcha_token
        print(f"Using hCaptcha token: {hcaptcha_token[:50]}...")
    
    response = requests.post(API_URL, json=payload)
    print(f"Status: {response.status_code}")
    
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")
    
    return response.status_code == 200

def main():
    print("=" * 60)
    print("BMW API Test - Live Deployment")
    print("=" * 60)
    
    # Test health
    fingerprint = test_health()
    
    # Test without hCaptcha
    print("\nTest 1: Without hCaptcha")
    success = test_status()
    
    if not success:
        print("\n⚠️  Authentication failed without hCaptcha")
        print("This is expected for BMW accounts that require hCaptcha")
        
        # Get hCaptcha token from user
        print("\nTo test with hCaptcha:")
        print("1. Get a fresh token from the BMW Connected app")
        print("2. Run: python3 test_live_api.py YOUR_HCAPTCHA_TOKEN")
    
    # If hCaptcha token provided as argument
    if len(sys.argv) > 1:
        print("\nTest 2: With hCaptcha")
        hcaptcha = sys.argv[1]
        success = test_status(hcaptcha)
        
        if success:
            print("\n✅ Authentication successful!")
        else:
            print("\n❌ Authentication failed even with hCaptcha")
            print("Possible issues:")
            print("- hCaptcha token expired (they last 2 minutes)")
            print("- Credentials incorrect")
            print("- BMW API changes")

if __name__ == "__main__":
    main()