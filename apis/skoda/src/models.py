"""
Skoda Connect API Data Models
Pydantic models for request/response validation and type safety
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator
import re

class VehicleType(str, Enum):
    """Vehicle type classification"""
    ICE = "ice"  # Internal combustion engine
    EV = "electric"  # Battery electric vehicle
    HYBRID = "hybrid"  # Hybrid vehicle
    PHEV = "plug_in_hybrid"  # Plug-in hybrid
    UNKNOWN = "unknown"

class ChargingState(str, Enum):
    """EV charging states"""
    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"
    CHARGING = "charging"
    CHARGE_PURPOSE_REACHED = "charge_purpose_reached"
    CONSERVATION = "conservation"
    ERROR = "error"
    UNKNOWN = "unknown"

class LockState(str, Enum):
    """Vehicle lock states"""
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    PARTIAL = "partial"
    UNKNOWN = "unknown"

class ClimateState(str, Enum):
    """Climate control states"""
    OFF = "off"
    HEATING = "heating"
    COOLING = "cooling"
    VENTILATION = "ventilation"
    UNKNOWN = "unknown"

# Request Models

class AuthenticationRequest(BaseModel):
    """Authentication request model"""
    username: str = Field(..., min_length=1, description="Skoda Connect username/email")
    password: str = Field(..., min_length=1, description="Skoda Connect password")
    force_refresh: bool = Field(False, description="Force fresh authentication")
    
    @validator('username')
    def validate_username(cls, v):
        if '@' in v and len(v.split('@')) == 2:
            return v.lower().strip()
        return v.strip()

class VehicleStatusRequest(BaseModel):
    """Vehicle status request model"""
    vin: str = Field(..., min_length=17, max_length=17, description="Vehicle VIN")
    force_refresh: bool = Field(False, description="Bypass cache and fetch fresh data")
    
    @validator('vin')
    def validate_vin(cls, v):
        vin = v.upper().strip()
        if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
            raise ValueError('VIN must be 17 characters, alphanumeric (no I, O, Q)')
        return vin

class LocationRequest(BaseModel):
    """Vehicle location request model"""
    vin: str = Field(..., min_length=17, max_length=17, description="Vehicle VIN")
    include_address: bool = Field(True, description="Resolve coordinates to address")
    
    @validator('vin')
    def validate_vin(cls, v):
        vin = v.upper().strip()
        if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
            raise ValueError('VIN must be 17 characters, alphanumeric (no I, O, Q)')
        return vin

class TripStatisticsRequest(BaseModel):
    """Trip statistics request model"""
    vin: str = Field(..., min_length=17, max_length=17, description="Vehicle VIN")
    days: int = Field(30, ge=1, le=365, description="Number of days to include")
    
    @validator('vin')
    def validate_vin(cls, v):
        vin = v.upper().strip()
        if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
            raise ValueError('VIN must be 17 characters, alphanumeric (no I, O, Q)')
        return vin

class RemoteCommandRequest(BaseModel):
    """Base model for remote commands"""
    vin: str = Field(..., min_length=17, max_length=17, description="Vehicle VIN")
    spin: Optional[str] = Field(None, description="S-PIN for secure operations")
    
    @validator('vin')
    def validate_vin(cls, v):
        vin = v.upper().strip()
        if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
            raise ValueError('VIN must be 17 characters, alphanumeric (no I, O, Q)')
        return vin
    
    @validator('spin')
    def validate_spin(cls, v):
        if v is not None:
            if not re.match(r'^\d{4}$', v):
                raise ValueError('S-PIN must be 4 digits')
        return v

# Response Models

class Coordinates(BaseModel):
    """GPS coordinates model"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")

class Address(BaseModel):
    """Address model"""
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country: Optional[str] = Field(None, description="Country name")
    formatted_address: Optional[str] = Field(None, description="Complete formatted address")

