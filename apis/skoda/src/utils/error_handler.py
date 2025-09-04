"""
Error Handler for Skoda Connect API
Centralized error handling with Skoda-specific error codes and responses
"""
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from enum import Enum
import traceback
import json

logger = logging.getLogger(__name__)

class SkodaErrorCode(Enum):
    """Skoda Connect API specific error codes"""
    # Authentication errors
    SPIN_REQUIRED = "SPIN_REQUIRED"
    AUTH_FAILED = "AUTH_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    MFA_REQUIRED = "MFA_REQUIRED"
    
    # Vehicle errors
    VEHICLE_NOT_FOUND = "VEHICLE_NOT_FOUND"
    VEHICLE_OFFLINE = "VEHICLE_OFFLINE"
    VEHICLE_LOCKED = "VEHICLE_LOCKED"
    INVALID_VIN = "INVALID_VIN"
    
    # Service errors
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    REMOTE_COMMAND_FAILED = "REMOTE_COMMAND_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    API_QUOTA_EXCEEDED = "API_QUOTA_EXCEEDED"
    
    # Data errors
    INVALID_REQUEST = "INVALID_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    
    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"

class SkodaAPIError(Exception):
    """Base exception for Skoda Connect API errors"""
    
    def __init__(
        self, 
        message: str, 
        code: SkodaErrorCode = SkodaErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        http_status: int = 500
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.http_status = http_status
        self.timestamp = datetime.now()
        super().__init__(self.message)

class AuthenticationError(SkodaAPIError):
    """Raised when authentication fails"""
    def __init__(self, message: str, code: SkodaErrorCode = SkodaErrorCode.AUTH_FAILED):
        super().__init__(message, code, http_status=401)

class SpinRequiredError(AuthenticationError):
    """Raised when SPIN is required for authentication"""
    def __init__(self, message: str = "SPIN required for authentication"):
        super().__init__(message, SkodaErrorCode.SPIN_REQUIRED)

class ValidationError(SkodaAPIError):
    """Raised when request validation fails"""
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, SkodaErrorCode.VALIDATION_ERROR, details, 400)

class VehicleError(SkodaAPIError):
    """Raised when vehicle-related operations fail"""
    def __init__(self, message: str, vin: Optional[str] = None, code: SkodaErrorCode = SkodaErrorCode.VEHICLE_NOT_FOUND):
        details = {"vin": vin} if vin else {}
        super().__init__(message, code, details, 404 if code == SkodaErrorCode.VEHICLE_NOT_FOUND else 400)

class RemoteServiceError(SkodaAPIError):
    """Raised when remote service operation fails"""
    def __init__(self, message: str, operation: Optional[str] = None):
        details = {"operation": operation} if operation else {}
        super().__init__(message, SkodaErrorCode.REMOTE_COMMAND_FAILED, details, 502)

class RateLimitError(SkodaAPIError):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str, limit: Optional[int] = None, reset_time: Optional[datetime] = None):
        details = {}
        if limit:
            details["limit"] = limit
        if reset_time:
            details["reset_time"] = reset_time.isoformat()
        super().__init__(message, SkodaErrorCode.RATE_LIMIT_EXCEEDED, details, 429)

class ExternalServiceError(SkodaAPIError):
    """Raised when external service (Skoda Connect) is unavailable"""
    def __init__(self, message: str, service: Optional[str] = None):
        details = {"service": service} if service else {}
        super().__init__(message, SkodaErrorCode.EXTERNAL_SERVICE_ERROR, details, 503)

class TimeoutError(SkodaAPIError):
    """Raised when operation times out"""
    def __init__(self, message: str, timeout_seconds: Optional[int] = None):
        details = {"timeout_seconds": timeout_seconds} if timeout_seconds else {}
        super().__init__(message, SkodaErrorCode.TIMEOUT_ERROR, details, 408)

def create_error_response(
    error: Exception,
    request_id: Optional[str] = None,
    include_traceback: bool = False
) -> Tuple[Dict[str, Any], int]:
    """
    Create standardized error response
    
    Args:
        error: The exception to handle
        request_id: Optional request ID for tracking
        include_traceback: Whether to include traceback in response
        
    Returns:
        Tuple of (response_dict, http_status_code)
    """
    if isinstance(error, SkodaAPIError):
        status_code = error.http_status
        error_response = {
            "success": False,
            "error": {
                "code": error.code.value,
                "message": error.message,
                "details": error.details,
                "timestamp": error.timestamp.isoformat()
            }
        }
        
        # Log error based on severity
        if status_code >= 500:
            logger.error(f"Server error [{error.code.value}]: {error.message}", exc_info=True)
        else:
            logger.warning(f"Client error [{error.code.value}]: {error.message}")
    else:
        # Handle unexpected errors
        status_code = 500
        error_response = {
            "success": False,
            "error": {
                "code": SkodaErrorCode.INTERNAL_ERROR.value,
                "message": "An unexpected error occurred",
                "details": {"original_error": str(error)},
                "timestamp": datetime.now().isoformat()
            }
        }
        
        logger.error(f"Unexpected error: {error}", exc_info=True)
    
    # Add request ID if provided
    if request_id:
        error_response["error"]["request_id"] = request_id
    
    # Add traceback if requested (development only)
    if include_traceback and isinstance(error, Exception):
        error_response["error"]["traceback"] = traceback.format_exc()
    
    return error_response, status_code

