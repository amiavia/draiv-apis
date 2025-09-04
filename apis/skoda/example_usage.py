#!/usr/bin/env python3
"""
Example usage of Skoda Authentication Manager
Demonstrates the main authentication and session management features
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from auth_manager import SkodaAuthManager
from config import get_auth_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Demonstrate auth manager usage"""
    
    # Initialize auth manager
    config = get_auth_config()
    auth_manager = SkodaAuthManager(
        bucket_name=config["bucket_name"],
        encryption_key=config["encryption_key"]
    )
    
    # Example credentials (replace with actual credentials)
    email = "your_email@example.com"
    password = "your_password"
    spin = "1234"  # Your 4-digit S-PIN
    
    try:
        logger.info("=== SKODA AUTH MANAGER EXAMPLE ===")
        
        # 1. Validate credentials format
        logger.info("1. Validating credential format...")
        if not auth_manager.validate_credentials(email, password):
            logger.error("Invalid credential format")
            return
        
        if spin and not auth_manager.validate_spin(spin):
            logger.error("Invalid S-PIN format")
            return
        
        logger.info("✓ Credentials format valid")
        
        # 2. Test credentials (optional - doesn't cache)
        logger.info("2. Testing credentials...")
        test_results = await auth_manager.test_credentials(email, password, spin)
        
        if not test_results["authentication_successful"]:
            logger.error(f"Credential test failed: {test_results['error']}")
            return
        
        logger.info(f"✓ Credentials valid - User: {test_results.get('user_info', {}).get('name', 'Unknown')}")
        
        # 3. Get or create session
        logger.info("3. Getting/creating session...")
        session, is_new_session = await auth_manager.get_or_create_session(email, password, spin)
        logger.info(f"✓ Session ready - New session: {is_new_session}")
        
        # 4. Use session for Skoda operations
        logger.info("4. Using session...")
        try:
            user_info = await session.get_info()
            logger.info(f"✓ User info retrieved: {user_info.get('name', 'Unknown')}")
            
            # Get vehicles if available
            vehicles = await session.get_vehicles()
            logger.info(f"✓ Found {len(vehicles)} vehicle(s)")
            
        except Exception as e:
            logger.warning(f"Session operation error: {e}")
        
        # 5. Check cache stats
        logger.info("5. Cache statistics...")
        cache_stats = auth_manager.get_cache_stats()
        logger.info(f"✓ Cache stats: {cache_stats}")
        
        # 6. Demonstrate session refresh
        logger.info("6. Refreshing session...")
        refreshed_session = await auth_manager.refresh_session(email, password)
        logger.info("✓ Session refreshed successfully")
        
        # 7. Clear specific user cache (optional)
        logger.info("7. Clearing user cache...")
        auth_manager.clear_cache(email)
        logger.info("✓ User cache cleared")
        
        logger.info("=== EXAMPLE COMPLETED SUCCESSFULLY ===")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        import traceback
        traceback.print_exc()

async def encryption_example():
    """Demonstrate encryption functionality"""
    logger.info("=== ENCRYPTION EXAMPLE ===")
    
    try:
        config = get_auth_config()
        auth_manager = SkodaAuthManager(
            bucket_name=config["bucket_name"],
            encryption_key=config["encryption_key"]
        )
        
        # Example sensitive data
        sensitive_data = {
            "email": "user@example.com",
            "password": "secret_password",
            "api_key": "sensitive_api_key",
            "timestamp": "2025-01-30T10:00:00Z"
        }
        
        # Encrypt data
        logger.info("Encrypting sensitive data...")
        encrypted = auth_manager.encrypt_credentials(sensitive_data)
        logger.info(f"✓ Data encrypted (length: {len(encrypted)} chars)")
        
        # Decrypt data
        logger.info("Decrypting data...")
        decrypted = auth_manager.decrypt_credentials(encrypted)
        logger.info("✓ Data decrypted successfully")
        
        # Verify integrity
        if decrypted == sensitive_data:
            logger.info("✓ Encryption/decryption integrity verified")
        else:
            logger.error("❌ Data integrity check failed")
        
        logger.info("=== ENCRYPTION EXAMPLE COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Encryption example failed: {e}")

if __name__ == "__main__":
    print("Skoda Authentication Manager - Example Usage")
    print("=" * 50)
    print()
    print("IMPORTANT: Update the credentials in this script before running!")
    print("- Replace email, password, and spin with your actual Skoda Connect credentials")
    print("- Ensure you have proper Google Cloud credentials configured")
    print("- Set environment variables as needed (see config.py)")
    print()
    
    # Run encryption example first (no network required)
    asyncio.run(encryption_example())
    
    print()
    print("To run the full authentication example:")
    print("1. Update credentials in main() function")
    print("2. Uncomment the line below")
    print()
    
    # Uncomment to run full example with real credentials:
    # asyncio.run(main())