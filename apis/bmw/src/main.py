"""
BMW API Cloud Function - Production Ready Implementation
Enhanced with circuit breaker, caching, monitoring, and proper error handling
"""
import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, Request, jsonify
import functions_framework
from google.cloud import storage, secretmanager

from auth_manager import BMWAuthManager
from vehicle_manager import BMWVehicleManager
from remote_services import BMWRemoteServices
from utils.circuit_breaker import CircuitBreaker
from utils.cache_manager import CacheManager
from utils.error_handler import (
    BMWAPIError, 
    handle_api_error,
    ValidationError,
    AuthenticationError,
    RemoteServiceError
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BUCKET_NAME = os.environ.get("BMW_OAUTH_BUCKET", "bmw-api-bucket")
PROJECT_ID = os.environ.get("GCP_PROJECT", "miavia-422212")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")

# Initialize components
app = Flask(__name__)
cache_manager = CacheManager()
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=BMWAPIError
)

class BMWAPIService:
    """Main service class for BMW API operations"""
    
    def __init__(self):
        self.auth_manager = BMWAuthManager(BUCKET_NAME)
        self.vehicle_manager = BMWVehicleManager()
        self.remote_services = BMWRemoteServices()
        self.metrics = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "avg_response_time": 0
        }
    
    async def process_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming BMW API request with proper error handling and monitoring
        """
        start_time = datetime.now()
        self.metrics["requests_total"] += 1
        
        try:
            # Validate request
            self._validate_request(data)
            
            # Extract parameters
            email = data["email"]
            password = data["password"]
            wkn = data["wkn"]
            action = data.get("action", "status")
            hcaptcha_token = data.get("hcaptcha")
            
            # Check cache for recent results (for read-only operations)
            cache_key = f"{email}:{wkn}:{action}"
            if action in ["status", "fuel", "location", "mileage", "lock_status", "is_locked"]:
                cached_result = cache_manager.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for {action} request")
                    self.metrics["requests_success"] += 1
                    return cached_result
            
            # Authenticate with circuit breaker protection
            account = await circuit_breaker.call(
                self.auth_manager.authenticate,
                email, password, hcaptcha_token
            )
            
            # Get vehicle
            vehicle = await self.vehicle_manager.get_vehicle(account, wkn)
            
            # Process action
            result = await self._process_action(vehicle, action)
            
            # Prepare response
            response_data = {
                "success": True,
                "brand": vehicle.brand,
                "vehicle_name": vehicle.name,
                "vin": vehicle.vin,
                "action": action,
                "result": result,
                "timestamp": datetime.now().isoformat(),
                "environment": ENVIRONMENT
            }
            
            # Cache successful read-only operations
            if action in ["status", "fuel", "location", "mileage", "lock_status", "is_locked"]:
                cache_manager.set(cache_key, response_data, ttl=300)  # 5 minutes cache
            
            # Update metrics
            self.metrics["requests_success"] += 1
            response_time = (datetime.now() - start_time).total_seconds()
            self._update_avg_response_time(response_time)
            
            logger.info(f"Successfully processed {action} request in {response_time:.2f}s")
            return response_data
            
        except ValidationError as e:
            self.metrics["requests_failed"] += 1
            logger.warning(f"Validation error: {e}")
            raise
        except AuthenticationError as e:
            self.metrics["requests_failed"] += 1
            logger.error(f"Authentication error: {e}")
            raise
        except Exception as e:
            self.metrics["requests_failed"] += 1
            logger.error(f"Unexpected error processing request: {e}", exc_info=True)
            raise BMWAPIError(f"Failed to process request: {str(e)}")
    
    def _validate_request(self, data: Dict[str, Any]) -> None:
        """Validate incoming request data"""
        required_fields = ["email", "password", "wkn"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate email format
        email = data.get("email", "")
        if not email or "@" not in email:
            raise ValidationError("Invalid email format")
        
        # Validate WKN format (should be alphanumeric)
        wkn = data.get("wkn", "")
        if not wkn or not wkn.isalnum():
            raise ValidationError("Invalid WKN format")
        
        # Validate action if provided
        valid_actions = [
            "status", "lock", "unlock", "flash", "ac", "fuel", 
            "location", "check_control", "mileage", "lock_status", "is_locked"
        ]
        action = data.get("action", "status")
        if action not in valid_actions:
            raise ValidationError(f"Invalid action: {action}. Valid actions: {', '.join(valid_actions)}")
    
    async def _process_action(self, vehicle: Any, action: str) -> Dict[str, Any]:
        """Process the requested action on the vehicle"""
        
        # Remote control actions
        if action == "lock":
            return await self.remote_services.lock_vehicle(vehicle)
        elif action == "unlock":
            return await self.remote_services.unlock_vehicle(vehicle)
        elif action == "flash":
            return await self.remote_services.flash_lights(vehicle)
        elif action == "ac":
            return await self.remote_services.activate_climate(vehicle)
        
        # Status queries
        elif action == "fuel":
            return self.vehicle_manager.get_fuel_status(vehicle)
        elif action == "location":
            return self.vehicle_manager.get_location(vehicle)
        elif action == "check_control":
            return self.vehicle_manager.get_check_control_messages(vehicle)
        elif action == "mileage":
            return self.vehicle_manager.get_mileage(vehicle)
        elif action == "lock_status":
            return self.vehicle_manager.get_lock_status(vehicle)
        elif action == "is_locked":
            return self.vehicle_manager.is_locked(vehicle)
        else:
            # Default to returning vehicle status
            return self.vehicle_manager.get_full_status(vehicle)
    
    def _update_avg_response_time(self, response_time: float) -> None:
        """Update average response time metric"""
        total_requests = self.metrics["requests_success"]
        if total_requests == 1:
            self.metrics["avg_response_time"] = response_time
        else:
            # Calculate running average
            current_avg = self.metrics["avg_response_time"]
            self.metrics["avg_response_time"] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current service metrics"""
        return {
            **self.metrics,
            "circuit_breaker_state": circuit_breaker.state,
            "cache_size": cache_manager.size(),
            "timestamp": datetime.now().isoformat()
        }

# Initialize service
bmw_service = BMWAPIService()

@functions_framework.http
def bmw_api(request: Request):
    """
    Main Cloud Function entry point for BMW API
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600"
        }
        return ("", 204, headers)
    
    # Handle health check
    if request.method == "GET" and request.path == "/health":
        return jsonify({
            "status": "healthy",
            "service": "bmw-api",
            "version": "2.0.0",
            "environment": ENVIRONMENT,
            "metrics": bmw_service.get_metrics()
        })
    
    # Handle metrics endpoint
    if request.method == "GET" and request.path == "/metrics":
        return jsonify(bmw_service.get_metrics())
    
    # Process BMW API request
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            raise ValidationError("Request body must be valid JSON")
        
        # Process request asynchronously
        result = asyncio.run(bmw_service.process_request(data))
        
        # Return successful response
        headers = {"Access-Control-Allow-Origin": "*"}
        return (jsonify(result), 200, headers)
        
    except ValidationError as e:
        return handle_api_error(e, 400)
    except AuthenticationError as e:
        return handle_api_error(e, 401)
    except RemoteServiceError as e:
        return handle_api_error(e, 503)
    except BMWAPIError as e:
        return handle_api_error(e, 500)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return handle_api_error(
            BMWAPIError(f"Internal server error: {str(e)}"), 
            500
        )

# Local development server
if __name__ == "__main__":
    import sys
    
    # Set up local environment
    os.environ["ENVIRONMENT"] = "development"
    
    # Run Flask app
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        debug=True
    )