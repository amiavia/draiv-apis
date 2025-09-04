"""
BMW Authentication Manager
Handles OAuth token management and authentication with BMW Connected Drive
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from google.cloud import storage
from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import Regions
from bimmer_connected.cli import load_oauth_store_from_file, store_oauth_store_to_file

from utils.error_handler import AuthenticationError, BMWAPIError, QuotaLimitError
from utils.user_agent_manager import user_agent_manager

logger = logging.getLogger(__name__)

class BMWAuthManager:
    """Manages BMW Connected Drive authentication and OAuth tokens"""
    
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.oauth_filename = "bmw_oauth.json"
        self.local_token_path = Path("/tmp") / self.oauth_filename
        self.storage_client = storage.Client()
        self.token_cache: Dict[str, Dict[str, Any]] = {}
        self.token_ttl = timedelta(hours=24)  # Token validity period
        
    async def authenticate(
        self, 
        email: str, 
        password: str, 
        hcaptcha_token: Optional[str] = None
    ) -> MyBMWAccount:
        """
        Authenticate with BMW Connected Drive
        
        Args:
            email: BMW account email
            password: BMW account password
            hcaptcha_token: Optional hCaptcha token for first-time auth
            
        Returns:
            Authenticated MyBMWAccount instance
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Check in-memory cache first
            cache_key = f"{email}:{password}"
            if cache_key in self.token_cache:
                cached = self.token_cache[cache_key]
                if datetime.now() < cached["expires"]:
                    logger.info(f"Using cached authentication for {email}")
                    return cached["account"]
            
            # Try to load existing OAuth token from storage
            has_token = await self._download_oauth_token(email)
            
            # Get dynamic user agent headers to avoid quota limits
            user_agent_headers = user_agent_manager.get_headers()
            
            if has_token:
                # Re-authenticate using stored token
                logger.info(f"Re-authenticating {email} using stored OAuth token with dynamic user agent")
                account = MyBMWAccount(email, password, Regions.REST_OF_WORLD)
                load_oauth_store_from_file(self.local_token_path, account)
                
                # Apply dynamic user agent to avoid quota limits
                if hasattr(account, '_session') and account._session:
                    account._session.headers.update(user_agent_headers)
                
            elif hcaptcha_token:
                # First-time authentication with hCaptcha
                logger.info(f"First-time authentication for {email} with hCaptcha and dynamic user agent")
                account = MyBMWAccount(
                    email, 
                    password, 
                    Regions.REST_OF_WORLD,
                    hcaptcha_token=hcaptcha_token
                )
                
                # Apply dynamic user agent to avoid quota limits
                if hasattr(account, '_session') and account._session:
                    account._session.headers.update(user_agent_headers)
                
            else:
                raise AuthenticationError(
                    "Missing hCaptcha token for first-time authentication. "
                    "Please provide 'hcaptcha' field in request."
                )
            
            # Verify authentication by fetching vehicles
            await account.get_vehicles()
            
            # Store OAuth token for future use
            await self._store_oauth_token(account, email)
            
            # Cache the authenticated account
            self.token_cache[cache_key] = {
                "account": account,
                "expires": datetime.now() + self.token_ttl
            }
            
            logger.info(f"Successfully authenticated {email}")
            return account
            
        except Exception as e:
            logger.error(f"Authentication failed for {email}: {e}")
            
            # Check if this is a quota limit error (403 with quota message)
            quota_error = self._parse_quota_error(str(e))
            if quota_error:
                logger.warning(f"BMW API quota limit exceeded for {email}: {quota_error['message']}")
                raise QuotaLimitError(quota_error['message'], quota_error.get('retry_after'))
            
            # Handle other authentication errors
            if "unauthorized" in str(e).lower():
                raise AuthenticationError(f"Invalid credentials for {email}")
            elif "hcaptcha" in str(e).lower():
                raise AuthenticationError(
                    "hCaptcha verification failed. Please try again with a valid token."
                )
            else:
                raise BMWAPIError(f"Authentication failed: {str(e)}")
    
    def _parse_quota_error(self, error_message: str) -> Optional[Dict[str, Any]]:
        """
        Parse BMW API quota error message to extract retry timing
        
        Args:
            error_message: Error message from BMW API
            
        Returns:
            Dictionary with quota error details or None if not a quota error
        """
        import re
        
        # Check for common quota error patterns
        quota_indicators = [
            "out of call volume quota",
            "quota will be replenished",
            "quota limit exceeded",
            "too many requests"
        ]
        
        error_lower = error_message.lower()
        if not any(indicator in error_lower for indicator in quota_indicators):
            return None
        
        # Extract retry time if present (format: "Quota will be replenished in 01:20:28")
        time_pattern = r'(?:replenished in|retry in|wait|after)\s*(\d{1,2}):(\d{2}):(\d{2})'
        time_match = re.search(time_pattern, error_lower)
        
        retry_after = None
        if time_match:
            hours, minutes, seconds = map(int, time_match.groups())
            retry_after = hours * 3600 + minutes * 60 + seconds
        else:
            # Look for simpler time formats like "60 seconds" or "30 minutes"
            simple_time = re.search(r'(\d+)\s*(second|minute|hour)s?', error_lower)
            if simple_time:
                value, unit = simple_time.groups()
                value = int(value)
                if unit.startswith('minute'):
                    retry_after = value * 60
                elif unit.startswith('hour'):
                    retry_after = value * 3600
                else:  # seconds
                    retry_after = value
        
        return {
            'message': f"BMW API quota limit exceeded. {error_message}",
            'retry_after': retry_after
        }
    
    async def _download_oauth_token(self, email: str) -> bool:
        """
        Download OAuth token from Google Cloud Storage
        
        Args:
            email: User email for token identification
            
        Returns:
            True if token exists and was downloaded, False otherwise
        """
        try:
            # Use email-specific token file
            blob_name = f"oauth_tokens/{email.replace('@', '_at_')}_oauth.json"
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            
            if blob.exists():
                blob.download_to_filename(str(self.local_token_path))
                logger.info(f"OAuth token downloaded for {email}")
                return True
            
            # Try legacy token location as fallback
            legacy_blob = bucket.blob(self.oauth_filename)
            if legacy_blob.exists():
                legacy_blob.download_to_filename(str(self.local_token_path))
                logger.info(f"Legacy OAuth token downloaded for {email}")
                return True
                
            logger.info(f"No existing OAuth token found for {email}")
            return False
            
        except Exception as e:
            logger.warning(f"Failed to download OAuth token: {e}")
            return False
    
    async def _store_oauth_token(self, account: MyBMWAccount, email: str) -> None:
        """
        Store OAuth token to Google Cloud Storage
        
        Args:
            account: Authenticated BMW account
            email: User email for token identification
        """
        try:
            # Store token locally first
            store_oauth_store_to_file(self.local_token_path, account)
            
            # Upload to cloud storage with email-specific path
            blob_name = f"oauth_tokens/{email.replace('@', '_at_')}_oauth.json"
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            
            blob.upload_from_filename(str(self.local_token_path))
            logger.info(f"OAuth token uploaded for {email}")
            
            # Clean up local file
            if self.local_token_path.exists():
                self.local_token_path.unlink()
                
        except Exception as e:
            logger.error(f"Failed to store OAuth token: {e}")
            # Don't fail the request if token storage fails
    
    def clear_cache(self, email: Optional[str] = None) -> None:
        """
        Clear authentication cache
        
        Args:
            email: Specific email to clear, or None to clear all
        """
        if email:
            # Clear specific user's cache
            keys_to_remove = [k for k in self.token_cache if k.startswith(f"{email}:")]
            for key in keys_to_remove:
                del self.token_cache[key]
            logger.info(f"Cleared cache for {email}")
        else:
            # Clear all cache
            self.token_cache.clear()
            logger.info("Cleared all authentication cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the authentication cache"""
        return {
            "cached_accounts": len(self.token_cache),
            "cache_entries": list(self.token_cache.keys()),
            "oldest_entry": min(
                (c["expires"] for c in self.token_cache.values()),
                default=None
            )
        }