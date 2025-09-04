"""
Skoda Vehicle Manager - Handles vehicle operations via MySkoda API
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from myskoda import MySkoda
from myskoda.auth import MySkodaAuth
from myskoda.models import Vehicle

from models import (
    SkodaVehicle, VehicleStatus, VehicleLocation, VehicleType,
    DoorStatus, WindowStatus, FuelStatus, BatteryStatus,
    ClimateStatus, ServiceInterval, TripSegment, ChargingStatus
)

logger = logging.getLogger(__name__)

class SkodaVehicleManager:
    """Manages Skoda vehicle operations through MySkoda API"""
    
    def __init__(self):
        self.connection_pool = {}  # Simple connection pooling
    
    async def _get_authenticated_client(self, credentials: Dict[str, Any]) -> MySkoda:
        """Get authenticated MySkoda client"""
        try:
            myskoda = MySkoda()
            auth = MySkodaAuth(credentials["username"], credentials["password"])
            await auth.authenticate()
            
            # Set up the client with authentication
            myskoda.auth = auth
            
            return myskoda
            
        except Exception as e:
            logger.error(f"Failed to create authenticated client: {e}")
            raise Exception(f"Authentication failed: {str(e)}")
    
    async def get_vehicles(self, credentials: Dict[str, Any]) -> List[SkodaVehicle]:
        """Get list of user's vehicles"""
        client = None
        try:
            client = await self._get_authenticated_client(credentials)
            
            # Get vehicles from MySkoda
            vehicles = await client.get_vehicles()
            
            skoda_vehicles = []
            for vehicle in vehicles:
                skoda_vehicle = SkodaVehicle(
                    vin=vehicle.vin,
                    name=getattr(vehicle, 'name', None) or f"{vehicle.model} {vehicle.model_year}",
                    model=vehicle.model,
                    year=vehicle.model_year,
                    color=getattr(vehicle, 'color', None),
                    vehicle_type=self._determine_vehicle_type(vehicle),
                    registration=getattr(vehicle, 'license_plate', None),
                    capabilities=self._get_vehicle_capabilities(vehicle)
                )
                skoda_vehicles.append(skoda_vehicle)
            
            return skoda_vehicles
            
        except Exception as e:
            logger.error(f"Failed to get vehicles: {e}")
            raise Exception(f"Failed to retrieve vehicles: {str(e)}")
        finally:
            if client:
                await client.disconnect()
    
    async def get_vehicle_status(self, credentials: Dict[str, Any], vin: str) -> VehicleStatus:
        """Get comprehensive vehicle status"""
        client = None
        try:
            client = await self._get_authenticated_client(credentials)
            
            # Get vehicle by VIN
            vehicles = await client.get_vehicles()
            vehicle = next((v for v in vehicles if v.vin == vin), None)
            
            if not vehicle:
                raise Exception(f"Vehicle with VIN {vin} not found")
            
            # Get detailed status
            status_info = await client.get_status(vin)
            
            # Convert to our models
            skoda_vehicle = SkodaVehicle(
                vin=vehicle.vin,
                name=getattr(vehicle, 'name', None) or f"{vehicle.model} {vehicle.model_year}",
                model=vehicle.model,
                year=vehicle.model_year,
                color=getattr(vehicle, 'color', None),
                vehicle_type=self._determine_vehicle_type(vehicle),
                registration=getattr(vehicle, 'license_plate', None),
                capabilities=self._get_vehicle_capabilities(vehicle)
            )
            
            # Extract status information
            doors = self._extract_door_status(status_info)
            windows = self._extract_window_status(status_info)
            fuel = self._extract_fuel_status(status_info, skoda_vehicle.vehicle_type)
            battery = self._extract_battery_status(status_info, skoda_vehicle.vehicle_type)
            climate = self._extract_climate_status(status_info)
            location = await self._get_vehicle_location_from_status(client, vin, status_info)
            service_interval = self._extract_service_interval(status_info)
            
            vehicle_status = VehicleStatus(
                vehicle=skoda_vehicle,
                doors=doors,
                windows=windows,
                fuel=fuel,
                battery=battery,
                climate=climate,
                location=location,
                mileage_km=getattr(status_info, 'mileage', 0),
                service_interval=service_interval,
                last_updated=datetime.utcnow()
            )
            
            return vehicle_status
            
        except Exception as e:
            logger.error(f"Failed to get vehicle status for {vin}: {e}")
            raise Exception(f"Failed to retrieve vehicle status: {str(e)}")
        finally:
            if client:
                await client.disconnect()
    
    async def get_vehicle_location(self, credentials: Dict[str, Any], vin: str) -> VehicleLocation:
        """Get vehicle GPS location"""
        client = None
        try:
            client = await self._get_authenticated_client(credentials)
            
            # Get location from MySkoda
            location_info = await client.get_position(vin)
            
            return VehicleLocation(
                latitude=location_info.latitude,
                longitude=location_info.longitude,
                address=getattr(location_info, 'address', None),
                updated_at=datetime.fromisoformat(location_info.timestamp) if hasattr(location_info, 'timestamp') else datetime.utcnow(),
                accuracy=getattr(location_info, 'accuracy', None)
            )
            
        except Exception as e:
            logger.error(f"Failed to get location for vehicle {vin}: {e}")
            raise Exception(f"Failed to retrieve vehicle location: {str(e)}")
        finally:
            if client:
                await client.disconnect()
    
    async def get_trip_history(self, credentials: Dict[str, Any], vin: str) -> List[TripSegment]:
        """Get vehicle trip history"""
        client = None
        try:
            client = await self._get_authenticated_client(credentials)
            
            # Get trip history from MySkoda
            trips_info = await client.get_trips(vin)
            
            trip_segments = []
            for trip in trips_info:
                segment = TripSegment(
                    start_time=datetime.fromisoformat(trip.start_time),
                    end_time=datetime.fromisoformat(trip.end_time),
                    distance_km=trip.distance / 1000,  # Convert to km
                    duration_minutes=trip.duration // 60,  # Convert to minutes
                    fuel_consumed=getattr(trip, 'fuel_consumed', None),
                    energy_consumed=getattr(trip, 'energy_consumed', None),
                    average_speed=trip.average_speed,
                    start_location=None,  # Would need to be populated if available
                    end_location=None
                )
                trip_segments.append(segment)
            
            return trip_segments
            
        except Exception as e:
            logger.error(f"Failed to get trip history for vehicle {vin}: {e}")
            raise Exception(f"Failed to retrieve trip history: {str(e)}")
        finally:
            if client:
                await client.disconnect()
    
    async def get_charging_status(self, credentials: Dict[str, Any], vin: str) -> ChargingStatus:
        """Get EV charging status"""
        client = None
        try:
            client = await self._get_authenticated_client(credentials)
            
            # Get charging info from MySkoda
            charging_info = await client.get_charging_status(vin)
            
            return ChargingStatus(
                is_charging=charging_info.is_charging,
                charging_power=getattr(charging_info, 'charging_power', None),
                charge_rate=getattr(charging_info, 'charge_rate', None),
                time_to_full_minutes=getattr(charging_info, 'time_to_full', None),
                target_charge_level=getattr(charging_info, 'target_charge', None),
                charging_location=getattr(charging_info, 'location', None),
                last_charge_session=datetime.fromisoformat(charging_info.last_updated) if hasattr(charging_info, 'last_updated') else None
            )
            
        except Exception as e:
            logger.error(f"Failed to get charging status for vehicle {vin}: {e}")
            raise Exception(f"Failed to retrieve charging status: {str(e)}")
        finally:
            if client:
                await client.disconnect()
    
    async def execute_command(
        self, 
        credentials: Dict[str, Any], 
        vin: str, 
        command: str, 
        s_pin: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute vehicle command"""
        client = None
        try:
            client = await self._get_authenticated_client(credentials)
            
            # Execute command based on type
            if command == "lock":
                result = await client.lock(vin, s_pin)
            elif command == "unlock":
                result = await client.unlock(vin, s_pin)
            elif command == "climate_start":
                result = await client.start_climate(vin, s_pin)
            elif command == "climate_stop":
                result = await client.stop_climate(vin, s_pin)
            elif command == "charging_start":
                result = await client.start_charging(vin, s_pin)
            elif command == "charging_stop":
                result = await client.stop_charging(vin, s_pin)
            else:
                raise Exception(f"Unknown command: {command}")
            
            return {
                "command": command,
                "vin": vin,
                "success": True,
                "result": result,
                "executed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Command {command} failed for vehicle {vin}: {e}")
            raise Exception(f"Command execution failed: {str(e)}")
        finally:
            if client:
                await client.disconnect()
    
    def _determine_vehicle_type(self, vehicle) -> VehicleType:
        """Determine vehicle type from vehicle info"""
        # This would need to be implemented based on MySkoda vehicle attributes
        if hasattr(vehicle, 'drivetrain'):
            if 'electric' in vehicle.drivetrain.lower():
                return VehicleType.ELECTRIC
            elif 'hybrid' in vehicle.drivetrain.lower():
                return VehicleType.HYBRID
            else:
                return VehicleType.FUEL
        return VehicleType.UNKNOWN
    
    def _get_vehicle_capabilities(self, vehicle) -> Dict[str, bool]:
        """Determine vehicle capabilities"""
        # Default capabilities - would be determined from vehicle specs
        return {
            "remote_lock": True,
            "remote_unlock": True,
            "climate_control": True,
            "flash_lights": True,
            "location_tracking": True,
            "trip_history": True,
            "charging_control": self._determine_vehicle_type(vehicle) in [VehicleType.ELECTRIC, VehicleType.HYBRID]
        }
    
    def _extract_door_status(self, status_info) -> DoorStatus:
        """Extract door status from MySkoda status"""
        return DoorStatus(
            driver=getattr(status_info, 'door_driver', 'closed'),
            passenger=getattr(status_info, 'door_passenger', 'closed'),
            rear_left=getattr(status_info, 'door_rear_left', 'closed'),
            rear_right=getattr(status_info, 'door_rear_right', 'closed'),
            locked=getattr(status_info, 'locked', False)
        )
    
    def _extract_window_status(self, status_info) -> WindowStatus:
        """Extract window status from MySkoda status"""
        return WindowStatus(
            driver=getattr(status_info, 'window_driver', 'closed'),
            passenger=getattr(status_info, 'window_passenger', 'closed'),
            rear_left=getattr(status_info, 'window_rear_left', 'closed'),
            rear_right=getattr(status_info, 'window_rear_right', 'closed')
        )
    
    def _extract_fuel_status(self, status_info, vehicle_type: VehicleType) -> Optional[FuelStatus]:
        """Extract fuel status if applicable"""
        if vehicle_type in [VehicleType.FUEL, VehicleType.HYBRID]:
            return FuelStatus(
                level=getattr(status_info, 'fuel_level', 0),
                range_km=getattr(status_info, 'fuel_range', 0),
                last_updated=datetime.utcnow()
            )
        return None
    
    def _extract_battery_status(self, status_info, vehicle_type: VehicleType) -> Optional[BatteryStatus]:
        """Extract battery status if applicable"""
        if vehicle_type in [VehicleType.ELECTRIC, VehicleType.HYBRID]:
            return BatteryStatus(
                level=getattr(status_info, 'battery_level', 0),
                range_km=getattr(status_info, 'battery_range', 0),
                charging=getattr(status_info, 'is_charging', False),
                last_updated=datetime.utcnow()
            )
        return None
    
    def _extract_climate_status(self, status_info) -> ClimateStatus:
        """Extract climate control status"""
        return ClimateStatus(
            active=getattr(status_info, 'climate_active', False),
            temperature=getattr(status_info, 'target_temperature', None),
            defrost=getattr(status_info, 'defrost_active', False)
        )
    
    async def _get_vehicle_location_from_status(
        self, 
        client: MySkoda, 
        vin: str, 
        status_info
    ) -> VehicleLocation:
        """Get location from status or fetch separately"""
        if hasattr(status_info, 'location'):
            return VehicleLocation(
                latitude=status_info.location.latitude,
                longitude=status_info.location.longitude,
                address=getattr(status_info.location, 'address', None),
                updated_at=datetime.utcnow(),
                accuracy=getattr(status_info.location, 'accuracy', None)
            )
        else:
            # Fetch location separately
            try:
                location_info = await client.get_position(vin)
                return VehicleLocation(
                    latitude=location_info.latitude,
                    longitude=location_info.longitude,
                    address=getattr(location_info, 'address', None),
                    updated_at=datetime.utcnow(),
                    accuracy=getattr(location_info, 'accuracy', None)
                )
            except:
                # Default location if unavailable
                return VehicleLocation(
                    latitude=0.0,
                    longitude=0.0,
                    address="Location unavailable",
                    updated_at=datetime.utcnow(),
                    accuracy=None
                )
    
    def _extract_service_interval(self, status_info) -> Optional[ServiceInterval]:
        """Extract service interval information"""
        if hasattr(status_info, 'service_info'):
            return ServiceInterval(
                distance_to_service=getattr(status_info.service_info, 'distance_to_service', 0),
                days_to_service=getattr(status_info.service_info, 'days_to_service', 0),
                type=getattr(status_info.service_info, 'service_type', 'Standard Service')
            )
        return None