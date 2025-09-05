"""
BMW Monkey Patch for bimmer_connected Library
==============================================
This module monkey-patches the bimmer_connected library to fix the BMW API quota issue.
It implements the fix from PR #743 which generates dynamic x-user-agent headers.

UPDATED: Now uses the exact PR #743 algorithm with container awareness for unique fingerprints.

This MUST be imported BEFORE importing any bimmer_connected modules!
"""

import hashlib
import platform
import random
import string
import uuid
import os
import re
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
            """Generate dynamic x-user-agent using PR #743 algorithm"""
            # Get stable system UUID with container awareness
            system_uuid = _get_system_uuid_pr743()
            build_string = _generate_build_string_pr743(system_uuid)
            
            # Format matching BMW's expected pattern from PR #743
            # Example: "android(LP1A.123456.789);bmw;2.20.3;row"
            x_user_agent = f"android({build_string});bmw;2.20.3;row"
            
            print(f"🔧 PR #743 x-user-agent: {x_user_agent}")
            print(f"🔧 System UUID: {system_uuid}")
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


def _get_container_id() -> str:
    """Get container ID for additional uniqueness"""
    try:
        with open('/proc/self/cgroup', 'r') as f:
            for line in f:
                if 'docker' in line or 'containerd' in line:
                    return line.split('/')[-1].strip()[:12]
    except:
        pass
    return 'default'


def _get_system_uuid_pr743() -> str:
    """
    Get stable system UUID for Cloud Functions/Run container using PR #743 approach.
    This ensures consistent fingerprint across container lifecycle while being unique per deployment.
    """
    # For Cloud Functions/Run, use service and revision info for stability
    service_name = os.environ.get('K_SERVICE', 'bmw-api')
    revision = os.environ.get('K_REVISION', 'default') 
    region = os.environ.get('FUNCTION_REGION', 'europe-west6')
    
    # Get container ID for additional uniqueness
    container_id = _get_container_id()
    
    # Create stable identifier for this deployment
    stable_id = f"{service_name}-{revision}-{region}-{container_id}"
    
    # Try to get actual system UUID as fallback
    try:
        system = platform.system().lower()
        if system == 'linux':
            # Try machine-id first (most stable on Linux)
            try:
                with open('/etc/machine-id', 'r') as f:
                    machine_id = f.read().strip()
                if machine_id:
                    return f"{machine_id}-{service_name}"
            except:
                pass
                
        # Fallback to MAC address
        mac_address = uuid.getnode()
        if mac_address:
            return f"{mac_address}-{service_name}"
            
    except:
        pass
        
    # Final fallback: use our stable deployment ID
    return stable_id


def _generate_build_string_pr743(system_uuid: str) -> str:
    """
    Generate BMW-compatible build string using exact PR #743 algorithm.
    This replicates the bimmer_connected PR #743 implementation.
    
    Args:
        system_uuid: System UUID for generating stable hash
        
    Returns:
        Build string in format: LP1A.123456.789
    """
    # Use SHA1 (BMW standard, not SHA256) as per PR #743
    digest = hashlib.sha1(system_uuid.encode()).hexdigest().upper()
    
    # Extract numeric digits from hash (PR #743 method)
    numeric_chars = re.findall(r'\d', digest)
    if len(numeric_chars) < 9:
        # Pad with zeros if not enough digits
        numeric_chars.extend(['0'] * (9 - len(numeric_chars)))
    
    # Create build string components
    middle_part = ''.join(numeric_chars[:6])
    build_part = ''.join(numeric_chars[6:9])
    
    # Platform-specific prefix (PR #743 approach)
    system = platform.system().lower()
    if system == 'linux':
        prefix = 'LP1A'  # Linux Platform 1A
    elif system == 'darwin':  # macOS
        prefix = 'DP1A'  # Darwin Platform 1A
    elif system == 'windows':
        prefix = 'WP1A'  # Windows Platform 1A
    else:
        prefix = 'AP1A'  # Android Platform 1A (default)
    
    build_string = f"{prefix}.{middle_part}.{build_part}"
    return build_string


# Auto-apply patch when module is imported
apply_monkey_patch()