class VehicleInfo(BaseModel):
    """Basic vehicle information model"""
    vin: str = Field(..., description="Vehicle VIN")
    brand: str = Field("Skoda", description="Vehicle brand")
    model: str = Field(..., description="Vehicle model")
    year: Optional[Union[str, int]] = Field(None, description="Model year")
    name: str = Field(..., description="Vehicle display name")
    license_plate: Optional[str] = Field(None, description="License plate number")
    color: Optional[str] = Field(None, description="Vehicle color")
    vehicle_type: VehicleType = Field(VehicleType.UNKNOWN, description="Vehicle type classification")

class BatteryStatus(BaseModel):
    """EV battery status model"""
    level_percent: Optional[int] = Field(None, ge=0, le=100, description="Battery level percentage")
    range_km: Optional[int] = Field(None, ge=0, description="Electric range in kilometers")
    charging_state: ChargingState = Field(ChargingState.UNKNOWN, description="Current charging state")
    charging_power_kw: Optional[float] = Field(None, ge=0, description="Charging power in kW")
    time_to_full_minutes: Optional[int] = Field(None, ge=0, description="Time to full charge in minutes")
    target_level_percent: Optional[int] = Field(None, ge=0, le=100, description="Target charge level")

class FuelStatus(BaseModel):
    """Fuel status model for ICE vehicles"""
    level_percent: Optional[int] = Field(None, ge=0, le=100, description="Fuel level percentage")
    range_km: Optional[int] = Field(None, ge=0, description="Fuel range in kilometers")
    consumption_l_100km: Optional[float] = Field(None, ge=0, description="Average consumption L/100km")

class EnergyStatus(BaseModel):
    """Combined energy status model"""
    vehicle_type: VehicleType = Field(..., description="Vehicle type")
    battery: Optional[BatteryStatus] = Field(None, description="Battery status for EVs")
    fuel: Optional[FuelStatus] = Field(None, description="Fuel status for ICE vehicles")
    total_range_km: Optional[int] = Field(None, ge=0, description="Total vehicle range")

class LocationData(BaseModel):
    """Vehicle location data model"""
    available: bool = Field(..., description="Whether location data is available")
    coordinates: Optional[Coordinates] = Field(None, description="GPS coordinates")
    address: Optional[Address] = Field(None, description="Resolved address")
    timestamp: Optional[datetime] = Field(None, description="Location timestamp")
    accuracy_meters: Optional[int] = Field(None, ge=0, description="Location accuracy in meters")

class DoorsWindowsStatus(BaseModel):
    """Doors and windows status model"""
    available: bool = Field(..., description="Whether door/window data is available")
    locked: LockState = Field(LockState.UNKNOWN, description="Lock state")
    doors_closed: Optional[bool] = Field(None, description="All doors closed")
    windows_closed: Optional[bool] = Field(None, description="All windows closed")
    trunk_closed: Optional[bool] = Field(None, description="Trunk closed")
    hood_closed: Optional[bool] = Field(None, description="Hood closed")

class ClimateStatus(BaseModel):
    """Climate control status model"""
    available: bool = Field(..., description="Whether climate data is available")
    state: ClimateState = Field(ClimateState.UNKNOWN, description="Current climate state")
    target_temperature_celsius: Optional[int] = Field(None, ge=-20, le=40, description="Target temperature")
    remaining_time_minutes: Optional[int] = Field(None, ge=0, description="Remaining runtime")
    defrost_active: Optional[bool] = Field(None, description="Defrost active")

class ServiceInterval(BaseModel):
    """Service interval model"""
    name: str = Field(..., description="Service name")
    next_service_km: Optional[int] = Field(None, ge=0, description="Next service mileage")
    next_service_days: Optional[int] = Field(None, ge=0, description="Next service days")
    overdue: bool = Field(False, description="Whether service is overdue")

class ServiceInfo(BaseModel):
    """Service information model"""
    available: bool = Field(..., description="Whether service data is available")
    intervals: List[ServiceInterval] = Field(default_factory=list, description="Service intervals")
    last_service_km: Optional[int] = Field(None, ge=0, description="Last service mileage")
    next_inspection_km: Optional[int] = Field(None, ge=0, description="Next inspection mileage")

