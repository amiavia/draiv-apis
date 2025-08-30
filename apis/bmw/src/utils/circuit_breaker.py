"""
Circuit Breaker Pattern Implementation
Prevents cascading failures when external services are unavailable
"""
import asyncio
import logging
from typing import Any, Callable, Optional, Type
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Service is down, fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls
    
    The circuit breaker pattern prevents an application from repeatedly
    trying to execute an operation that's likely to fail, allowing it
    to continue without waiting for the fault to be fixed.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
        name: Optional[str] = None
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch and count as failure
            name: Optional name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name or "CircuitBreaker"
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self.successful_calls = 0
        self.total_calls = 0
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        self.total_calls += 1
        
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"{self.name}: Circuit entering HALF_OPEN state")
            else:
                time_until_reset = self._time_until_reset()
                logger.warning(
                    f"{self.name}: Circuit is OPEN. "
                    f"Retry in {time_until_reset:.0f} seconds"
                )
                raise Exception(
                    f"Circuit breaker is OPEN. Service unavailable. "
                    f"Retry in {time_until_reset:.0f} seconds"
                )
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Call succeeded
            self._on_success()
            return result
            
        except self.expected_exception as e:
            # Call failed
            self._on_failure()
            raise
        except Exception as e:
            # Unexpected exception, don't count as circuit failure
            logger.error(f"{self.name}: Unexpected exception: {e}")
            raise
    
    def _on_success(self) -> None:
        """Handle successful call"""
        self.successful_calls += 1
        
        if self.state == CircuitState.HALF_OPEN:
            # Service recovered, close circuit
            logger.info(f"{self.name}: Circuit recovered, entering CLOSED state")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            # Service still down, reopen circuit
            logger.warning(f"{self.name}: Recovery failed, circuit returning to OPEN state")
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            # Too many failures, open circuit
            logger.error(
                f"{self.name}: Failure threshold reached ({self.failure_count}), "
                f"circuit entering OPEN state"
            )
            self.state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def _time_until_reset(self) -> float:
        """Calculate seconds until circuit can attempt reset"""
        if not self.last_failure_time:
            return 0
        
        time_since_failure = datetime.now() - self.last_failure_time
        time_until_reset = self.recovery_timeout - time_since_failure.total_seconds()
        return max(0, time_until_reset)
    
    def reset(self) -> None:
        """Manually reset the circuit breaker"""
        logger.info(f"{self.name}: Manually resetting circuit breaker")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "successful_calls": self.successful_calls,
            "total_calls": self.total_calls,
            "success_rate": (
                self.successful_calls / self.total_calls * 100
                if self.total_calls > 0 else 0
            ),
            "last_failure_time": (
                self.last_failure_time.isoformat()
                if self.last_failure_time else None
            ),
            "time_until_reset": (
                self._time_until_reset()
                if self.state == CircuitState.OPEN else None
            )
        }