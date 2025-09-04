"""
Circuit Breaker Implementation for Skoda API
Provides fault tolerance and prevents cascading failures
"""
import asyncio
import logging
from typing import Callable, Any, Optional, Type
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreakerError(Exception):
    """Circuit breaker is open, request blocked"""
    pass

class CircuitBreaker:
    """
    Circuit breaker implementation for API fault tolerance
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
        success_threshold: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        
        # State tracking
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.call_count = 0
        self.success_call_count = 0
        
        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function call through circuit breaker
        """
        self.total_calls += 1
        self.call_count += 1
        
        # Check current state and decide whether to proceed
        if self.state == CircuitBreakerState.OPEN:
            if not self._should_attempt_reset():
                logger.warning("Circuit breaker is OPEN, blocking call")
                raise CircuitBreakerError("Circuit breaker is open")
            else:
                # Move to half-open state
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker moving to HALF_OPEN state")
        
        try:
            # Execute the function
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Call succeeded
            self._on_success()
            return result
            
        except self.expected_exception as e:
            # Expected failure type
            self._on_failure()
            raise e
        except Exception as e:
            # Unexpected exception, also count as failure
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from OPEN state"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure >= timedelta(seconds=self.recovery_timeout)
    
    def _on_success(self) -> None:
        """Handle successful call"""
        self.success_call_count += 1
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Count successful calls in half-open state
            self.success_count += 1
            
            if self.success_count >= self.success_threshold:
                # Enough successes, reset to closed
                self._reset()
                logger.info("Circuit breaker RESET to CLOSED state")
        else:
            # In closed state, reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call"""
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Failure in half-open state, go back to open
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
            logger.warning("Circuit breaker failure in HALF_OPEN, returning to OPEN state")
            
        elif self.state == CircuitBreakerState.CLOSED:
            # Check if we should trip the breaker
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.error(f"Circuit breaker TRIPPED to OPEN state after {self.failure_count} failures")
    
    def _reset(self) -> None:
        """Reset circuit breaker to closed state"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    def force_open(self) -> None:
        """Manually force circuit breaker to open state"""
        self.state = CircuitBreakerState.OPEN
        self.last_failure_time = datetime.utcnow()
        logger.warning("Circuit breaker manually forced to OPEN state")
    
    def force_close(self) -> None:
        """Manually force circuit breaker to closed state"""
        self._reset()
        logger.info("Circuit breaker manually forced to CLOSED state")
    
    @property
    def current_state(self) -> str:
        """Get current circuit breaker state"""
        return self.state.value
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        success_rate = (
            (self.total_calls - self.total_failures) / self.total_calls * 100
            if self.total_calls > 0 else 0
        )
        
        return {
            "state": self.state.value,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "success_rate": round(success_rate, 2),
            "current_failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "time_until_retry": self._get_time_until_retry()
        }
    
    def _get_time_until_retry(self) -> Optional[int]:
        """Get seconds until next retry attempt"""
        if self.state != CircuitBreakerState.OPEN or self.last_failure_time is None:
            return None
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        remaining_time = self.recovery_timeout - time_since_failure.total_seconds()
        
        return max(0, int(remaining_time))
    
    def __str__(self) -> str:
        """String representation of circuit breaker"""
        return f"CircuitBreaker(state={self.state.value}, failures={self.failure_count}/{self.failure_threshold})"