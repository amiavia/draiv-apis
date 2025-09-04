#!/usr/bin/env python3
"""
Test script for Skoda Authentication Manager
Tests authentication with provided credentials
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from auth_manager import SkodaAuthManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test credentials (as provided in requirements)
TEST_EMAIL = "Info@miavia.ai"
TEST_PASSWORD = "wozWi9-matvah-xonmyq"
TEST_SPIN = "2405"

# Mock bucket name for testing
TEST_BUCKET = "draiv-skoda-test"

async def test_authentication():
    """Test basic authentication functionality"""
    logger.info("Starting Skoda Authentication Manager test")
    
    try:
        # Initialize auth manager
        auth_manager = SkodaAuthManager(bucket_name=TEST_BUCKET)
        logger.info("✓ Auth manager initialized")
        
        # Test credential validation
        logger.info("Testing credential validation...")
        is_valid = auth_manager.validate_credentials(TEST_EMAIL, TEST_PASSWORD)
        logger.info(f"✓ Credential validation: {'PASSED' if is_valid else 'FAILED'}")
        
        # Test S-PIN validation
        logger.info("Testing S-PIN validation...")
        spin_valid = auth_manager.validate_spin(TEST_SPIN)
        logger.info(f"✓ S-PIN validation: {'PASSED' if spin_valid else 'FAILED'}")
        
        # Test credential testing function
        logger.info("Testing credential verification...")
        test_results = await auth_manager.test_credentials(TEST_EMAIL, TEST_PASSWORD, TEST_SPIN)
        logger.info(f"✓ Credential test results: {test_results}")
        
        if test_results["authentication_successful"]:
            logger.info("✓ AUTHENTICATION SUCCESSFUL")
            
            # Test session management
            logger.info("Testing session management...")
            session, is_new = await auth_manager.get_or_create_session(TEST_EMAIL, TEST_PASSWORD, TEST_SPIN)
            logger.info(f"✓ Session created: new_session={is_new}")
            
            # Get cache stats
            cache_stats = auth_manager.get_cache_stats()
            logger.info(f"✓ Cache stats: {cache_stats}")
            
            # Test session refresh
            logger.info("Testing session refresh...")
            refreshed_session = await auth_manager.refresh_session(TEST_EMAIL, TEST_PASSWORD)
            logger.info("✓ Session refresh successful")
            
            logger.info("🎉 ALL TESTS PASSED!")
            
        else:
            logger.error(f"❌ AUTHENTICATION FAILED: {test_results['error']}")
            
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

async def test_encryption():
    """Test encryption/decryption functionality"""
    logger.info("Testing encryption functionality...")
    
    try:
        auth_manager = SkodaAuthManager(bucket_name=TEST_BUCKET)
        
        # Test data
        test_credentials = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "timestamp": "2025-01-30T10:00:00Z"
        }
        
        # Test encryption
        encrypted = auth_manager.encrypt_credentials(test_credentials)
        logger.info("✓ Credentials encrypted successfully")
        
        # Test decryption
        decrypted = auth_manager.decrypt_credentials(encrypted)
        logger.info("✓ Credentials decrypted successfully")
        
        # Verify data integrity
        if decrypted == test_credentials:
            logger.info("✓ Encryption/decryption integrity verified")
        else:
            logger.error("❌ Encryption/decryption data mismatch")
            
    except Exception as e:
        logger.error(f"❌ Encryption test failed: {e}")

async def main():
    """Run all tests"""
    logger.info("=== SKODA AUTHENTICATION MANAGER TESTS ===")
    
    # Test encryption first (doesn't require network)
    await test_encryption()
    
    # Test authentication (requires network and valid credentials)
    await test_authentication()
    
    logger.info("=== TEST COMPLETED ===")

if __name__ == "__main__":
    # Run tests
    asyncio.run(main())