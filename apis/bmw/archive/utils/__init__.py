"""
BMW API Utilities
Common utilities for error handling, caching, and circuit breaking
"""

from .circuit_breaker import CircuitBreaker, CircuitState
from .cache_manager import CacheManager, CacheEntry
from .error_handler import (
    BMWAPIError,
    ValidationError,
    AuthenticationError,
    RemoteServiceError,
    VehicleNotFoundError,
    RateLimitError,
    ExternalServiceError,
    handle_api_error,
    error_tracker
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    
    # Cache Manager
    "CacheManager",
    "CacheEntry",
    
    # Error Handling
    "BMWAPIError",
    "ValidationError",
    "AuthenticationError",
    "RemoteServiceError",
    "VehicleNotFoundError",
    "RateLimitError",
    "ExternalServiceError",
    "handle_api_error",
    "error_tracker"
]