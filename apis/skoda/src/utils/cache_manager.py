"""
Cache Manager for Skoda API
Redis-based caching with TTL support
"""
import json
import logging
from typing import Any, Optional, Dict, List, Pattern
import redis.asyncio as redis
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Redis-based cache manager with TTL support
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.prefix = "skoda_api:"
        
        # Default TTL values (seconds)
        self.default_ttls = {
            "vehicle_status": 60,      # 1 minute
            "vehicle_list": 300,       # 5 minutes
            "location": 30,            # 30 seconds
            "auth_validation": 300,    # 5 minutes
            "trip_history": 3600,      # 1 hour
            "charging_status": 60      # 1 minute
        }
    
    async def connect(self) -> None:
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis cache connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Continue without cache in development
            self.redis_client = None
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis cache connection closed")
    
    def _make_key(self, key: str) -> str:
        """Create prefixed cache key"""
        return f"{self.prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            prefixed_key = self._make_key(key)
            value = await self.redis_client.get(prefixed_key)
            
            if value is not None:
                # Try to deserialize JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # Return string if not JSON
                    return value
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        cache_type: Optional[str] = None
    ) -> bool:
        """Set value in cache with optional TTL"""
        if not self.redis_client:
            return False
        
        try:
            prefixed_key = self._make_key(key)
            
            # Determine TTL
            if ttl is None and cache_type:
                ttl = self.default_ttls.get(cache_type, 300)  # Default 5 minutes
            
            # Serialize value
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            
            # Set with TTL
            if ttl:
                await self.redis_client.setex(prefixed_key, ttl, value)
            else:
                await self.redis_client.set(prefixed_key, value)
            
            logger.debug(f"Cached key {key} with TTL {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            prefixed_key = self._make_key(key)
            result = await self.redis_client.delete(prefixed_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.redis_client:
            return 0
        
        try:
            prefixed_pattern = self._make_key(pattern)
            
            # Get all matching keys
            keys = await self.redis_client.keys(prefixed_pattern)
            
            if keys:
                # Delete all matching keys
                deleted = await self.redis_client.delete(*keys)
                logger.debug(f"Deleted {deleted} keys matching pattern {pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            prefixed_key = self._make_key(key)
            result = await self.redis_client.exists(prefixed_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache exists check error for key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get TTL for key (-1 if no expiry, -2 if key doesn't exist)"""
        if not self.redis_client:
            return -2
        
        try:
            prefixed_key = self._make_key(key)
            return await self.redis_client.ttl(prefixed_key)
            
        except Exception as e:
            logger.error(f"Cache TTL check error for key {key}: {e}")
            return -2
    
    async def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """Extend TTL for existing key"""
        if not self.redis_client:
            return False
        
        try:
            prefixed_key = self._make_key(key)
            current_ttl = await self.redis_client.ttl(prefixed_key)
            
            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                await self.redis_client.expire(prefixed_key, new_ttl)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Cache extend TTL error for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment numeric value in cache"""
        if not self.redis_client:
            return None
        
        try:
            prefixed_key = self._make_key(key)
            result = await self.redis_client.incrby(prefixed_key, amount)
            return result
            
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disconnected"}
        
        try:
            info = await self.redis_client.info()
            
            # Extract relevant stats
            stats = {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "redis_version": info.get("redis_version", "unknown")
            }
            
            # Calculate hit ratio
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            total = hits + misses
            
            if total > 0:
                stats["hit_ratio"] = round((hits / total) * 100, 2)
            else:
                stats["hit_ratio"] = 0.0
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"status": "error", "error": str(e)}
    
    async def flush_prefix(self, prefix: str = "") -> int:
        """Flush all keys with given prefix (dangerous!)"""
        if not self.redis_client:
            return 0
        
        try:
            pattern = self._make_key(f"{prefix}*")
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.warning(f"Flushed {deleted} keys with prefix {prefix}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache flush error for prefix {prefix}: {e}")
            return 0
    
    async def size(self) -> int:
        """Get approximate number of keys in cache"""
        if not self.redis_client:
            return 0
        
        try:
            # Count keys with our prefix
            pattern = self._make_key("*")
            keys = await self.redis_client.keys(pattern)
            return len(keys)
            
        except Exception as e:
            logger.error(f"Cache size check error: {e}")
            return 0