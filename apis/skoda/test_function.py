#!/usr/bin/env python3
"""Simple test for Skoda API Cloud Function"""

import sys
sys.path.append('src')

# Mock Flask request object
class MockRequest:
    def __init__(self, method='POST', json_data=None):
        self.method = method
        self._json_data = json_data or {}
    
    def get_json(self):
        return self._json_data

# Test the function
if __name__ == "__main__":
    print("Testing Skoda API Cloud Function...")
    
    # Test data
    test_data = {
        'email': 'Info@miavia.ai',
        'password': 'wozWi9-matvah-xonmyq',
        'vin': 'TMBJJ7NX5MY061741',
        'action': 'status'
    }
    
    try:
        # Import without functions_framework to test core logic
        with open('src/main_cloud.py', 'r') as f:
            code = f.read()
            
        # Remove functions framework imports and decorators
        code = code.replace('import functions_framework', '# import functions_framework')
        code = code.replace('@functions_framework.http', '# @functions_framework.http')
        code = code.replace('from flask import jsonify, Response', 'from json import dumps as jsonify')
        
        # Execute the code
        exec(code)
        
        # Test the function
        mock_request = MockRequest(json_data=test_data)
        result = skoda_api(mock_request)
        print("✅ Function executed successfully!")
        print("Result type:", type(result))
        if hasattr(result, '__len__'):
            print("Result length:", len(str(result)))
        
    except Exception as e:
        print("❌ Function test failed:", str(e))
        import traceback
        traceback.print_exc()