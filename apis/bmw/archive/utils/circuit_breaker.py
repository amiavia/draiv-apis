"""
Circuit Breaker Pattern Implementation
Prevents cascading failures when external services are unavailable
Enhanced with quota-aware handling for BMW API
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
    QUOTA_PAUSED = "quota_paused"  # Paused due to quota limits

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
        
        # Quota handling
        self.quota_pause_until: Optional[datetime] = None
        self.quota_retry_count = 0
        
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
        elif self.state == CircuitState.QUOTA_PAUSED:
            if self._should_resume_from_quota():
                self.state = CircuitState.CLOSED
                logger.info(f"{self.name}: Quota pause expired, resuming normal operation")
            else:
                time_until_resume = self._time_until_quota_resume()
                logger.warning(
                    f"{self.name}: Circuit is QUOTA_PAUSED. "
                    f"Quota will be available in {time_until_resume:.0f} seconds"
                )
                from utils.error_handler import QuotaLimitError
                raise QuotaLimitError(
                    f"BMW API quota limit active. Retry in {time_until_resume:.0f} seconds",
                    retry_after=int(time_until_resume)
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
            
        except Exception as e:
            # Check if this is a quota error that should pause the circuit
            from utils.error_handler import QuotaLimitError
            if isinstance(e, QuotaLimitError):
                self._on_quota_error(e)
                raise
            elif isinstance(e, self.expected_exception):
                # Regular service failure
                self._on_failure()
                raise
            else:
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
            self.quota_retry_count = 0  # Reset quota retry count on success
            self.quota_pause_until = None
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
            # Reset quota retry count if we had quota issues before
            if self.quota_retry_count > 0:
                self.quota_retry_count = 0
                logger.info(f"{self.name}: Quota retry count reset after successful call")
    
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
    
    def _on_quota_error(self, error) -> None:
        """Handle quota limit error"""
        self.quota_retry_count += 1
        
        # Calculate pause duration based on retry_after from error
        if hasattr(error, 'retry_after') and error.retry_after:
            pause_seconds = error.retry_after
        else:
            # Default pause with exponential backoff
            pause_seconds = min(300, 60 * (2 ** (self.quota_retry_count - 1)))  # Max 5 minutes
        
        self.quota_pause_until = datetime.now() + timedelta(seconds=pause_seconds)
        self.state = CircuitState.QUOTA_PAUSED
        
        logger.warning(
            f"{self.name}: Quota limit reached, pausing for {pause_seconds} seconds. "
            f"Retry count: {self.quota_retry_count}"
        )
    
    def _should_resume_from_quota(self) -> bool:
        """Check if quota pause period has expired"""
        if not self.quota_pause_until:
            return True
        return datetime.now() >= self.quota_pause_until
    
    def _time_until_quota_resume(self) -> float:
        """Calculate seconds until quota pause expires"""
        if not self.quota_pause_until:
            return 0
        time_remaining = self.quota_pause_until - datetime.now()
        return max(0, time_remaining.total_seconds())
    
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
            ),
            "quota_retry_count": self.quota_retry_count,
            "quota_pause_until": (
                self.quota_pause_until.isoformat()
                if self.quota_pause_until else None
            ),
            "time_until_quota_resume": (
                self._time_until_quota_resume()
                if self.state == CircuitState.QUOTA_PAUSED else None
            )
        }