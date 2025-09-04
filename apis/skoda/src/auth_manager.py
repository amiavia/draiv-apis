"""
Skoda Connect Authentication Manager
Handles OAuth token management and authentication with Skoda Connect API
"""
import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from google.cloud import storage
try:
    from myskoda import MySkoda
    from myskoda.rest_api import RestApi
except ImportError:
    logging.error("MySkoda library not installed. Install with: pip install myskoda")
    raise

from .error_handler import AuthenticationError, SkodaAPIError
from utils.cache_manager import SkodaCacheManager

logger = logging.getLogger(__name__)

class SkodaAuthManager:
    """
    Manages Skoda Connect authentication and session handling
    
    Provides secure authentication with token caching and automatic renewal.
    Integrates with Google Cloud Storage for persistent token storage.
    """
    
    def __init__(
        self, 
        bucket_name: str,
        cache_manager: Optional[SkodaCacheManager] = None
    ):
        """
        Initialize Skoda authentication manager
        
        Args:
            bucket_name: Google Cloud Storage bucket for token storage
            cache_manager: Optional cache manager for session caching
        """
        self.bucket_name = bucket_name
        self.cache_manager = cache_manager or SkodaCacheManager()
        self.oauth_filename = "skoda_oauth.json"
        self.local_token_path = Path("/tmp") / self.oauth_filename
        self.storage_client = storage.Client()
        self.session_cache: Dict[str, Dict[str, Any]] = {}
        self.session_ttl = timedelta(hours=12)  # Session validity period
        
    async def authenticate(
        self, 
        username: str, 
        password: str,
        force_refresh: bool = False
    ) -> MySkoda:
        """
        Authenticate with Skoda Connect and return MySkoda instance
        
        Args:
            username: Skoda Connect username/email
            password: Skoda Connect password
            force_refresh: Force new authentication even if cached session exists
            
        Returns:
            Authenticated MySkoda instance
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Check in-memory cache first
            cache_key = f"{username}:{password}"
            if not force_refresh and cache_key in self.session_cache:
                cached = self.session_cache[cache_key]
                if datetime.now() < cached["expires"]:
                    logger.info(f"Using cached authentication for {username}")
                    return cached["myskoda"]
            
            # Check persistent cache
            session_cache_key = f"auth:session:{username}"
            if not force_refresh:
                cached_session = await self.cache_manager.get(session_cache_key)
                if cached_session:
                    logger.info(f"Using cached session for {username}")
                    myskoda = await self._restore_session(cached_session)
                    if myskoda:
                        return myskoda
            
            # Perform fresh authentication
            logger.info(f"Performing fresh authentication for {username}")
            myskoda = await self._fresh_authentication(username, password)
            
            # Cache the authenticated session
            await self._cache_session(username, myskoda, cache_key, session_cache_key)
            
            logger.info(f"Successfully authenticated with Skoda Connect for {username}")
            return myskoda
            
        except Exception as e:
            logger.error(f"Authentication failed for {username}: {e}")
            if "unauthorized" in str(e).lower() or "invalid" in str(e).lower():
                raise AuthenticationError(f"Invalid credentials for {username}")
            elif "blocked" in str(e).lower() or "captcha" in str(e).lower():
                raise AuthenticationError(f"Account blocked or CAPTCHA required for {username}")
            else:
                raise SkodaAPIError(f"Authentication failed: {str(e)}")
    
    async def _fresh_authentication(self, username: str, password: str) -> MySkoda:
        """Perform fresh authentication with Skoda Connect"""
        try:
            # Create MySkoda instance
            myskoda = MySkoda()
            
            # Attempt authentication with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await myskoda.connect(username, password)
                    
                    # Verify authentication by getting vehicles
                    await myskoda.get_vehicles()
                    
                    logger.info(f"Authentication successful on attempt {attempt + 1}")
                    return myskoda
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Authentication attempt {attempt + 1} failed: {e}. Retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise e
            
            raise AuthenticationError("Authentication failed after all retries")
            
        except Exception as e:
            logger.error(f"Fresh authentication failed: {e}")
            raise AuthenticationError(f"Failed to authenticate: {str(e)}")
    
    async def _restore_session(self, session_data: Dict[str, Any]) -> Optional[MySkoda]:
        """Attempt to restore MySkoda session from cached data"""
        try:
            # This is a placeholder - actual implementation would depend on
            # MySkoda library's session restoration capabilities
            logger.info("Attempting to restore cached session")
            
            # Create new MySkoda instance
            myskoda = MySkoda()
            
            # If MySkoda supports session restoration, implement here
            # For now, return None to force fresh authentication
            return None
            
        except Exception as e:
            logger.warning(f"Failed to restore session: {e}")
            return None
    
    async def _cache_session(
        self, 
        username: str, 
        myskoda: MySkoda, 
        memory_key: str, 
        persistent_key: str
    ) -> None:
        """Cache authenticated session both in memory and persistently"""
        try:
            # Cache in memory
            self.session_cache[memory_key] = {
                "myskoda": myskoda,
                "expires": datetime.now() + self.session_ttl,
                "created": datetime.now()
            }
            
            # Cache persistently (store session metadata only, not credentials)
            session_data = {
                "username": username,
                "authenticated_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + self.session_ttl).isoformat()
            }
            
            await self.cache_manager.set(
                persistent_key,
                session_data,
                ttl=int(self.session_ttl.total_seconds())
            )
            
            logger.info(f"Cached authentication session for {username}")
            
        except Exception as e:
            logger.warning(f"Failed to cache session: {e}")
            # Don't fail authentication if caching fails
    
    async def validate_session(self, myskoda: MySkoda) -> bool:
        """
        Validate that MySkoda session is still active
        
        Args:
            myskoda: MySkoda instance to validate
            
        Returns:
            True if session is valid, False otherwise
        """
        try:
            # Attempt a simple API call to validate session
            await myskoda.get_vehicles()
            return True
            
        except Exception as e:
            logger.warning(f"Session validation failed: {e}")
            return False
    
    async def refresh_session(
        self, 
        username: str, 
        password: str, 
        myskoda: MySkoda
    ) -> MySkoda:
        """
        Refresh existing session or create new one if needed
        
        Args:
            username: Skoda Connect username
            password: Skoda Connect password
            myskoda: Existing MySkoda instance
            
        Returns:
            Refreshed or new MySkoda instance
            
        Raises:
            AuthenticationError: If session refresh fails
        """
        try:
            # First try to validate existing session
            if await self.validate_session(myskoda):
                logger.info(f"Existing session for {username} is still valid")
                return myskoda
            
            # Session invalid, perform fresh authentication
            logger.info(f"Refreshing session for {username}")
            return await self.authenticate(username, password, force_refresh=True)
            
        except Exception as e:
            logger.error(f"Session refresh failed for {username}: {e}")
            raise AuthenticationError(f"Failed to refresh session: {str(e)}")
    
    async def logout(self, username: str) -> None:
        """
        Logout user and clear cached sessions
        
        Args:
            username: Username to logout
        """
        try:
            # Clear in-memory cache
            keys_to_remove = [k for k in self.session_cache if k.startswith(f"{username}:")]
            for key in keys_to_remove:
                del self.session_cache[key]
            
            # Clear persistent cache
            session_key = f"auth:session:{username}"
            await self.cache_manager.delete(session_key)
            
            # Clear any stored tokens
            await self._delete_stored_tokens(username)
            
            logger.info(f"Successfully logged out {username}")
            
        except Exception as e:
            logger.warning(f"Logout cleanup failed for {username}: {e}")
    
    async def _download_oauth_token(self, username: str) -> bool:
        """
        Download OAuth token from Google Cloud Storage
        
        Args:
            username: User email for token identification
            
        Returns:
            True if token exists and was downloaded, False otherwise
        """
        try:
            # Use username-specific token file
            blob_name = f"oauth_tokens/skoda_{username.replace('@', '_at_')}_oauth.json"
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            
            if blob.exists():
                blob.download_to_filename(str(self.local_token_path))
                logger.info(f"OAuth token downloaded for {username}")
                return True
                
            logger.info(f"No existing OAuth token found for {username}")
            return False
            
        except Exception as e:
            logger.warning(f"Failed to download OAuth token: {e}")
            return False
    
    async def _store_oauth_token(self, username: str, token_data: Dict[str, Any]) -> None:
        """
        Store OAuth token to Google Cloud Storage
        
        Args:
            username: User email for token identification
            token_data: Token data to store
        """
        try:
            # Store token data as JSON
            with open(self.local_token_path, 'w') as f:
                json.dump(token_data, f)
            
            # Upload to cloud storage with username-specific path
            blob_name = f"oauth_tokens/skoda_{username.replace('@', '_at_')}_oauth.json"
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            
            blob.upload_from_filename(str(self.local_token_path))
            logger.info(f"OAuth token uploaded for {username}")
            
            # Clean up local file
            if self.local_token_path.exists():
                self.local_token_path.unlink()
                
        except Exception as e:
            logger.error(f"Failed to store OAuth token: {e}")
            # Don't fail the request if token storage fails
    
    async def _delete_stored_tokens(self, username: str) -> None:
        """Delete stored OAuth tokens for user"""
        try:
            blob_name = f"oauth_tokens/skoda_{username.replace('@', '_at_')}_oauth.json"
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted stored OAuth token for {username}")
                
        except Exception as e:
            logger.warning(f"Failed to delete stored tokens: {e}")
    
    async def get_session_info(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get information about cached session
        
        Args:
            username: Username to check
            
        Returns:
            Session info if available, None otherwise
        """
        try:
            session_key = f"auth:session:{username}"
            session_data = await self.cache_manager.get(session_key)
            
            if session_data:
                return {
                    "username": session_data.get("username"),
                    "authenticated_at": session_data.get("authenticated_at"),
                    "expires_at": session_data.get("expires_at"),
                    "is_expired": datetime.now() > datetime.fromisoformat(
                        session_data.get("expires_at", "1970-01-01T00:00:00")
                    )
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get session info for {username}: {e}")
            return None
    
    def clear_cache(self, username: Optional[str] = None) -> None:
        """
        Clear authentication cache
        
        Args:
            username: Specific username to clear, or None to clear all
        """
        if username:
            # Clear specific user's cache
            keys_to_remove = [k for k in self.session_cache if k.startswith(f"{username}:")]
            for key in keys_to_remove:
                del self.session_cache[key]
            logger.info(f"Cleared cache for {username}")
        else:
            # Clear all cache
            self.session_cache.clear()
            logger.info("Cleared all authentication cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the authentication cache"""
        active_sessions = sum(
            1 for session in self.session_cache.values()
            if datetime.now() < session["expires"]
        )
        
        expired_sessions = len(self.session_cache) - active_sessions
        
        return {
            "total_cached_sessions": len(self.session_cache),
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions,
            "cache_entries": list(self.session_cache.keys()),
            "oldest_session": min(
                (s["created"] for s in self.session_cache.values()),
                default=None
            )
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on authentication system
        
        Returns:
            Health status and metrics
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "cache_stats": self.get_cache_stats()
        }
        
        try:
            # Test Google Cloud Storage connectivity
            bucket = self.storage_client.bucket(self.bucket_name)
            bucket.exists()  # This will raise exception if not accessible
            health_status["storage_connection"] = "healthy"
            
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["storage_connection"] = f"error: {str(e)}"
        
        return health_status