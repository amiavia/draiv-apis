"""
Skoda Connect API Configuration
"""
import os
from pathlib import Path

# Cloud Storage configuration
BUCKET_NAME = os.getenv("SKODA_BUCKET_NAME", "draiv-skoda-tokens")

# Authentication settings
SESSION_TIMEOUT_MINUTES = int(os.getenv("SKODA_SESSION_TIMEOUT", "30"))
MAX_RETRY_ATTEMPTS = int(os.getenv("SKODA_MAX_RETRIES", "3"))

# Security settings
ENCRYPTION_KEY = os.getenv("SKODA_ENCRYPTION_KEY")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "draiv-apis")

# Local storage paths
LOCAL_STORAGE_PATH = Path(os.getenv("SKODA_LOCAL_STORAGE", "/tmp/skoda"))
LOCAL_STORAGE_PATH.mkdir(exist_ok=True)

# API settings  
API_TIMEOUT_SECONDS = int(os.getenv("SKODA_API_TIMEOUT", "30"))
API_RATE_LIMIT_REQUESTS = int(os.getenv("SKODA_RATE_LIMIT", "60"))
API_RATE_LIMIT_WINDOW = int(os.getenv("SKODA_RATE_WINDOW", "60"))

# Logging configuration
LOG_LEVEL = os.getenv("SKODA_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Test credentials (for development only)
DEV_TEST_EMAIL = os.getenv("SKODA_DEV_EMAIL")
DEV_TEST_PASSWORD = os.getenv("SKODA_DEV_PASSWORD") 
DEV_TEST_SPIN = os.getenv("SKODA_DEV_SPIN")

def get_auth_config() -> dict:
    """Get authentication configuration"""
    return {
        "bucket_name": BUCKET_NAME,
        "encryption_key": ENCRYPTION_KEY,
        "session_timeout_minutes": SESSION_TIMEOUT_MINUTES,
        "max_retry_attempts": MAX_RETRY_ATTEMPTS
    }

def get_api_config() -> dict:
    """Get API configuration"""
    return {
        "timeout_seconds": API_TIMEOUT_SECONDS,
        "rate_limit_requests": API_RATE_LIMIT_REQUESTS,
        "rate_limit_window": API_RATE_LIMIT_WINDOW
    }