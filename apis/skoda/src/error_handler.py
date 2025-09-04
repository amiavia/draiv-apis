"""
Skoda Connect Error Handler
Centralized error handling and custom exception classes for Skoda Connect API
"""
import logging
from typing import Dict, Any, Optional, Tuple
from flask import jsonify
from datetime import datetime

logger = logging.getLogger(__name__)

class SkodaAPIError(Exception):
    """Base exception for Skoda Connect API errors"""
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or "SKODA_API_ERROR"
        super().__init__(self.message)

class ValidationError(SkodaAPIError):
    """Raised when request validation fails"""
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")

class AuthenticationError(SkodaAPIError):
    """Raised when authentication fails"""
    def __init__(self, message: str):
        super().__init__(message, "AUTHENTICATION_ERROR")

class RemoteServiceError(SkodaAPIError):
    """Raised when remote service operation fails"""
    def __init__(self, message: str):
        super().__init__(message, "REMOTE_SERVICE_ERROR")

class VehicleNotFoundError(SkodaAPIError):
    """Raised when vehicle is not found"""
    def __init__(self, message: str):
        super().__init__(message, "VEHICLE_NOT_FOUND")

class RateLimitError(SkodaAPIError):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str):
        super().__init__(message, "RATE_LIMIT_EXCEEDED")

class ExternalServiceError(SkodaAPIError):
    """Raised when external service (Skoda Connect API) is unavailable"""
    def __init__(self, message: str):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR")

class SPinValidationError(SkodaAPIError):
    """Raised when S-PIN validation fails"""
    def __init__(self, message: str):
        super().__init__(message, "SPIN_VALIDATION_ERROR")

class VehicleCapabilityError(SkodaAPIError):
    """Raised when vehicle doesn't support requested capability"""
    def __init__(self, message: str):
        super().__init__(message, "VEHICLE_CAPABILITY_ERROR")

class CircuitBreakerError(SkodaAPIError):
    """Raised when circuit breaker is open"""
    def __init__(self, message: str):
        super().__init__(message, "CIRCUIT_BREAKER_OPEN")

def handle_api_error(error: Exception, status_code: int) -> Tuple[Any, int, Dict[str, str]]:
    """
    Handle API errors and return formatted response
    
    Args:
        error: The exception to handle
        status_code: HTTP status code to return
        
    Returns:
        Tuple of (response, status_code, headers)
    """
    # Log the error with appropriate level
    if status_code >= 500:
        logger.error(f"Server error: {error}", exc_info=True)
    elif status_code >= 400:
        logger.warning(f"Client error: {error}")
    else:
        logger.info(f"API response: {error}")
    
    # Prepare error response
    error_response = {
        "success": False,
        "error": {
            "message": str(error),
            "code": getattr(error, "code", "UNKNOWN_ERROR"),
            "timestamp": datetime.now().isoformat(),
            "api_provider": "skoda_connect"
        }
    }
    
    # Add additional context for specific errors
    if isinstance(error, ValidationError):
        error_response["error"]["type"] = "validation"
        error_response["error"]["details"] = "Please check your request parameters"
        error_response["error"]["suggestions"] = [
            "Verify VIN format (17 characters)",
            "Check required fields",
            "Validate data types"
        ]
    elif isinstance(error, AuthenticationError):
        error_response["error"]["type"] = "authentication"
        error_response["error"]["details"] = "Please verify your credentials"
        error_response["error"]["suggestions"] = [
            "Check username and password",
            "Verify account is active",
            "Try logging in via Skoda Connect app first"
        ]
    elif isinstance(error, RemoteServiceError):
        error_response["error"]["type"] = "remote_service"
        error_response["error"]["details"] = "The remote operation could not be completed"
        error_response["error"]["suggestions"] = [
            "Check vehicle connectivity",
            "Try again in a few minutes",
            "Ensure vehicle is awake"
        ]
    elif isinstance(error, VehicleNotFoundError):
        error_response["error"]["type"] = "vehicle_not_found"
        error_response["error"]["details"] = "Vehicle not found in your account"
        error_response["error"]["suggestions"] = [
            "Verify VIN is correct",
            "Check if vehicle is registered to your account",
            "Contact Skoda Connect support if issue persists"
        ]
    elif isinstance(error, RateLimitError):
        error_response["error"]["type"] = "rate_limit"
        error_response["error"]["details"] = "Too many requests. Please try again later"
        error_response["error"]["suggestions"] = [
            "Wait 60 seconds before retrying",
            "Reduce request frequency",
            "Contact support if you need higher limits"
        ]
    elif isinstance(error, ExternalServiceError):
        error_response["error"]["type"] = "external_service"
        error_response["error"]["details"] = "Skoda Connect services are temporarily unavailable"
        error_response["error"]["suggestions"] = [
            "Check Skoda Connect service status",
            "Try again in 5-10 minutes",
            "Use Skoda Connect mobile app as alternative"
        ]
    elif isinstance(error, SPinValidationError):
        error_response["error"]["type"] = "spin_validation"
        error_response["error"]["details"] = "S-PIN verification failed"
        error_response["error"]["suggestions"] = [
            "Check S-PIN is correct",
            "Verify S-PIN in Skoda Connect app",
            "Contact dealer if PIN is forgotten"
        ]
    elif isinstance(error, VehicleCapabilityError):
        error_response["error"]["type"] = "vehicle_capability"
        error_response["error"]["details"] = "Vehicle doesn't support this feature"
        error_response["error"]["suggestions"] = [
            "Check vehicle model capabilities",
            "Verify feature is available for your vehicle",
            "Contact dealer for feature upgrades"
        ]
    elif isinstance(error, CircuitBreakerError):
        error_response["error"]["type"] = "circuit_breaker"
        error_response["error"]["details"] = "Service temporarily unavailable due to repeated failures"
        error_response["error"]["suggestions"] = [
            "Service will retry automatically",
            "Check Skoda Connect service status",
            "Contact support if issue persists"
        ]
    
    # CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Content-Type": "application/json"
    }
    
    return (jsonify(error_response), status_code, headers)