class Trip(BaseModel):
    """Individual trip model"""
    start_time: datetime = Field(..., description="Trip start time")
    end_time: Optional[datetime] = Field(None, description="Trip end time")
    distance_km: float = Field(..., ge=0, description="Trip distance in kilometers")
    duration_minutes: Optional[int] = Field(None, ge=0, description="Trip duration in minutes")
    consumption: Optional[float] = Field(None, ge=0, description="Trip consumption")
    start_location: Optional[Address] = Field(None, description="Start location")
    end_location: Optional[Address] = Field(None, description="End location")

class TripStatistics(BaseModel):
    """Trip statistics model"""
    period_start: datetime = Field(..., description="Statistics period start")
    period_end: datetime = Field(..., description="Statistics period end")
    total_distance_km: float = Field(..., ge=0, description="Total distance")
    total_trips: int = Field(..., ge=0, description="Total number of trips")
    avg_consumption: Optional[float] = Field(None, ge=0, description="Average consumption")
    avg_trip_distance_km: Optional[float] = Field(None, ge=0, description="Average trip distance")
    trips: List[Trip] = Field(default_factory=list, description="Individual trips")

class VehicleStatus(BaseModel):
    """Comprehensive vehicle status model"""
    vin: str = Field(..., description="Vehicle VIN")
    vehicle_info: VehicleInfo = Field(..., description="Basic vehicle information")
    energy: EnergyStatus = Field(..., description="Energy status (fuel/battery)")
    location: LocationData = Field(..., description="Location data")
    doors_windows: DoorsWindowsStatus = Field(..., description="Doors and windows status")
    climate: ClimateStatus = Field(..., description="Climate control status")
    service_info: ServiceInfo = Field(..., description="Service information")
    capabilities: List[str] = Field(default_factory=list, description="Vehicle capabilities")
    last_updated: datetime = Field(..., description="Last update timestamp")
    api_provider: str = Field("skoda_connect", description="API provider")

class VehicleListItem(BaseModel):
    """Vehicle list item model"""
    vin: str = Field(..., description="Vehicle VIN")
    brand: str = Field("Skoda", description="Vehicle brand")
    model: str = Field(..., description="Vehicle model")
    name: str = Field(..., description="Vehicle display name")
    license_plate: Optional[str] = Field(None, description="License plate")
    vehicle_type: VehicleType = Field(VehicleType.UNKNOWN, description="Vehicle type")
    capabilities: List[str] = Field(default_factory=list, description="Vehicle capabilities")

class CommandResponse(BaseModel):
    """Remote command response model"""
    command_id: str = Field(..., description="Unique command identifier")
    vin: str = Field(..., description="Vehicle VIN")
    operation: str = Field(..., description="Command operation")
    status: str = Field(..., description="Command status")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(..., description="Response timestamp")

# API Response Models

