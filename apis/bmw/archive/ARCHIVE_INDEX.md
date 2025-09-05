# BMW API Archive Index

This archive contains all legacy implementations, utilities, and documentation that are no longer used in the current stateless BMW API deployment.

**Current Production Deployment:** https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless

## Archive Structure

### /legacy-implementations/
Legacy main implementations and authentication modules that were replaced by the stateless approach:

- **main_bmw_fingerprint.py** - BMW API with fingerprint authentication approach
- **main_bmw_simple_v17.py** - Simple BMW API using bimmer_connected v17
- **main_fingerprint.py** - Fingerprint-based authentication implementation
- **main_fixed.py** - Fixed version addressing various bugs
- **main_fixed_complete.py** - Complete fixed implementation
- **main_original.py** - Original BMW API implementation
- **main_simple.py** - Simplified BMW API version
- **auth_manager.py** - OAuth token management (stateful)
- **auth_manager_original.py** - Original auth manager
- **bmw_auth_fix.py** - Authentication fixes
- **bmw_fingerprint_auth.py** - Fingerprint authentication module
- **fingerprint_patch.py** - Android fingerprint patching
- **remote_services.py** - Remote vehicle services
- **vehicle_manager.py** - Vehicle management module

### /utils/
Utility modules not used in stateless implementation:

- **bmw_android_patch.py** - Android device fingerprint patches
- **bmw_monkey_patch.py** - Runtime patches for bimmer_connected
- **cache_manager.py** - Caching utilities
- **circuit_breaker.py** - Circuit breaker pattern implementation
- **error_handler.py** - Error handling utilities
- **user_agent_manager.py** - User agent rotation

### /deployment-scripts/
Alternative deployment scripts replaced by deploy_stateless.sh:

- **deploy_fingerprint.sh** - Deployment for fingerprint version
- **deploy_simple.sh** - Simple deployment script
- **deploy_now.sh** - Quick deployment script
- **promote.sh** - Promotion between environments
- **Dockerfile** - Docker container definition
- **Dockerfile.fingerprint** - Docker for fingerprint version

### /tests/
Test files for legacy implementations:

- **test_bmw_standalone.py** - Standalone BMW API tests
- **test_bmw_workaround.py** - Workaround implementation tests
- **test_live_api.py** - Live API integration tests
- **test_quota_deployment.py** - Quota handling tests
- **debug_auth.py** - Authentication debugging
- **tests/** - Additional test modules

### /docs/
Legacy documentation:

- **BMW_QUOTA_FIX_README.md** - Documentation about quota fixes
- **GCP_DEPLOYMENT_COMMANDS.md** - GCP deployment instructions
- **README.md** - Original BMW API documentation
- **PRPs/** - Product Requirement Prompts
- **trigger_deploy.txt** - Deployment trigger file
- **.staging-version** - Staging version tracking
- **requirements.txt** - Old requirements file from src/

### /staging/
Staging environment implementations:

- **main.py** - Staging-specific main implementation

### /config/
Configuration files (if any were present)

## Why Archived?

These files were archived because the current stateless implementation (`main_stateless.py`) provides:

1. **Stateless Operation** - No OAuth token storage required
2. **Simplified Architecture** - Single file implementation
3. **Better Security** - Fresh authentication per request
4. **Reduced Complexity** - No token management or caching needed
5. **Production Proven** - Currently running successfully in production

## Restoration

If you need to restore any archived files:
```bash
# Example: Restore a specific file
mv archive/legacy-implementations/main_simple.py ../src/

# Example: Restore entire utils directory
mv archive/utils ../src/
```

## Archive Date
**Archived on:** January 2025
**Archived by:** Claude Code cleanup operation
**Reason:** Simplification to stateless-only deployment