"""
Skoda Connect API Main Application
FastAPI application providing Skoda Connect vehicle integration
"""
import os
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from vehicle_manager import SkodaVehicleManager
from auth_manager import SkodaAuthManager
from error_handler import handle_endpoint_error, error_tracker
from models import (
    AuthenticationRequest, VehicleStatusRequest, LocationRequest,
    TripStatisticsRequest, VehicleListResponse, VehicleStatusResponse,
    LocationResponse, TripStatisticsResponse, ChargingStatusResponse,
    ServiceIntervalResponse, CapabilitiesResponse, HealthResponse,
    ErrorResponse
)
from utils.cache_manager import SkodaCacheManager
from utils.circuit_breaker import CircuitBreaker

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global application state
app_state = {
    "vehicle_manager": None,
    "auth_manager": None,
    "startup_time": None
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Skoda Connect API...")
    app_state["startup_time"] = datetime.now()
    
    # Initialize components
    try:
        # Initialize cache manager
        cache_manager = SkodaCacheManager(
            redis_url=os.getenv("REDIS_URL"),
            key_prefix="skoda:"
        )
        
        # Initialize circuit breaker
        circuit_breaker = CircuitBreaker(
            failure_threshold=int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5")),
            recovery_timeout=int(os.getenv("CIRCUIT_BREAKER_RECOVERY", "60")),
            name="SkodaAPI"
        )
        
        # Initialize auth manager
        app_state["auth_manager"] = SkodaAuthManager(
            bucket_name=os.getenv("GCS_BUCKET", "skoda-oauth-tokens"),
            cache_manager=cache_manager
        )
        
        # Initialize vehicle manager
        app_state["vehicle_manager"] = SkodaVehicleManager(
            cache_manager=cache_manager,
            circuit_breaker=circuit_breaker
        )
        
        logger.info("Skoda Connect API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Skoda Connect API...")
    # Cleanup if needed
    logger.info("Shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Skoda Connect API",
    description="Production-ready API for Skoda Connect vehicle integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency injection
async def get_vehicle_manager() -> SkodaVehicleManager:
    """Get vehicle manager instance"""
    if not app_state["vehicle_manager"]:
        raise HTTPException(status_code=503, detail="Service not ready")
    return app_state["vehicle_manager"]

async def get_auth_manager() -> SkodaAuthManager:
    """Get auth manager instance"""
    if not app_state["auth_manager"]:
        raise HTTPException(status_code=503, detail="Service not ready")
    return app_state["auth_manager"]

# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """
    Health check endpoint
    
    Returns service health status and basic metrics
    """
    try:
        uptime = None
        if app_state["startup_time"]:
            uptime = int((datetime.now() - app_state["startup_time"]).total_seconds())
        
        cache_stats = await vehicle_manager.get_cache_stats()
        error_stats = error_tracker.get_health_status()
        
        return HealthResponse(
            status="healthy",
            uptime_seconds=uptime,
            cache_stats=cache_stats,
            error_stats=error_stats
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            uptime_seconds=uptime
        )

# Authentication endpoints
@app.post("/auth/login", response_model=Dict[str, str], tags=["Authentication"])
async def authenticate_user(
    request: AuthenticationRequest,
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """
    Authenticate with Skoda Connect
    
    Authenticates user credentials and initializes session
    """
    try:
        success = await vehicle_manager.initialize(
            request.username, 
            request.password
        )
        
        if success:
            return {
                "status": "success",
                "message": "Authentication successful",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
            
    except Exception as e:
        response, status_code, headers = handle_endpoint_error(
            e, "/auth/login", user_id=request.username
        )
        raise HTTPException(status_code=status_code, detail=response.json)

# Vehicle management endpoints
@app.get("/vehicles", response_model=VehicleListResponse, tags=["Vehicles"])
async def get_vehicles(
    force_refresh: bool = False,
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """
    Get list of user's vehicles
    
    Returns all vehicles associated with the authenticated user
    """
    try:
        vehicles = await vehicle_manager.get_vehicles(force_refresh=force_refresh)
        
        return VehicleListResponse(
            success=True,
            vehicles=vehicles,
            count=len(vehicles)
        )
        
    except Exception as e:
        response, status_code, headers = handle_endpoint_error(e, "/vehicles")
        raise HTTPException(status_code=status_code, detail=response.json)

@app.get("/vehicles/{vin}/status", response_model=VehicleStatusResponse, tags=["Vehicles"])
async def get_vehicle_status(
    vin: str,
    force_refresh: bool = False,
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """
    Get comprehensive vehicle status
    
    Returns detailed status information for the specified vehicle
    """
    try:
        status = await vehicle_manager.get_vehicle_status(
            vin=vin.upper(),
            force_refresh=force_refresh
        )
        
        return VehicleStatusResponse(
            success=True,
            vehicle=status
        )
        
    except Exception as e:
        response, status_code, headers = handle_endpoint_error(
            e, f"/vehicles/{vin}/status", vin=vin
        )
        raise HTTPException(status_code=status_code, detail=response.json)

@app.get("/vehicles/{vin}/location", response_model=LocationResponse, tags=["Location"])
async def get_vehicle_location(
    vin: str,
    include_address: bool = True,
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """
    Get vehicle location
    
    Returns GPS coordinates and optional address resolution
    """
    try:
        location = await vehicle_manager.get_vehicle_location(
            vin=vin.upper(),
            include_address=include_address
        )
        
        return LocationResponse(
            success=True,
            vin=vin.upper(),
            location=location
        )
        
    except Exception as e:
        response, status_code, headers = handle_endpoint_error(
            e, f"/vehicles/{vin}/location", vin=vin
        )
        raise HTTPException(status_code=status_code, detail=response.json)

@app.get("/vehicles/{vin}/trips", response_model=TripStatisticsResponse, tags=["Statistics"])
async def get_trip_statistics(
    vin: str,
    days: int = 30,
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """
    Get vehicle trip statistics
    
    Returns trip history and statistics for the specified period
    """
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
        
        statistics = await vehicle_manager.get_trip_statistics(
            vin=vin.upper(),
            days=days
        )
        
        return TripStatisticsResponse(
            success=True,
            vin=vin.upper(),
            statistics=statistics
        )
        
    except Exception as e:
        response, status_code, headers = handle_endpoint_error(
            e, f"/vehicles/{vin}/trips", vin=vin
        )
        raise HTTPException(status_code=status_code, detail=response.json)

@app.get("/vehicles/{vin}/charging", response_model=ChargingStatusResponse, tags=["Electric Vehicles"])
async def get_charging_status(
    vin: str,
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """
    Get EV charging status
    
    Returns battery and charging information for electric vehicles
    """
    try:
        charging = await vehicle_manager.get_charging_status(vin=vin.upper())
        
        return ChargingStatusResponse(
            success=True,
            vin=vin.upper(),
            charging=charging
        )
        
    except Exception as e:
        response, status_code, headers = handle_endpoint_error(
            e, f"/vehicles/{vin}/charging", vin=vin
        )
        raise HTTPException(status_code=status_code, detail=response.json)

@app.get("/vehicles/{vin}/service", response_model=ServiceIntervalResponse, tags=["Service"])
async def get_service_intervals(
    vin: str,
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """
    Get vehicle service intervals
    
    Returns maintenance schedule and service information
    """
    try:
        service = await vehicle_manager.get_service_intervals(vin=vin.upper())
        
        return ServiceIntervalResponse(
            success=True,
            vin=vin.upper(),
            service=service
        )
        
    except Exception as e:
        response, status_code, headers = handle_endpoint_error(
            e, f"/vehicles/{vin}/service", vin=vin
        )
        raise HTTPException(status_code=status_code, detail=response.json)

@app.get("/vehicles/{vin}/capabilities", response_model=CapabilitiesResponse, tags=["Vehicles"])
async def get_vehicle_capabilities(
    vin: str,
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """
    Get vehicle capabilities
    
    Returns list of features supported by the vehicle
    """
    try:
        capabilities = await vehicle_manager.detect_vehicle_capabilities(vin=vin.upper())
        
        return CapabilitiesResponse(
            success=True,
            vin=vin.upper(),
            capabilities=capabilities
        )
        
    except Exception as e:
        response, status_code, headers = handle_endpoint_error(
            e, f"/vehicles/{vin}/capabilities", vin=vin
        )
        raise HTTPException(status_code=status_code, detail=response.json)

# Admin/monitoring endpoints
@app.get("/admin/cache/stats", tags=["Admin"])
async def get_cache_stats(
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """Get cache statistics"""
    try:
        return await vehicle_manager.get_cache_stats()
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache statistics")

@app.get("/admin/errors/stats", tags=["Admin"])
async def get_error_stats():
    """Get error statistics"""
    try:
        return error_tracker.get_error_stats()
    except Exception as e:
        logger.error(f"Failed to get error stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error statistics")

@app.post("/admin/cache/clear", tags=["Admin"])
async def clear_cache(
    vin: Optional[str] = None,
    vehicle_manager: SkodaVehicleManager = Depends(get_vehicle_manager)
):
    """Clear cache (all or specific VIN)"""
    try:
        await vehicle_manager.clear_cache(vin)
        return {
            "status": "success",
            "message": f"Cache cleared{'for VIN: ' + vin if vin else ' (all)'}"
        }
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": exc.detail,
                "code": f"HTTP_{exc.status_code}",
                "timestamp": datetime.now().isoformat()
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "message": "Internal server error",
                "code": "INTERNAL_SERVER_ERROR",
                "timestamp": datetime.now().isoformat()
            }
        }
    )

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=os.getenv("ENV") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )