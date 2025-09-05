"""
BMW Android Patch - Docker Workaround Approach for Cloud Functions
================================================================
Implements the proven Docker workaround but adapted for Cloud Functions.
Patches bimmer_connected X_USER_AGENT with dynamic PR #743 fingerprints.

Based on the working Docker script approach but enhanced with:
- Dynamic fingerprint generation (not static HAN-ua-20250902)
- Cloud Function compatibility
- PR #743 algorithm implementation
"""

import os
import platform
import hashlib
import uuid
import re
import importlib
import inspect
from typing import Optional


def _get_system_uuid_pr743() -> str:
    """
    Get system UUID exactly as PR #743 does, adapted for Cloud Functions
    """
    # For Cloud Functions, create stable ID based on function metadata
    function_name = os.environ.get('K_SERVICE', 'bmw_api_simple')
    function_revision = os.environ.get('K_REVISION', 'default')
    region = os.environ.get('FUNCTION_REGION', 'europe-west6')
    
    # Get container ID for additional uniqueness
    container_id = 'default'
    try:
        with open('/proc/self/cgroup', 'r') as f:
            for line in f:
                if 'docker' in line or 'containerd' in line:
                    container_id = line.split('/')[-1].strip()[:12]
                    break
    except:
        pass
    
    # Create stable identifier for this deployment
    stable_id = f"{function_name}-{function_revision}-{region}-{container_id}"
    
    # Try to get actual system UUID as fallback (PR #743 method)
    try:
        system = platform.system().lower()
        if system == 'linux':
            # Try machine-id first (most stable on Linux)
            try:
                with open('/etc/machine-id', 'r') as f:
                    machine_id = f.read().strip()
                if machine_id:
                    return f"{machine_id}-{function_name}"
            except:
                pass
                
        # Fallback to MAC address
        mac_address = uuid.getnode()
        if mac_address:
            return f"{mac_address}-{function_name}"
            
    except:
        pass
        
    # Final fallback: use our stable deployment ID
    return stable_id


def _generate_build_string_pr743(system_uuid: str) -> str:
    """
    Generate BMW-compatible build string using exact PR #743 algorithm
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


def generate_pr743_fingerprint() -> str:
    """
    Generate dynamic Android fingerprint using PR #743 algorithm
    
    Returns:
        Android user agent string like: android(LP1A.123456.789);bmw;2.20.3;row
    """
    system_uuid = _get_system_uuid_pr743()
    build_string = _generate_build_string_pr743(system_uuid)
    fingerprint = f"android({build_string});bmw;2.20.3;row"
    return fingerprint


def apply_android_patch():
    """
    Apply Android patch using Docker workaround approach
    
    This replicates the Docker script but:
    1. Finds bimmer_connected/const.py using Python inspection
    2. Generates dynamic PR #743 fingerprint (not static HAN-ua-20250902)
    3. Patches X_USER_AGENT constant in memory
    4. Works in Cloud Functions environment
    """
    print("🐒 Applying BMW Android patch (Docker workaround approach)...")
    
    try:
        # Step 1: Find bimmer_connected const.py (like Docker script does)
        print("📍 Step 1: Locating bimmer_connected const.py...")
        
        try:
            m = importlib.import_module("bimmer_connected")
            const_file = os.path.join(os.path.dirname(inspect.getfile(m)), "const.py")
            print(f"🔍 Found const.py at: {const_file}")
        except Exception as e:
            print(f"⚠️ Could not locate const.py via inspection: {e}")
            # Fallback: try to import const directly
        
        # Step 2: Generate dynamic PR #743 fingerprint (Docker uses static HAN-ua-20250902)
        print("🔧 Step 2: Generating dynamic PR #743 fingerprint...")
        fingerprint = generate_pr743_fingerprint()
        system_uuid = _get_system_uuid_pr743()
        print(f"🔧 System UUID: {system_uuid}")
        print(f"🔧 Generated fingerprint: {fingerprint}")
        
        # Step 3: Patch X_USER_AGENT constant (like Docker sed command)
        print("🔄 Step 3: Patching X_USER_AGENT constant...")
        
        try:
            import bimmer_connected.const as const
            original_x_user_agent = getattr(const, 'X_USER_AGENT', 'not_found')
            print(f"📋 Original X_USER_AGENT: {original_x_user_agent}")
            
            # Apply the patch (equivalent to Docker's sed command)
            const.X_USER_AGENT = fingerprint
            print(f"✅ Patched X_USER_AGENT: {fingerprint}")
            
            # Verify the change (like Docker's grep command)
            current_x_user_agent = getattr(const, 'X_USER_AGENT', 'not_found')
            print(f"🔍 Verification - Current X_USER_AGENT: {current_x_user_agent}")
            
            if current_x_user_agent == fingerprint:
                print("✅ Android patch applied successfully!")
                print("🎯 BMW will now see this deployment as unique Android device")
                return True
            else:
                print("❌ Patch verification failed!")
                return False
                
        except ImportError as e:
            print(f"⚠️ Could not import bimmer_connected.const: {e}")
            print("ℹ️ This might be expected if bimmer_connected is not yet installed")
            return False
            
    except Exception as e:
        print(f"❌ Error applying Android patch: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_patch_info() -> dict:
    """
    Get information about the current patch status
    
    Returns:
        Dict with patch information
    """
    try:
        fingerprint = generate_pr743_fingerprint()
        system_uuid = _get_system_uuid_pr743()
        
        # Try to get current X_USER_AGENT from bimmer_connected
        current_agent = "not_available"
        try:
            import bimmer_connected.const as const
            current_agent = getattr(const, 'X_USER_AGENT', 'not_found')
        except:
            pass
        
        return {
            "generated_fingerprint": fingerprint,
            "system_uuid": system_uuid,
            "current_x_user_agent": current_agent,
            "patch_active": current_agent == fingerprint,
            "algorithm": "PR_743_with_docker_workaround"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "algorithm": "PR_743_with_docker_workaround"
        }


# Auto-apply patch when module is imported (like the Docker approach)
if __name__ != "__main__":
    # Only auto-apply in production, not during direct execution
    apply_android_patch()

# For testing/debugging
if __name__ == "__main__":
    print("BMW Android Patch - Testing Mode")
    print("=" * 50)
    
    # Test fingerprint generation
    fingerprint = generate_pr743_fingerprint()
    print(f"Generated fingerprint: {fingerprint}")
    
    # Test patch info
    info = get_patch_info()
    print(f"Patch info: {info}")
    
    # Test patch application
    success = apply_android_patch()
    print(f"Patch application: {'✅ Success' if success else '❌ Failed'}")