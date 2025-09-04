"""
Rate Limiter for Skoda Connect API
Per-user rate limiting implementation with sliding window algorithm
"""
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque, defaultdict
import time
import redis.asyncio as redis
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class RateLimitRule:
    """Rate limit rule definition"""
    requests: int           # Number of requests allowed
    window: int            # Time window in seconds
    burst_requests: int    # Burst requests allowed
    burst_window: int      # Burst window in seconds

@dataclass
class UserRateLimit:
    """Per-user rate limit tracking"""
    user_id: str
    requests: deque = field(default_factory=deque)
    burst_requests: deque = field(default_factory=deque)
    total_requests: int = 0
    blocked_requests: int = 0
    last_request: Optional[datetime] = None

class SkodaRateLimiter:
    """
    Advanced rate limiter for Skoda Connect API with per-user tracking
    
    Implements sliding window rate limiting with support for:
    - Per-user limits
    - Different limits for different operations
    - Burst request handling
    - Redis-backed distributed limiting
    - Detailed statistics and monitoring
    """
    
    # Default rate limits optimized for Skoda Connect API
    DEFAULT_LIMITS = {
        "status": RateLimitRule(
            requests=30,        # 30 requests per minute
            window=60,         # 1 minute window
            burst_requests=10,  # Allow 10 burst requests
            burst_window=10    # in 10 seconds
        ),
        "control": RateLimitRule(
            requests=10,        # 10 control commands per minute
            window=60,         # 1 minute window
            burst_requests=3,   # Allow 3 burst commands
            burst_window=10    # in 10 seconds
        ),
        "auth": RateLimitRule(
            requests=5,         # 5 auth attempts per minute
            window=60,         # 1 minute window
            burst_requests=2,   # Allow 2 burst attempts
            burst_window=30    # in 30 seconds
        ),
        "location": RateLimitRule(
            requests=60,        # 60 location requests per minute
            window=60,         # 1 minute window
            burst_requests=15,  # Allow 15 burst requests
            burst_window=10    # in 10 seconds
        ),
        "trip": RateLimitRule(
            requests=20,        # 20 trip data requests per minute
            window=60,         # 1 minute window
            burst_requests=5,   # Allow 5 burst requests
            burst_window=15    # in 15 seconds
        )
    }
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        limits: Optional[Dict[str, RateLimitRule]] = None,
        enable_redis: bool = True,
        key_prefix: str = "skoda_rate_limit:"
    ):
        """
        Initialize rate limiter
        
        Args:
            redis_url: Redis connection URL for distributed limiting
            limits: Custom rate limit rules
            enable_redis: Whether to use Redis for distributed limiting
            key_prefix: Prefix for Redis keys
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.limits = limits or self.DEFAULT_LIMITS
        self.enable_redis = enable_redis
        self.key_prefix = key_prefix
        
        # In-memory storage for standalone operation
        self.user_limits: Dict[str, UserRateLimit] = {}
        
        # Redis client
        self.redis_client: Optional[redis.Redis] = None
        self.redis_available = False
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "redis_errors": 0,
            "cleanup_runs": 0
        }
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client, initialize if needed"""
        if not self.enable_redis:
            return None
            
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                await self.redis_client.ping()
                self.redis_available = True
                logger.info("Redis connection established for rate limiting")
            except Exception as e:
                logger.warning(f"Redis not available for rate limiting: {e}")
                self.redis_available = False
                return None
        
        return self.redis_client if self.redis_available else None
    
    async def is_allowed(
        self,
        user_id: str,
        operation: str,
        increment: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit
        
        Args:
            user_id: User identifier
            operation: Operation type (status, control, auth, etc.)
            increment: Whether to increment the counter
            
        Returns:
            Tuple of (is_allowed, limit_info)
        """
        self.stats["total_requests"] += 1
        
        # Get rate limit rule
        rule = self.limits.get(operation)
        if not rule:
            logger.warning(f"No rate limit rule found for operation: {operation}")
            return True, {"status": "no_limit"}
        
        current_time = time.time()
        
        # Try Redis-based limiting first
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                allowed, info = await self._check_redis_limit(
                    redis_client, user_id, operation, rule, current_time, increment
                )
                return allowed, info
            except Exception as e:
                logger.error(f"Redis rate limit check failed: {e}")
                self.stats["redis_errors"] += 1
                # Fall back to in-memory limiting
        
        # In-memory rate limiting
        return await self._check_memory_limit(user_id, operation, rule, current_time, increment)
    
    async def _check_redis_limit(
        self,
        redis_client: redis.Redis,
        user_id: str,
        operation: str,
        rule: RateLimitRule,
        current_time: float,
        increment: bool
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis"""
        key = f"{self.key_prefix}{user_id}:{operation}"
        burst_key = f"{key}:burst"
        
        # Use Redis pipeline for atomic operations
        pipe = redis_client.pipeline()
        
        # Regular rate limit check
        pipe.zremrangebyscore(key, 0, current_time - rule.window)
        pipe.zcard(key)
        pipe.zremrangebyscore(burst_key, 0, current_time - rule.burst_window)
        pipe.zcard(burst_key)
        
        if increment:
            pipe.zadd(key, {str(current_time): current_time})
            pipe.expire(key, rule.window)
            pipe.zadd(burst_key, {str(current_time): current_time})
            pipe.expire(burst_key, rule.burst_window)
        
        results = await pipe.execute()
        
        if increment:
            regular_count = results[1] + 1
            burst_count = results[3] + 1
        else:
            regular_count = results[1]
            burst_count = results[3]
        
        # Check limits
        regular_allowed = regular_count <= rule.requests
        burst_allowed = burst_count <= rule.burst_requests
        
        is_allowed = regular_allowed and burst_allowed
        
        if not is_allowed:
            self.stats["blocked_requests"] += 1
        
        # Calculate time until reset
        if regular_count > 0:
            oldest_request = await redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                reset_time = int(oldest_request[0][1] + rule.window)
            else:
                reset_time = int(current_time + rule.window)
        else:
            reset_time = int(current_time + rule.window)
        
        return is_allowed, {
            "allowed": is_allowed,
            "requests_made": regular_count,
            "requests_limit": rule.requests,
            "burst_requests_made": burst_count,
            "burst_requests_limit": rule.burst_requests,
            "reset_time": reset_time,
            "retry_after": max(0, reset_time - current_time),
            "window": rule.window,
            "source": "redis"
        }
    
    async def _check_memory_limit(
        self,
        user_id: str,
        operation: str,
        rule: RateLimitRule,
        current_time: float,
        increment: bool
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using in-memory storage"""
        user_key = f"{user_id}:{operation}"
        
        # Get or create user rate limit tracking
        if user_key not in self.user_limits:
            self.user_limits[user_key] = UserRateLimit(user_id=user_key)
        
        user_limit = self.user_limits[user_key]
        
        # Clean up old requests
        cutoff_time = current_time - rule.window
        burst_cutoff_time = current_time - rule.burst_window
        
        while user_limit.requests and user_limit.requests[0] <= cutoff_time:
            user_limit.requests.popleft()
        
        while user_limit.burst_requests and user_limit.burst_requests[0] <= burst_cutoff_time:
            user_limit.burst_requests.popleft()
        
        # Check limits
        regular_count = len(user_limit.requests)
        burst_count = len(user_limit.burst_requests)
        
        regular_allowed = regular_count < rule.requests
        burst_allowed = burst_count < rule.burst_requests
        
        is_allowed = regular_allowed and burst_allowed
        
        # Increment counters if allowed and requested
        if increment:
            if is_allowed:
                user_limit.requests.append(current_time)
                user_limit.burst_requests.append(current_time)
                user_limit.total_requests += 1
                user_limit.last_request = datetime.now()
            else:
                user_limit.blocked_requests += 1
                self.stats["blocked_requests"] += 1
        
        # Calculate reset time
        if user_limit.requests:
            reset_time = int(user_limit.requests[0] + rule.window)
        else:
            reset_time = int(current_time + rule.window)
        
        return is_allowed, {
            "allowed": is_allowed,
            "requests_made": regular_count + (1 if increment and is_allowed else 0),
            "requests_limit": rule.requests,
            "burst_requests_made": burst_count + (1 if increment and is_allowed else 0),
            "burst_requests_limit": rule.burst_requests,
            "reset_time": reset_time,
            "retry_after": max(0, reset_time - current_time),
            "window": rule.window,
            "source": "memory"
        }
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get rate limit statistics for a user"""
        stats = {}
        
        for operation in self.limits.keys():
            user_key = f"{user_id}:{operation}"
            if user_key in self.user_limits:
                user_limit = self.user_limits[user_key]
                stats[operation] = {
                    "total_requests": user_limit.total_requests,
                    "blocked_requests": user_limit.blocked_requests,
                    "current_window_requests": len(user_limit.requests),
                    "current_burst_requests": len(user_limit.burst_requests),
                    "last_request": (
                        user_limit.last_request.isoformat()
                        if user_limit.last_request else None
                    )
                }
            else:
                stats[operation] = {
                    "total_requests": 0,
                    "blocked_requests": 0,
                    "current_window_requests": 0,
                    "current_burst_requests": 0,
                    "last_request": None
                }
        
        return stats
    
    async def reset_user_limits(self, user_id: str, operation: Optional[str] = None) -> bool:
        """Reset rate limits for a user"""
        if operation:
            user_key = f"{user_id}:{operation}"
            if user_key in self.user_limits:
                del self.user_limits[user_key]
                logger.info(f"Reset rate limit for user {user_id}, operation {operation}")
                return True
        else:
            # Reset all operations for user
            keys_to_remove = [
                key for key in self.user_limits.keys()
                if key.startswith(f"{user_id}:")
            ]
            for key in keys_to_remove:
                del self.user_limits[key]
            logger.info(f"Reset all rate limits for user {user_id}")
            return len(keys_to_remove) > 0
        
        return False
    
    async def cleanup_expired(self) -> int:
        """Clean up expired rate limit entries"""
        current_time = time.time()
        expired_keys = []
        
        for user_key, user_limit in self.user_limits.items():
            # Remove if no requests in the last hour
            if (not user_limit.last_request or 
                (datetime.now() - user_limit.last_request).total_seconds() > 3600):
                expired_keys.append(user_key)
        
        for key in expired_keys:
            del self.user_limits[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired rate limit entries")
        
        self.stats["cleanup_runs"] += 1
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall rate limiter statistics"""
        active_users = len(set(
            key.split(':')[0] for key in self.user_limits.keys()
        ))
        
        blocked_rate = 0
        if self.stats["total_requests"] > 0:
            blocked_rate = (
                self.stats["blocked_requests"] / 
                self.stats["total_requests"] * 100
            )
        
        return {
            "total_requests": self.stats["total_requests"],
            "blocked_requests": self.stats["blocked_requests"],
            "blocked_rate": f"{blocked_rate:.2f}%",
            "active_users": active_users,
            "active_user_operations": len(self.user_limits),
            "redis_available": self.redis_available,
            "redis_errors": self.stats["redis_errors"],
            "cleanup_runs": self.stats["cleanup_runs"],
            "configured_operations": list(self.limits.keys())
        }
    
    async def start_cleanup_task(self, interval: int = 300) -> None:
        """Start background cleanup task"""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval)
                    await self.cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Rate limiter cleanup error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"Started rate limiter cleanup task (interval: {interval}s)")
    
    async def stop_cleanup_task(self) -> None:
        """Stop background cleanup task"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped rate limiter cleanup task")
    
    async def close(self) -> None:
        """Close connections and cleanup"""
        await self.stop_cleanup_task()
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Rate limiter Redis connection closed")

# Create decorator for easy rate limiting
def rate_limit(operation: str, user_id_field: str = "user_id"):
    """
    Rate limiting decorator for Skoda Connect API functions
    
    Usage:
        @rate_limit("status", user_id_field="email")
        async def get_vehicle_status(email, vehicle_id):
            # Your API call here
            pass
    """
    def decorator(func: callable) -> callable:
        async def wrapper(*args, **kwargs):
            rate_limiter = getattr(wrapper, '_rate_limiter', None)
            if not rate_limiter:
                return await func(*args, **kwargs)
            
            # Extract user ID
            user_id = None
            if user_id_field in kwargs:
                user_id = kwargs[user_id_field]
            elif hasattr(func, '__code__'):
                # Try to get from positional args
                arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]
                if user_id_field in arg_names:
                    arg_index = arg_names.index(user_id_field)
                    if arg_index < len(args):
                        user_id = args[arg_index]
            
            if not user_id:
                logger.warning(f"Could not extract user_id from {user_id_field}")
                return await func(*args, **kwargs)
            
            # Check rate limit
            allowed, info = await rate_limiter.is_allowed(user_id, operation)
            if not allowed:
                from .error_handler import RateLimitError
                raise RateLimitError(
                    f"Rate limit exceeded for {operation}. Try again in {info['retry_after']:.0f} seconds",
                    limit=info['requests_limit'],
                    reset_time=datetime.fromtimestamp(info['reset_time'])
                )
            
            # Execute function
            return await func(*args, **kwargs)
        
        wrapper._original_func = func
        return wrapper
    
    return decorator