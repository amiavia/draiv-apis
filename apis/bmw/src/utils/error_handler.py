"""
Error Handler
Centralized error handling and custom exception classes
"""
import logging
from typing import Dict, Any, Optional, Tuple
from flask import jsonify
from datetime import datetime

logger = logging.getLogger(__name__)

class BMWAPIError(Exception):
    """Base exception for BMW API errors"""
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or "BMW_API_ERROR"
        super().__init__(self.message)

class ValidationError(BMWAPIError):
    """Raised when request validation fails"""
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")

class AuthenticationError(BMWAPIError):
    """Raised when authentication fails"""
    def __init__(self, message: str):
        super().__init__(message, "AUTHENTICATION_ERROR")

class RemoteServiceError(BMWAPIError):
    """Raised when remote service operation fails"""
    def __init__(self, message: str):
        super().__init__(message, "REMOTE_SERVICE_ERROR")

class VehicleNotFoundError(BMWAPIError):
    """Raised when vehicle is not found"""
    def __init__(self, message: str):
        super().__init__(message, "VEHICLE_NOT_FOUND")

class RateLimitError(BMWAPIError):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str):
        super().__init__(message, "RATE_LIMIT_EXCEEDED")

class ExternalServiceError(BMWAPIError):
    """Raised when external service (BMW API) is unavailable"""
    def __init__(self, message: str):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR")

def handle_api_error(error: Exception, status_code: int) -> Tuple[Any, int, Dict[str, str]]:
    """
    Handle API errors and return formatted response
    
    Args:
        error: The exception to handle
        status_code: HTTP status code to return
        
    Returns:
        Tuple of (response, status_code, headers)
    """
    # Log the error
    if status_code >= 500:
        logger.error(f"Server error: {error}", exc_info=True)
    else:
        logger.warning(f"Client error: {error}")
    
    # Prepare error response
    error_response = {
        "success": False,
        "error": {
            "message": str(error),
            "code": getattr(error, "code", "UNKNOWN_ERROR"),
            "timestamp": datetime.now().isoformat()
        }
    }
    
    # Add additional context for specific errors
    if isinstance(error, ValidationError):
        error_response["error"]["type"] = "validation"
        error_response["error"]["details"] = "Please check your request parameters"
    elif isinstance(error, AuthenticationError):
        error_response["error"]["type"] = "authentication"
        error_response["error"]["details"] = "Please verify your credentials"
    elif isinstance(error, RemoteServiceError):
        error_response["error"]["type"] = "remote_service"
        error_response["error"]["details"] = "The remote operation could not be completed"
    elif isinstance(error, RateLimitError):
        error_response["error"]["type"] = "rate_limit"
        error_response["error"]["details"] = "Too many requests. Please try again later"
    elif isinstance(error, ExternalServiceError):
        error_response["error"]["type"] = "external_service"
        error_response["error"]["details"] = "BMW services are temporarily unavailable"
    
    # CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    }
    
    return (jsonify(error_response), status_code, headers)

class ErrorTracker:
    """Track and analyze errors for monitoring"""
    
    def __init__(self):
        self.errors: Dict[str, Dict[str, Any]] = {}
        self.error_counts: Dict[str, int] = {}
    
    def track_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Track an error occurrence
        
        Args:
            error: The exception to track
            context: Optional context information
        """
        error_type = type(error).__name__
        error_code = getattr(error, "code", "UNKNOWN")
        
        # Update error count
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Store error details (keep last 100 per type)
        if error_type not in self.errors:
            self.errors[error_type] = []
        
        error_entry = {
            "message": str(error),
            "code": error_code,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        
        self.errors[error_type].append(error_entry)
        
        # Keep only last 100 errors per type
        if len(self.errors[error_type]) > 100:
            self.errors[error_type] = self.errors[error_type][-100:]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        total_errors = sum(self.error_counts.values())
        
        return {
            "total_errors": total_errors,
            "error_types": self.error_counts,
            "recent_errors": {
                error_type: errors[-5:]  # Last 5 errors per type
                for error_type, errors in self.errors.items()
            }
        }
    
    def clear_stats(self) -> None:
        """Clear error statistics"""
        self.errors.clear()
        self.error_counts.clear()
        logger.info("Error statistics cleared")

# Global error tracker instance
error_tracker = ErrorTracker()