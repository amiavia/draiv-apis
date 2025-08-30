"""
Cache Manager
In-memory caching with TTL support for API responses
"""
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with value and expiration"""
    value: Any
    expires_at: datetime
    created_at: datetime
    hit_count: int = 0

class CacheManager:
    """
    In-memory cache manager with TTL support
    
    Provides caching for API responses to reduce load on external services
    and improve response times for frequently accessed data.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize cache manager
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default TTL in seconds
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.stats["misses"] += 1
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if datetime.now() > entry.expires_at:
            del self.cache[key]
            self.stats["expirations"] += 1
            self.stats["misses"] += 1
            logger.debug(f"Cache entry expired for key: {key}")
            return None
        
        # Update hit count and stats
        entry.hit_count += 1
        self.stats["hits"] += 1
        logger.debug(f"Cache hit for key: {key} (hits: {entry.hit_count})")
        
        return entry.value
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if not specified)
        """
        # Check if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self.cache[key] = CacheEntry(
            value=value,
            expires_at=expires_at,
            created_at=datetime.now(),
            hit_count=0
        )
        
        logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")
    
    def delete(self, key: str) -> bool:
        """
        Delete entry from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Deleted cache entry for key: {key}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared {count} cache entries")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries
        
        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now > entry.expires_at
        ]
        
        for key in expired_keys:
            del self.cache[key]
            self.stats["expirations"] += 1
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry"""
        if not self.cache:
            return
        
        # Find oldest entry
        oldest_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].created_at
        )
        
        del self.cache[oldest_key]
        self.stats["evictions"] += 1
        logger.debug(f"Evicted oldest cache entry: {oldest_key}")
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            self.stats["hits"] / total_requests * 100
            if total_requests > 0 else 0
        )
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.2f}%",
            "evictions": self.stats["evictions"],
            "expirations": self.stats["expirations"],
            "total_requests": total_requests
        }
    
    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """
        Generate cache key from arguments
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        # Create a string representation of all arguments
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        
        # Convert to JSON and hash for consistent key
        key_json = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_json.encode()).hexdigest()
        
        return key_hash