class SkodaErrorTracker:
    """Track and analyze errors for monitoring and alerting"""
    
    def __init__(self, max_errors_per_type: int = 100):
        self.errors: Dict[str, List[Dict[str, Any]]] = {}
        self.error_counts: Dict[str, int] = {}
        self.max_errors_per_type = max_errors_per_type
    
    def track_error(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None,
        vin: Optional[str] = None
    ) -> None:
        """
        Track an error occurrence with context
        
        Args:
            error: The exception to track
            context: Optional context information (endpoint, user, etc.)
            vin: Optional vehicle VIN for vehicle-specific errors
        """
        error_type = type(error).__name__
        error_code = getattr(error, "code", "UNKNOWN")
        
        # Update error count
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Store error details
        if error_type not in self.errors:
            self.errors[error_type] = []
        
        error_entry = {
            "message": str(error),
            "code": error_code,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            "vin": vin,
            "count": self.error_counts[error_type]
        }
        
        self.errors[error_type].append(error_entry)
        
        # Keep only the most recent errors per type
        if len(self.errors[error_type]) > self.max_errors_per_type:
            self.errors[error_type] = self.errors[error_type][-self.max_errors_per_type:]
        
        # Log high-priority errors
        if isinstance(error, (ExternalServiceError, CircuitBreakerError)):
            logger.error(f"High priority error tracked: {error_type} - {error}")
        elif self.error_counts[error_type] % 10 == 0:  # Log every 10th occurrence
            logger.warning(f"Recurring error: {error_type} occurred {self.error_counts[error_type]} times")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        total_errors = sum(self.error_counts.values())
        
        # Calculate error rates
        most_common_errors = sorted(
            self.error_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Get recent errors across all types
        recent_errors = []
        for error_type, errors in self.errors.items():
            recent_errors.extend(errors[-3:])  # Last 3 errors per type
        
        # Sort by timestamp
        recent_errors.sort(key=lambda x: x["timestamp"], reverse=True)
        recent_errors = recent_errors[:10]  # Top 10 most recent
        
        return {
            "total_errors": total_errors,
            "unique_error_types": len(self.error_counts),
            "error_counts_by_type": dict(self.error_counts),
            "most_common_errors": most_common_errors,
            "recent_errors": recent_errors,
            "statistics_generated": datetime.now().isoformat()
        }
    
    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get error trends for the specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_iso = cutoff_time.isoformat()
        
        trends = {}
        for error_type, errors in self.errors.items():
            recent_errors = [
                e for e in errors 
                if e["timestamp"] >= cutoff_iso
            ]
            trends[error_type] = {
                "count": len(recent_errors),
                "rate_per_hour": len(recent_errors) / hours,
                "latest": recent_errors[-1]["timestamp"] if recent_errors else None
            }
        
        return {
            "period_hours": hours,
            "trends_by_type": trends,
            "generated": datetime.now().isoformat()
        }
    
    def clear_stats(self) -> None:
        """Clear all error statistics"""
        self.errors.clear()
        self.error_counts.clear()
        logger.info("Skoda error statistics cleared")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall service health based on error patterns"""
        total_errors = sum(self.error_counts.values())
        
        # Define health thresholds
        critical_errors = self.error_counts.get("CircuitBreakerError", 0)
        external_service_errors = self.error_counts.get("ExternalServiceError", 0)
        auth_errors = self.error_counts.get("AuthenticationError", 0)
        
        # Determine health status
        if critical_errors > 5 or external_service_errors > 10:
            health_status = "critical"
            health_message = "Multiple service failures detected"
        elif auth_errors > 20 or total_errors > 50:
            health_status = "warning"
            health_message = "Elevated error rates detected"
        elif total_errors > 0:
            health_status = "degraded"
            health_message = "Some errors present but service operational"
        else:
            health_status = "healthy"
            health_message = "No errors detected"
        
        return {
            "status": health_status,
            "message": health_message,
            "total_errors": total_errors,
            "critical_error_count": critical_errors,
            "timestamp": datetime.now().isoformat()
        }

# Global error tracker instance
error_tracker = SkodaErrorTracker()

# Convenience function for error handling in endpoints
def handle_endpoint_error(
    error: Exception, 
    endpoint: str,
    vin: Optional[str] = None,
    user_id: Optional[str] = None
) -> Tuple[Any, int, Dict[str, str]]:
    """
    Handle errors in API endpoints with automatic tracking
    
    Args:
        error: The exception to handle
        endpoint: The API endpoint where error occurred
        vin: Optional vehicle VIN
        user_id: Optional user identifier
        
    Returns:
        Tuple of (response, status_code, headers)
    """
    context = {
        "endpoint": endpoint,
        "user_id": user_id
    }
    
    # Track the error
    error_tracker.track_error(error, context, vin)
    
    # Determine appropriate status code
    if isinstance(error, ValidationError):
        status_code = 400
    elif isinstance(error, AuthenticationError):
        status_code = 401
    elif isinstance(error, VehicleNotFoundError):
        status_code = 404
    elif isinstance(error, RateLimitError):
        status_code = 429
    elif isinstance(error, (ExternalServiceError, CircuitBreakerError)):
        status_code = 503
    elif isinstance(error, (RemoteServiceError, SPinValidationError, VehicleCapabilityError)):
        status_code = 422
    else:
        status_code = 500
    
    return handle_api_error(error, status_code)