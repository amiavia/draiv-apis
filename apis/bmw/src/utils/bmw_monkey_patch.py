"""
BMW Monkey Patch for bimmer_connected Library
==============================================
This module monkey-patches the bimmer_connected library to fix the BMW API quota issue.
It implements the fix from PR #743 which generates dynamic x-user-agent headers.

This MUST be imported BEFORE importing any bimmer_connected modules!
"""

import hashlib
import platform
import random
import string
import uuid
from typing import Optional

def apply_monkey_patch():
    """
    Apply monkey patches to bimmer_connected to fix quota issues.
    This must be called before importing MyBMWAccount.
    """
    print("🐒 Applying BMW monkey patch for dynamic user agent...")
    
    # We need to patch the module before it's imported
    import sys
    
    # Create a mock module for the constants
    class MockConstants:
        """Mock constants module with our custom x-user-agent"""
        
        @staticmethod
        def get_x_user_agent():
            """Generate dynamic x-user-agent to avoid BMW quota blocks"""
            # Generate a stable but unique identifier for this deployment
            system_id = _get_system_uuid()
            build_string = _generate_build_string(system_id)
            
            # Format matching BMW's expected pattern from PR #743
            # Example: "android(LP1A.123456.789);bmw;2.20.3;row"
            x_user_agent = f"android({build_string});bmw;2.20.3;row"
            
            print(f"🔧 Generated x-user-agent: {x_user_agent}")
            return x_user_agent
    
    # Patch the bimmer_connected modules
    try:
        # If bimmer_connected.const is already imported, patch it
        if 'bimmer_connected.const' in sys.modules:
            import bimmer_connected.const as const
            original_x_user_agent = getattr(const, 'X_USER_AGENT', None)
            const.X_USER_AGENT = MockConstants.get_x_user_agent()
            print(f"✅ Patched existing bimmer_connected.const (was: {original_x_user_agent})")
        
        # Patch the client module if it exists
        if 'bimmer_connected.api.client' in sys.modules:
            import bimmer_connected.api.client as client
            
            # Override the generate_default_header method
            original_generate = getattr(client.MyBMWClient, 'generate_default_header', None)
            
            def patched_generate_header(self, *args, **kwargs):
                """Patched header generator with dynamic user agent"""
                return MockConstants.get_x_user_agent()
            
            client.MyBMWClient.generate_default_header = patched_generate_header
            print("✅ Patched bimmer_connected.api.client.generate_default_header")
        
        # Patch authentication module if it exists
        if 'bimmer_connected.api.authentication' in sys.modules:
            import bimmer_connected.api.authentication as auth
            
            # Find and patch any x-user-agent references
            if hasattr(auth, 'MyBMWAuthentication'):
                auth_class = auth.MyBMWAuthentication
                
                # Wrap the init to set our headers
                original_init = auth_class.__init__
                
                def patched_init(self, *args, **kwargs):
                    result = original_init(self, *args, **kwargs)
                    # Set our custom headers
                    if hasattr(self, 'session') and self.session:
                        self.session.headers['x-user-agent'] = MockConstants.get_x_user_agent()
                        self.session.headers['user-agent'] = MockConstants.get_x_user_agent()
                    return result
                
                auth_class.__init__ = patched_init
                print("✅ Patched bimmer_connected.api.authentication")
        
        # Pre-emptive patch: Set up import hooks for modules not yet imported
        original_import = __builtins__.__import__
        
        def custom_import(name, *args, **kwargs):
            """Custom import that patches bimmer_connected modules"""
            module = original_import(name, *args, **kwargs)
            
            # Patch constants when imported
            if name == 'bimmer_connected.const':
                if hasattr(module, 'X_USER_AGENT'):
                    module.X_USER_AGENT = MockConstants.get_x_user_agent()
                    print(f"✅ Patched bimmer_connected.const on import")
            
            # Patch client when imported
            elif name == 'bimmer_connected.api.client':
                if hasattr(module, 'MyBMWClient'):
                    module.MyBMWClient.generate_default_header = lambda self: MockConstants.get_x_user_agent()
                    print(f"✅ Patched bimmer_connected.api.client on import")
            
            return module
        
        # Replace the import function
        __builtins__.__import__ = custom_import
        print("✅ Import hooks installed for future bimmer_connected imports")
        
    except Exception as e:
        print(f"⚠️ Error applying monkey patch: {e}")
        # Continue anyway - partial patching is better than none


def _get_system_uuid() -> str:
    """
    Get a stable UUID for this system/deployment.
    This ensures the same UUID is used consistently.
    """
    # Try to get a stable identifier
    try:
        # Use MAC address as a stable identifier
        mac = uuid.getnode()
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bmw-{mac}"))
    except:
        # Fallback to a random but stable UUID (stored in memory)
        if not hasattr(_get_system_uuid, '_cached_uuid'):
            _get_system_uuid._cached_uuid = str(uuid.uuid4())
        return _get_system_uuid._cached_uuid


def _generate_build_string(system_id: str) -> str:
    """
    Generate a build string that looks like Android build numbers.
    Format: LP1A.123456.789 (based on PR #743 examples)
    
    Args:
        system_id: System UUID for generating stable hash
        
    Returns:
        Build string in Android format
    """
    # Create a hash from the system ID for stability
    hash_obj = hashlib.sha256(system_id.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Generate components from the hash
    # Prefix: 2-4 letters (like LP1A, RP1A, etc.)
    prefix_chars = ''.join([
        hash_hex[0].upper() if hash_hex[0].isalpha() else 'L',
        hash_hex[1].upper() if hash_hex[1].isalpha() else 'P',
        '1',
        hash_hex[2].upper() if hash_hex[2].isalpha() else 'A'
    ])
    
    # Middle number: 6 digits
    middle_num = int(hash_hex[3:9], 16) % 1000000
    middle_str = f"{middle_num:06d}"
    
    # End number: 3 digits
    end_num = int(hash_hex[9:12], 16) % 1000
    end_str = f"{end_num:03d}"
    
    build_string = f"{prefix_chars}.{middle_str}.{end_str}"
    return build_string


# Auto-apply patch when module is imported
apply_monkey_patch()