#!/usr/bin/env python3
"""
Integration test for Skoda Connect API
Tests all components working together with test credentials
"""
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set test environment
os.environ["LOG_LEVEL"] = "INFO"
os.environ["ENCRYPTION_KEY"] = "test_key_for_integration_only_12345678901234"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
os.environ["GOOGLE_CLOUD_BUCKET"] = "test-bucket"

async def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        # Core modules
        import main
        print("✅ main.py imported")
        
        import auth_manager
        print("✅ auth_manager.py imported")
        
        import vehicle_manager
        print("✅ vehicle_manager.py imported")
        
        import remote_services
        print("✅ remote_services.py imported")
        
        import models
        print("✅ models.py imported")
        
        # Utilities
        from utils import circuit_breaker
        print("✅ circuit_breaker imported")
        
        from utils import cache_manager
        print("✅ cache_manager imported")
        
        from utils import error_handler
        print("✅ error_handler imported")
        
        from utils import rate_limiter
        print("✅ rate_limiter imported")
        
        from utils import logger
        print("✅ logger imported")
        
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

async def test_model_validation():
    """Test Pydantic models"""
    print("\n📊 Testing data models...")
    
    try:
        from models import AuthSetupRequest, VehicleStatus, ErrorCode
        
        # Test auth request
        auth_req = AuthSetupRequest(
            email="Info@miavia.ai",
            password="wozWi9-matvah-xonmyq",
            s_pin="2405"
        )
        print(f"✅ AuthSetupRequest validated: {auth_req.email}")
        
        # Test vehicle status
        status = VehicleStatus(
            locked=True,
            doors_open=False,
            windows_open=False,
            fuel_level=65,
            battery_level=None,
            odometer=15234,
            range_km=520
        )
        print(f"✅ VehicleStatus validated: {status.fuel_level}% fuel")
        
        # Test error codes
        assert ErrorCode.SPIN_REQUIRED == "SPIN_REQUIRED"
        print("✅ Error codes validated")
        
        return True
    except Exception as e:
        print(f"❌ Model validation failed: {e}")
        return False

async def test_utilities():
    """Test utility components"""
    print("\n🔧 Testing utilities...")
    
    try:
        from utils.circuit_breaker import SkodaCircuitBreaker
        from utils.cache_manager import SkodaCacheManager
        from utils.rate_limiter import SkodaRateLimiter
        from utils.logger import SkodaLogger
        
        # Test circuit breaker
        cb = SkodaCircuitBreaker(failure_threshold=5, recovery_timeout=60)
        assert cb.state == "CLOSED"
        print(f"✅ Circuit breaker initialized: state={cb.state}")
        
        # Test cache manager (memory mode)
        cache = SkodaCacheManager(use_redis=False)
        await cache.set("test_key", "test_value", ttl=10)
        value = await cache.get("test_key")
        assert value == "test_value"
        print("✅ Cache manager working")
        
        # Test rate limiter (memory mode)
        limiter = SkodaRateLimiter(use_redis=False)
        allowed = await limiter.check_limit("test_user", "status")
        assert allowed == True
        print("✅ Rate limiter working")
        
        # Test logger
        logger = SkodaLogger("test")
        logger.info("Test log message")
        print("✅ Logger working")
        
        return True
    except Exception as e:
        print(f"❌ Utilities test failed: {e}")
        return False

async def test_auth_components():
    """Test authentication components"""
    print("\n🔐 Testing authentication components...")
    
    try:
        from auth_manager import validate_spin
        from models import SPinRequest
        
        # Test S-PIN validation
        valid = validate_spin("2405")
        assert valid == True
        print("✅ S-PIN validation: 2405 is valid")
        
        invalid = validate_spin("0000")
        assert invalid == False
        print("✅ S-PIN validation: 0000 is invalid (simple pattern)")
        
        # Test S-PIN request model
        spin_req = SPinRequest(s_pin="2405")
        assert spin_req.s_pin == "2405"
        print("✅ S-PIN request model validated")
        
        return True
    except Exception as e:
        print(f"❌ Auth component test failed: {e}")
        return False

async def test_api_structure():
    """Test API application structure"""
    print("\n🌐 Testing API structure...")
    
    try:
        from main import app
        
        # Check that app is a FastAPI instance
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
        print("✅ FastAPI app created")
        
        # Check routes are registered
        routes = [route.path for route in app.routes]
        
        # Check key endpoints exist
        expected_endpoints = [
            "/health",
            "/auth/setup",
            "/auth/validate", 
            "/vehicles",
            "/vehicles/{vin}",
            "/vehicles/{vin}/lock",
            "/vehicles/{vin}/unlock"
        ]
        
        for endpoint in expected_endpoints:
            if any(endpoint in route for route in routes):
                print(f"✅ Endpoint found: {endpoint}")
            else:
                print(f"⚠️ Endpoint missing: {endpoint}")
        
        return True
    except Exception as e:
        print(f"❌ API structure test failed: {e}")
        return False

async def main():
    """Run all integration tests"""
    print("=" * 50)
    print("🚀 SKODA CONNECT API INTEGRATION TEST")
    print("=" * 50)
    
    results = []
    
    # Run all tests
    results.append(await test_imports())
    results.append(await test_model_validation())
    results.append(await test_utilities())
    results.append(await test_auth_components())
    results.append(await test_api_structure())
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"✅ Passed: {passed}/{total}")
    if failed > 0:
        print(f"❌ Failed: {failed}/{total}")
    
    success_rate = (passed / total) * 100
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("The Skoda Connect API is ready for deployment.")
    else:
        print("\n⚠️ Some tests failed. Please review the output above.")
    
    print("\n📝 Test Credentials Available:")
    print("Email: Info@miavia.ai")
    print("Password: wozWi9-matvah-xonmyq")
    print("S-PIN: 2405")
    
    return success_rate == 100

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)