"""
Minimal BMW Fingerprint Patch for Quota Isolation
==================================================
This module applies the PR #743 fingerprint algorithm to generate
unique x-user-agent headers for each deployment, preventing quota sharing.

MUST be imported BEFORE any bimmer_connected modules!
"""

import hashlib
import platform
import os
import re

def apply_fingerprint_patch():
    """Apply fingerprint patch to bimmer_connected for quota isolation"""
    print("🔧 Applying BMW fingerprint patch for quota isolation...")
    
    import sys
    
    class FingerprintGenerator:
        @staticmethod
        def get_x_user_agent():
            """Generate unique x-user-agent using PR #743 algorithm"""
            system_uuid = _get_system_uuid()
            build_string = _generate_build_string(system_uuid)
            x_user_agent = f"android({build_string});bmw;2.20.3;row"
            print(f"  → Generated x-user-agent: {x_user_agent}")
            return x_user_agent
    
    # Pre-emptive import hook for bimmer_connected modules
    original_import = __builtins__.__import__
    
    def custom_import(name, *args, **kwargs):
        module = original_import(name, *args, **kwargs)
        
        # Patch constants module when imported
        if name == 'bimmer_connected.const':
            if hasattr(module, 'X_USER_AGENT'):
                module.X_USER_AGENT = FingerprintGenerator.get_x_user_agent()
                print("  ✅ Patched bimmer_connected.const.X_USER_AGENT")
        
        return module
    
    __builtins__.__import__ = custom_import
    print("  ✅ Fingerprint patch installed successfully")


def _get_system_uuid():
    """Get stable system UUID for this deployment"""
    # Use Cloud Function/Run environment variables for uniqueness
    service_name = os.environ.get('K_SERVICE', 'bmw-api')
    revision = os.environ.get('K_REVISION', 'default')
    region = os.environ.get('FUNCTION_REGION', 'europe-west6')
    
    # Try to get container ID for additional uniqueness
    container_id = 'default'
    try:
        with open('/proc/self/cgroup', 'r') as f:
            for line in f:
                if 'docker' in line or 'containerd' in line:
                    container_id = line.split('/')[-1].strip()[:12]
                    break
    except:
        pass
    
    # Create stable deployment identifier
    deployment_id = f"{service_name}-{revision}-{region}-{container_id}"
    
    # Try to get machine ID as additional entropy
    try:
        with open('/etc/machine-id', 'r') as f:
            machine_id = f.read().strip()
            if machine_id:
                deployment_id = f"{machine_id}-{deployment_id}"
    except:
        pass
    
    return deployment_id


def _generate_build_string(system_uuid):
    """Generate Android-style build string using PR #743 algorithm"""
    # Use SHA1 as per PR #743 (not SHA256)
    digest = hashlib.sha1(system_uuid.encode()).hexdigest().upper()
    
    # Extract numeric digits from hash
    numeric_chars = re.findall(r'\d', digest)
    if len(numeric_chars) < 9:
        numeric_chars.extend(['0'] * (9 - len(numeric_chars)))
    
    # Build components
    middle_part = ''.join(numeric_chars[:6])
    build_part = ''.join(numeric_chars[6:9])
    
    # Platform prefix
    system = platform.system().lower()
    if system == 'linux':
        prefix = 'LP1A'
    elif system == 'darwin':
        prefix = 'DP1A'
    elif system == 'windows':
        prefix = 'WP1A'
    else:
        prefix = 'AP1A'
    
    return f"{prefix}.{middle_part}.{build_part}"