class APIResponse(BaseModel):
    """Base API response model"""
    success: bool = Field(..., description="Operation success status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    api_provider: str = Field("skoda_connect", description="API provider")

class ErrorResponse(APIResponse):
    """Error response model"""
    success: bool = Field(False, description="Always false for errors")
    error: Dict[str, Any] = Field(..., description="Error details")

class VehicleListResponse(APIResponse):
    """Vehicle list response model"""
    vehicles: List[VehicleListItem] = Field(..., description="List of vehicles")
    count: int = Field(..., ge=0, description="Number of vehicles")
    
    @root_validator
    def validate_count(cls, values):
        vehicles = values.get('vehicles', [])
        values['count'] = len(vehicles)
        return values

class VehicleStatusResponse(APIResponse):
    """Vehicle status response model"""
    vehicle: VehicleStatus = Field(..., description="Vehicle status data")

class LocationResponse(APIResponse):
    """Location response model"""
    vin: str = Field(..., description="Vehicle VIN")
    location: LocationData = Field(..., description="Location data")

class TripStatisticsResponse(APIResponse):
    """Trip statistics response model"""
    vin: str = Field(..., description="Vehicle VIN")
    statistics: TripStatistics = Field(..., description="Trip statistics")

class ChargingStatusResponse(APIResponse):
    """Charging status response model"""
    vin: str = Field(..., description="Vehicle VIN")
    charging: BatteryStatus = Field(..., description="Charging status")

class ServiceIntervalResponse(APIResponse):
    """Service interval response model"""
    vin: str = Field(..., description="Vehicle VIN")
    service: ServiceInfo = Field(..., description="Service information")

class CapabilitiesResponse(APIResponse):
    """Vehicle capabilities response model"""
    vin: str = Field(..., description="Vehicle VIN")
    capabilities: List[str] = Field(..., description="List of supported capabilities")

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    version: str = Field("1.0.0", description="API version")
    service: str = Field("skoda-connect-api", description="Service name")
    uptime_seconds: Optional[int] = Field(None, ge=0, description="Service uptime in seconds")
    cache_stats: Optional[Dict[str, Any]] = Field(None, description="Cache statistics")
    error_stats: Optional[Dict[str, Any]] = Field(None, description="Error statistics")

# Utility Models for Validation

class VINValidator(BaseModel):
    """VIN validation utility"""
    vin: str
    
    @validator('vin')
    def validate_vin_format(cls, v):
        vin = v.upper().strip()
        if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
            raise ValueError('Invalid VIN format')
        return vin
    
    @property
    def manufacturer_code(self) -> str:
        """Extract manufacturer code from VIN"""
        return self.vin[:3]
    
    @property
    def model_year_code(self) -> str:
        """Extract model year code from VIN"""
        return self.vin[9]
    
    @property
    def is_skoda(self) -> bool:
        """Check if VIN is from Skoda"""
        skoda_codes = ['TMB', 'TME', 'TMP', 'TMZ']  # Common Skoda manufacturer codes
        return self.manufacturer_code in skoda_codes

class ConfigModel(BaseModel):
    """Configuration model for environment variables"""
    skoda_username: Optional[str] = Field(None, env='SKODA_USERNAME')
    skoda_password: Optional[str] = Field(None, env='SKODA_PASSWORD')
    redis_url: Optional[str] = Field(None, env='REDIS_URL')
    gcs_bucket: Optional[str] = Field(None, env='GCS_BUCKET')
    log_level: str = Field('INFO', env='LOG_LEVEL')
    cache_ttl_seconds: int = Field(300, env='CACHE_TTL_SECONDS')
    circuit_breaker_threshold: int = Field(5, env='CIRCUIT_BREAKER_THRESHOLD')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

# Model Collections for Export

__all__ = [
    # Enums
    'VehicleType',
    'ChargingState',
    'LockState', 
    'ClimateState',
    
    # Request Models
    'AuthenticationRequest',
    'VehicleStatusRequest',
    'LocationRequest',
    'TripStatisticsRequest',
    'RemoteCommandRequest',
    
    # Data Models
    'Coordinates',
    'Address',
    'VehicleInfo',
    'BatteryStatus',
    'FuelStatus',
    'EnergyStatus',
    'LocationData',
    'DoorsWindowsStatus',
    'ClimateStatus',
    'ServiceInterval',
    'ServiceInfo',
    'Trip',
    'TripStatistics',
    'VehicleStatus',
    'VehicleListItem',
    'CommandResponse',
    
    # Response Models
    'APIResponse',
    'ErrorResponse',
    'VehicleListResponse',
    'VehicleStatusResponse',
    'LocationResponse',
    'TripStatisticsResponse',
    'ChargingStatusResponse',
    'ServiceIntervalResponse',
    'CapabilitiesResponse',
    'HealthResponse',
    
    # Utilities
    'VINValidator',
    'ConfigModel'
]