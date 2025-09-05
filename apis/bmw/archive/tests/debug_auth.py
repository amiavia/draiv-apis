#!/usr/bin/env python3
"""
Debug BMW authentication to see what's failing
"""
import requests
import json

# Test with both our API and the original stateless API
def test_both_apis():
    
    # Test data
    payload = {
        "email": "Info@miavia.ai",
        "password": "qegbe6-ritdoz-vikDeK",
        "wkn": "WBA3K51040K175114",
        "action": "status",
        "hcaptcha": "P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.haJwZACjZXhwzmi6pfSncGFzc2tlecUDu8LyOeCjCmCwFWhwoGOlHV87ryGcjdqg1m6skSs5gc7oFMaqRkg8e6rNc5p2mFZSrttCpSRt2jHsyL7WqrnSGznlE8UXayxziM07xiO5ksnp8QgmNR-zeNw6uyUM7BO5RCLddM20tqL1xCh2TMhH_klwxIim0tBLbn7gtNHtmEeWNTW7zCc8R88Hygj_sFkxOKEYCW8tPEoWLc58Ev4obvOqY9qIZ2CxMw7C4DCSlayAMRNepaOLRqSeUnoFW0LKt39MPhgKKczrsT1YvhymsfWwCKkwNWXDj0OBDIp9hcQrDQTH4GHgZBoRmT3h3_1bvwkzHa7LC4U0KBR-9idDeqovaiMoqRujSJdZ-dCXsfl0l5KVi2D7qy94iz2-DFPrMhIpSsrb4Wiuz2qi5t2m9mBOAh4VijS_B7bRf-8N6BFHavP2s9hZrZArtZaRm3X3It8PO09l-gDwvKYSEsIj4FBck-mxtp7wbfyQznWJgRGZvtdy0hLuGYYVhU_AfsR1I0YJMnYAIf4Y9YW5O6MgnE0QnkTx_yNPGnXGcTEtokHpY3Gn1yxJmp9elB0bbut5OnE8X15xA3ZlRl-7K5xIBWOTRnXuxM3nHmtztQNjAQCK8406n6K0BYVg_IeT2yU1j0XnSuCTXQdwiZ7ew9iKB1wyiE91Og7bCt5zGWHIvxIMNSvK2O6DKlUOCkN3yzxnZh3y78_DOE9YRU-6gQbhYrmBqj23nM5jXtgHkqj6WLOixBEcNdKOXolLjcoJFFV0mk0j7y6Dfn2H3XuK5uUR7K1kOfwZDFhb-qJe6WHtJU3i0VVmEq1GCTyHStmte4fPNCjz5ULFDf0-SqgHeO8ZqGqE_QcWoS1mbVRUF9VNgyTT19Fay9-fF2GX9yn7BDlDuL-D1VpXpLaUmBGpywOq2572JbIURD6tO6dUEUmFnLVwP3NlzUjp1MwmgG-7cbl3zO0AwE6eMgTCa_mL1dKr8-5KVXrGRLw4aFXZOxhOmWxEmnqTGHSI9-YCuUJ4PrbH1nkVkXhg_C9slw2xiacyhEQKdTY2djkjmHnpA4VsDvzj2Xs5eW6F9czFHan3BQ58V8YYIZGPfH4uwPHDjPBj5SI2dJddsKHzViosx3hK98Ey1imwW4h-qtb3YeEbtKB0YHpFvd9MgPJrGfBufwvsjChEn1Hc1ebId3yFX5HSIxzwvTUQWtzASSxSyHT5O457t_iT90QDhvavql2dy1xbpw_GjXJYai7mZco5q5mG6kSuS5uDXP-rAc5l0bCia3KoMjIwYWQwYTGoc2hhcmRfaWTOAzGDbw.CcxZNGVh0RbIAi7e9DZjVWA-VsYenoAdiDDqS9g6l5A"
    }
    
    apis = [
        ("New Fingerprint API", "https://bmw-api-fixed-r3b47jhqiq-oa.a.run.app"),
        ("Original Stateless API", "https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless")
    ]
    
    for name, url in apis:
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"URL: {url}")
        print(f"{'='*60}")
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
            except:
                print(f"Raw Response: {response.text[:500]}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_both_apis()