def handle_api_error(error: Exception, request_id: Optional[str] = None) -> Tuple[Dict[str, Any], int, Dict[str, str]]:
    """
    Handle API errors and return Flask-compatible response
    
    Args:
        error: The exception to handle
        request_id: Optional request ID for tracking
        
    Returns:
        Tuple of (response_dict, status_code, headers)
    """
    error_response, status_code = create_error_response(error, request_id)
    
    # Standard headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    }
    
    # Add rate limit headers if applicable
    if isinstance(error, RateLimitError) and "reset_time" in error.details:
        headers["Retry-After"] = str(60)  # Default retry after 60 seconds
    
    return error_response, status_code, headers

class ErrorTracker:
    """Track and analyze errors for monitoring and debugging"""
    
    def __init__(self, max_errors_per_type: int = 100):
        """
        Initialize error tracker
        
        Args:
            max_errors_per_type: Maximum number of errors to keep per type
        """
        self.max_errors_per_type = max_errors_per_type
        self.errors: Dict[str, List[Dict[str, Any]]] = {}
        self.error_counts: Dict[str, int] = {}
        self.hourly_stats: Dict[str, Dict[int, int]] = {}  # hour -> error_count
    
    def track_error(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> None:
        """
        Track an error occurrence
        
        Args:
            error: The exception to track
            context: Optional context information
            request_id: Optional request ID
        """
        if isinstance(error, SkodaAPIError):
            error_type = error.code.value
            error_details = {
                "message": error.message,
                "code": error.code.value,
                "http_status": error.http_status,
                "details": error.details,
                "timestamp": error.timestamp.isoformat()
            }
        else:
            error_type = type(error).__name__
            error_details = {
                "message": str(error),
                "code": "UNKNOWN_ERROR",
                "http_status": 500,
                "details": {},
                "timestamp": datetime.now().isoformat()
            }
        
        # Add context and request ID
        if context:
            error_details["context"] = context
        if request_id:
            error_details["request_id"] = request_id
        
        # Update error count
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Store error details
        if error_type not in self.errors:
            self.errors[error_type] = []
        
        self.errors[error_type].append(error_details)
        
        # Keep only recent errors
        if len(self.errors[error_type]) > self.max_errors_per_type:
            self.errors[error_type] = self.errors[error_type][-self.max_errors_per_type:]
        
        # Update hourly stats
        current_hour = datetime.now().hour
        if error_type not in self.hourly_stats:
            self.hourly_stats[error_type] = {}
        if current_hour not in self.hourly_stats[error_type]:
            self.hourly_stats[error_type][current_hour] = 0
        self.hourly_stats[error_type][current_hour] += 1
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        total_errors = sum(self.error_counts.values())
        
        # Calculate error rates
        error_rates = {}
        if total_errors > 0:
            for error_type, count in self.error_counts.items():
                error_rates[error_type] = f"{(count / total_errors * 100):.2f}%"
        
        # Get recent errors (last 10 per type)
        recent_errors = {}
        for error_type, errors in self.errors.items():
            recent_errors[error_type] = errors[-10:]
        
        return {
            "total_errors": total_errors,
            "error_counts": self.error_counts,
            "error_rates": error_rates,
            "recent_errors": recent_errors,
            "hourly_stats": self.hourly_stats,
            "most_common_errors": sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status based on error patterns"""
        total_errors = sum(self.error_counts.values())
        current_hour = datetime.now().hour
        
        # Count errors in the last hour
        recent_errors = 0
        for error_type, hourly_data in self.hourly_stats.items():
            recent_errors += hourly_data.get(current_hour, 0)
        
        # Determine health status
        if recent_errors == 0:
            status = "healthy"
        elif recent_errors < 10:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "status": status,
            "total_errors": total_errors,
            "recent_errors": recent_errors,
            "error_rate": f"{(recent_errors / max(1, total_errors) * 100):.2f}%"
        }
    
    def clear_stats(self) -> None:
        """Clear all error statistics"""
        self.errors.clear()
        self.error_counts.clear()
        self.hourly_stats.clear()
        logger.info("Error statistics cleared")

# Global error tracker instance
error_tracker = ErrorTracker()

# Error mapping for common HTTP status codes
HTTP_ERROR_MAPPING = {
    400: SkodaErrorCode.INVALID_REQUEST,
    401: SkodaErrorCode.AUTH_FAILED,
    403: SkodaErrorCode.VEHICLE_LOCKED,
    404: SkodaErrorCode.VEHICLE_NOT_FOUND,
    408: SkodaErrorCode.TIMEOUT_ERROR,
    429: SkodaErrorCode.RATE_LIMIT_EXCEEDED,
    500: SkodaErrorCode.INTERNAL_ERROR,
    502: SkodaErrorCode.EXTERNAL_SERVICE_ERROR,
    503: SkodaErrorCode.SERVICE_UNAVAILABLE,
}

def map_http_error(status_code: int, message: str) -> SkodaAPIError:
    """
    Map HTTP status code to Skoda API error
    
    Args:
        status_code: HTTP status code
        message: Error message
        
    Returns:
        Appropriate SkodaAPIError instance
    """
    error_code = HTTP_ERROR_MAPPING.get(status_code, SkodaErrorCode.INTERNAL_ERROR)
    return SkodaAPIError(message, error_code, http_status=status_code)