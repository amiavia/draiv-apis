"""
Dynamic User Agent Manager for BMW API
Generates stable, unique user agents to avoid BMW quota limits
"""
import hashlib
import platform
import uuid
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class UserAgentManager:
    """
    Manages dynamic user agent generation to avoid BMW API quota limits.
    
    BMW introduced quota limits tracked via x-user-agent header.
    This class generates a stable, unique user agent per deployment/container
    to distribute quota usage and avoid hitting limits.
    """
    
    def __init__(self, instance_id: Optional[str] = None):
        """
        Initialize user agent manager
        
        Args:
            instance_id: Optional custom instance ID, generates one if not provided
        """
        self._instance_id = instance_id
        self._user_agent = None
        self._agent_cache_file = Path("/tmp/draiv_user_agent.cache")
        
    @property
    def instance_id(self) -> str:
        """Get or generate stable instance ID for this deployment"""
        if not self._instance_id:
            # Try to load from cache first
            if self._agent_cache_file.exists():
                try:
                    with open(self._agent_cache_file, 'r') as f:
                        cached_id = f.read().strip()
                        if cached_id:
                            self._instance_id = cached_id
                            logger.info("Loaded cached instance ID")
                            return self._instance_id
                except Exception as e:
                    logger.warning(f"Failed to load cached instance ID: {e}")
            
            # Generate new stable instance ID based on system characteristics
            system_info = f"{platform.node()}-{platform.machine()}-{platform.system()}"
            
            # For containerized environments, try to get container ID
            container_id = self._get_container_id()
            if container_id:
                system_info += f"-{container_id}"
            
            # Create deterministic UUID based on system info
            namespace_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, "draiv.ch")
            self._instance_id = str(uuid.uuid5(namespace_uuid, system_info))
            
            # Cache the instance ID
            try:
                with open(self._agent_cache_file, 'w') as f:
                    f.write(self._instance_id)
                logger.info(f"Generated and cached new instance ID: {self._instance_id[:8]}...")
            except Exception as e:
                logger.warning(f"Failed to cache instance ID: {e}")
        
        return self._instance_id
    
    def _get_container_id(self) -> Optional[str]:
        """
        Extract container ID from cgroup or other container indicators
        
        Returns:
            Container ID if running in container, None otherwise
        """
        try:
            # Try to get Docker container ID from cgroup
            with open('/proc/self/cgroup', 'r') as f:
                for line in f:
                    if 'docker' in line:
                        # Extract container ID from Docker cgroup path
                        parts = line.strip().split('/')
                        if len(parts) > 2:
                            container_id = parts[-1]
                            if len(container_id) >= 12:  # Docker container IDs are typically 64 chars
                                return container_id[:12]  # Use first 12 chars
        except (FileNotFoundError, IOError):
            # Not running in a container or cgroup not available
            pass
        
        # Try Cloud Run/GCP metadata
        try:
            import os
            if 'K_SERVICE' in os.environ:  # Cloud Run
                return f"cloudrun-{os.environ.get('K_REVISION', 'unknown')}"
        except Exception:
            pass
        
        return None
    
    @property 
    def user_agent(self) -> str:
        """
        Generate dynamic user agent string
        
        Returns:
            Unique user agent string for this deployment
        """
        if not self._user_agent:
            # Create stable hash from instance ID
            hasher = hashlib.sha256()
            hasher.update(self.instance_id.encode('utf-8'))
            agent_hash = hasher.hexdigest()[:16]  # Use first 16 chars
            
            # Generate user agent in format similar to bimmer_connected default
            # but with unique hash to avoid quota conflicts
            self._user_agent = f"draiv-bmw-api/{agent_hash}"
            
            logger.info(f"Generated user agent: {self._user_agent}")
        
        return self._user_agent
    
    def reset_user_agent(self) -> str:
        """
        Force regeneration of user agent (useful for testing)
        
        Returns:
            New user agent string
        """
        self._user_agent = None
        self._instance_id = None
        
        # Remove cache file
        try:
            if self._agent_cache_file.exists():
                self._agent_cache_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to remove cache file: {e}")
        
        return self.user_agent
    
    def get_headers(self) -> dict:
        """
        Get HTTP headers with dynamic user agent
        
        Returns:
            Dictionary of HTTP headers including x-user-agent
        """
        return {
            'x-user-agent': self.user_agent,
            'User-Agent': self.user_agent
        }
    
    def get_stats(self) -> dict:
        """Get user agent manager statistics"""
        return {
            'instance_id': self.instance_id,
            'user_agent': self.user_agent,
            'cache_file_exists': self._agent_cache_file.exists(),
            'container_id': self._get_container_id()
        }

# Global instance for consistent user agent across the application
user_agent_manager = UserAgentManager()