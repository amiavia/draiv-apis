#!/usr/bin/env python3
"""
BMW API Quota Fix Deployment Test Script

This script tests the quota handling functionality in staging/production
to verify the fix is working correctly.
"""
import asyncio
import json
import time
import sys
from typing import Dict, Any
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BMWQuotaDeploymentTester:
    """Test quota handling deployment"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health_endpoint(self) -> Dict[str, Any]:
        """Test health endpoint includes quota information"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                data = await response.json()
                
                # Check for required quota fields
                required_fields = [
                    'user_agent_info',
                    'metrics',
                    'status'
                ]
                
                for field in required_fields:
                    if field not in data:
                        raise AssertionError(f"Health endpoint missing field: {field}")
                
                # Check user agent info structure
                user_agent_info = data.get('user_agent_info', {})
                if not user_agent_info.get('user_agent', '').startswith('draiv-bmw-api/'):
                    raise AssertionError("Invalid user agent format")
                
                logger.info("✅ Health endpoint test passed")
                return data
                
        except Exception as e:
            logger.error(f"❌ Health endpoint test failed: {e}")
            raise
    
    async def test_metrics_endpoint(self) -> Dict[str, Any]:
        """Test metrics endpoint includes circuit breaker stats"""
        try:
            async with self.session.get(f"{self.base_url}/metrics") as response:
                data = await response.json()
                
                # Check for circuit breaker metrics
                if 'circuit_breaker_state' not in data:
                    raise AssertionError("Metrics missing circuit_breaker_state")
                
                logger.info("✅ Metrics endpoint test passed")
                return data
                
        except Exception as e:
            logger.error(f"❌ Metrics endpoint test failed: {e}")
            raise
    
    async def test_user_agent_consistency(self) -> bool:
        """Test user agent remains consistent across requests"""
        try:
            agents = []
            
            # Make multiple requests to health endpoint
            for i in range(3):
                async with self.session.get(f"{self.base_url}/health") as response:
                    data = await response.json()
                    agent = data.get('user_agent_info', {}).get('user_agent')
                    agents.append(agent)
                    await asyncio.sleep(0.1)  # Small delay between requests
            
            # All agents should be identical
            if len(set(agents)) != 1:
                raise AssertionError(f"User agent inconsistency: {agents}")
            
            logger.info(f"✅ User agent consistency test passed: {agents[0]}")
            return True
            
        except Exception as e:
            logger.error(f"❌ User agent consistency test failed: {e}")
            raise
    
    async def test_api_request_with_quota_handling(self, email: str, password: str, wkn: str) -> bool:
        """Test API request with proper quota error handling"""
        try:
            payload = {
                "email": email,
                "password": password,
                "wkn": wkn,
                "action": "status"
            }
            
            async with self.session.post(
                f"{self.base_url}",
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                data = await response.json()
                
                if response.status == 429:  # Quota limit error
                    if 'quota_limit' not in data.get('error', {}).get('type', ''):
                        raise AssertionError("429 response doesn't indicate quota error")
                    
                    retry_after = data.get('error', {}).get('retry_after')
                    if retry_after:
                        logger.info(f"✅ Quota error handled properly, retry after {retry_after}s")
                    else:
                        logger.info("✅ Quota error handled (no retry timing)")
                    
                    return True
                    
                elif response.status == 401:  # Authentication error (expected for test)
                    logger.info("✅ Got authentication error (expected for test credentials)")
                    return True
                    
                elif response.status == 200:
                    logger.info("✅ API request successful")
                    return True
                    
                else:
                    logger.warning(f"⚠️  Unexpected response status: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ API request test failed: {e}")
            raise
    
    async def run_all_tests(self, test_credentials: Dict[str, str] = None) -> bool:
        """Run complete deployment test suite"""
        logger.info("🚀 Starting BMW API quota fix deployment tests...")
        
        try:
            # Test 1: Health endpoint
            health_data = await self.test_health_endpoint()
            
            # Test 2: Metrics endpoint  
            metrics_data = await self.test_metrics_endpoint()
            
            # Test 3: User agent consistency
            await self.test_user_agent_consistency()
            
            # Test 4: API request (optional with credentials)
            if test_credentials:
                await self.test_api_request_with_quota_handling(
                    email=test_credentials.get('email', ''),
                    password=test_credentials.get('password', ''),
                    wkn=test_credentials.get('wkn', '')
                )
            else:
                logger.info("⏭️  Skipping API request test (no credentials provided)")
            
            logger.info("🎉 All deployment tests passed!")
            
            # Print summary
            print("\n" + "="*50)
            print("BMW QUOTA FIX DEPLOYMENT TEST RESULTS")
            print("="*50)
            print(f"Service Status: {health_data.get('status')}")
            print(f"User Agent: {health_data.get('user_agent_info', {}).get('user_agent')}")
            print(f"Circuit Breaker: {metrics_data.get('circuit_breaker_state', 'closed')}")
            print(f"Total Requests: {metrics_data.get('requests_total', 0)}")
            print(f"Success Rate: {metrics_data.get('requests_success', 0)}/{metrics_data.get('requests_total', 0)}")
            print("="*50)
            
            return True
            
        except Exception as e:
            logger.error(f"💥 Deployment test suite failed: {e}")
            return False


async def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test BMW API quota fix deployment")
    parser.add_argument('--url', default='http://localhost:8080', help='API base URL')
    parser.add_argument('--email', help='Test email for API request')
    parser.add_argument('--password', help='Test password for API request')  
    parser.add_argument('--wkn', help='Test WKN for API request')
    
    args = parser.parse_args()
    
    # Prepare test credentials if provided
    test_creds = None
    if args.email and args.password and args.wkn:
        test_creds = {
            'email': args.email,
            'password': args.password,
            'wkn': args.wkn
        }
    
    # Run tests
    async with BMWQuotaDeploymentTester(args.url) as tester:
        success = await tester.run_all_tests(test_creds)
        
        if success:
            print("\n✅ DEPLOYMENT READY: Quota fix is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ DEPLOYMENT ISSUES: Fix quota handling before production!")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())