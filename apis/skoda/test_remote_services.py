#!/usr/bin/env python3
"""
Test script for Skoda Remote Services
Run: python test_remote_services.py
"""
import asyncio
import logging
import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from remote_services import SkodaRemoteServices, SPinValidationError, ValidationError, RemoteServiceError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_skoda_remote_services():
    """Test all Skoda remote service operations"""
    print("🚗 Testing Skoda Connect Remote Services")
    print("=" * 50)
    
    # Initialize service
    skoda_service = SkodaRemoteServices()
    test_vin = "TMBJB2ZE9M1234567"
    valid_spin = "2405"  # Test S-PIN
    invalid_spin = "1234"
    
    try:
        # Test 1: S-PIN Validation
        print("\n1. Testing S-PIN Validation")
        print(f"Valid S-PIN ({valid_spin}): {skoda_service.validate_spin_for_operation(valid_spin, 'lock')}")
        print(f"Invalid S-PIN ({invalid_spin}): {skoda_service.validate_spin_for_operation(invalid_spin, 'lock')}")
        print(f"Empty S-PIN: {skoda_service.validate_spin_for_operation('', 'lock')}")
        
        # Test 2: Lock vehicle with valid S-PIN
        print("\n2. Testing Vehicle Lock (Valid S-PIN)")
        try:
            result = await skoda_service.lock_vehicle(test_vin, valid_spin)
            print(f"✅ Lock successful: {result}")
        except Exception as e:
            print(f"❌ Lock failed: {e}")
        
        # Test 3: Lock vehicle with invalid S-PIN
        print("\n3. Testing Vehicle Lock (Invalid S-PIN)")
        try:
            result = await skoda_service.lock_vehicle(test_vin, invalid_spin)
            print(f"❌ Lock should have failed: {result}")
        except SPinValidationError as e:
            print(f"✅ Lock correctly rejected invalid S-PIN: {e}")
        
        # Test 4: Unlock vehicle with valid S-PIN
        print("\n4. Testing Vehicle Unlock (Valid S-PIN)")
        try:
            result = await skoda_service.unlock_vehicle(test_vin, valid_spin)
            print(f"✅ Unlock successful: {result}")
        except Exception as e:
            print(f"❌ Unlock failed: {e}")
        
        # Test 5: Climate control operations
        print("\n5. Testing Climate Control")
        try:
            # Start climate with temperature
            result = await skoda_service.start_climate_control(test_vin, 24)
            print(f"✅ Start climate successful: {result}")
            
            # Stop climate
            result = await skoda_service.stop_climate_control(test_vin)
            print(f"✅ Stop climate successful: {result}")
        except Exception as e:
            print(f"❌ Climate control failed: {e}")
        
        # Test 6: Flash lights (no S-PIN required)
        print("\n6. Testing Flash Lights")
        try:
            result = await skoda_service.flash_lights(test_vin)
            print(f"✅ Flash lights successful: {result}")
        except Exception as e:
            print(f"❌ Flash lights failed: {e}")
        
        # Test 7: Charging operations
        print("\n7. Testing EV Charging")
        try:
            # Start charging
            result = await skoda_service.start_charging(test_vin)
            print(f"✅ Start charging successful: {result}")
            
            # Stop charging  
            result = await skoda_service.stop_charging(test_vin)
            print(f"✅ Stop charging successful: {result}")
        except Exception as e:
            print(f"❌ Charging operations failed: {e}")
        
        # Test 8: Invalid temperature validation
        print("\n8. Testing Temperature Validation")
        try:
            result = await skoda_service.start_climate_control(test_vin, 50)  # Invalid temp
            print(f"❌ Should have failed with invalid temperature: {result}")
        except ValidationError as e:
            print(f"✅ Temperature validation working: {e}")
        
        # Test 9: Command queue status
        print("\n9. Testing Queue Status")
        queue_status = skoda_service.get_queue_status()
        print(f"Queue status: {queue_status}")
        
        # Test 10: Circuit breaker stats
        print("\n10. Circuit Breaker Stats")
        cb_stats = skoda_service.circuit_breaker.get_stats()
        print(f"Circuit breaker stats: {cb_stats}")
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await skoda_service.cleanup()
        print("🧹 Cleanup completed")

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(test_skoda_remote_services())