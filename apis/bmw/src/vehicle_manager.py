"""
BMW Vehicle Manager
Handles vehicle data retrieval and status queries
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from bimmer_connected.account import MyBMWAccount
from bimmer_connected.vehicle import MyBMWVehicle

from utils.error_handler import BMWAPIError

logger = logging.getLogger(__name__)

class BMWVehicleManager:
    """Manages BMW vehicle data and status queries"""
    
    def __init__(self):
        self.vehicle_cache: Dict[str, MyBMWVehicle] = {}
        
    async def get_vehicle(self, account: MyBMWAccount, wkn: str) -> MyBMWVehicle:
        """
        Get vehicle by WKN (vehicle identification number)
        
        Args:
            account: Authenticated BMW account
            wkn: Vehicle WKN
            
        Returns:
            MyBMWVehicle instance
            
        Raises:
            BMWAPIError: If vehicle not found or error occurs
        """
        try:
            # Check cache first
            cache_key = f"{account.username}:{wkn}"
            if cache_key in self.vehicle_cache:
                logger.info(f"Using cached vehicle data for {wkn}")
                return self.vehicle_cache[cache_key]
            
            # Fetch vehicles from API
            await account.get_vehicles()
            
            # Find vehicle by WKN
            vehicle = account.get_vehicle(wkn)
            if not vehicle:
                raise BMWAPIError(f"Vehicle with WKN {wkn} not found")
            
            # Cache the vehicle
            self.vehicle_cache[cache_key] = vehicle
            
            logger.info(f"Retrieved vehicle: {vehicle.name} ({vehicle.brand})")
            return vehicle
            
        except Exception as e:
            logger.error(f"Failed to get vehicle {wkn}: {e}")
            raise BMWAPIError(f"Failed to retrieve vehicle: {str(e)}")
    
    def get_full_status(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """
        Get comprehensive vehicle status
        
        Args:
            vehicle: BMW vehicle instance
            
        Returns:
            Dictionary with full vehicle status
        """
        try:
            status = {
                "vehicle_info": {
                    "brand": vehicle.brand,
                    "name": vehicle.name,
                    "vin": vehicle.vin,
                    "model": getattr(vehicle, "model", "Unknown"),
                    "year": getattr(vehicle, "year", "Unknown")
                },
                "fuel_and_battery": self.get_fuel_status(vehicle),
                "location": self.get_location(vehicle),
                "mileage": self.get_mileage(vehicle),
                "doors_and_windows": self._get_doors_windows_status(vehicle),
                "check_control": self.get_check_control_messages(vehicle),
                "last_updated": datetime.now().isoformat()
            }
            
            logger.info(f"Retrieved full status for {vehicle.name}")
            return status
            
        except Exception as e:
            logger.error(f"Failed to get full status: {e}")
            return {
                "error": f"Failed to retrieve status: {str(e)}",
                "partial_data": True
            }
    
    def get_fuel_status(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """Get fuel and battery status"""
        try:
            fuel_and_battery = vehicle.fuel_and_battery
            
            return {
                "remaining_fuel": getattr(fuel_and_battery, "remaining_fuel", None),
                "remaining_fuel_percent": getattr(fuel_and_battery, "remaining_fuel_percent", None),
                "remaining_range_fuel": getattr(fuel_and_battery, "remaining_range_fuel", None),
                "remaining_range_electric": getattr(fuel_and_battery, "remaining_range_electric", None),
                "remaining_range_total": getattr(fuel_and_battery, "remaining_range_total", None),
                "fuel_type": getattr(fuel_and_battery, "fuel_type", "Unknown"),
                "charging_status": getattr(fuel_and_battery, "charging_status", None),
                "battery_level": getattr(fuel_and_battery, "battery_level", None)
            }
            
        except Exception as e:
            logger.warning(f"Failed to get fuel status: {e}")
            return {"error": str(e)}
    
    def get_location(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """Get vehicle location"""
        try:
            location = vehicle.location
            
            if not location or not location.location:
                return {"status": "Location not available"}
            
            return {
                "latitude": location.location.latitude,
                "longitude": location.location.longitude,
                "heading": getattr(location, "heading", None),
                "address": getattr(location, "address", None),
                "timestamp": location.vehicle_update_timestamp.isoformat() if location.vehicle_update_timestamp else None,
                "google_maps_url": f"https://www.google.com/maps?q={location.location.latitude},{location.location.longitude}"
            }
            
        except Exception as e:
            logger.warning(f"Failed to get location: {e}")
            return {"error": str(e)}
    
    def get_mileage(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """Get vehicle mileage"""
        try:
            mileage = vehicle.mileage
            
            if hasattr(mileage, "value") and hasattr(mileage, "unit"):
                return {
                    "value": mileage.value,
                    "unit": mileage.unit
                }
            else:
                return {
                    "value": mileage if mileage else "Unknown",
                    "unit": "km"
                }
                
        except Exception as e:
            logger.warning(f"Failed to get mileage: {e}")
            return {"error": str(e)}
    
    def get_check_control_messages(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """Get check control messages"""
        try:
            report = vehicle.check_control_message_report
            
            if not report:
                return {"has_messages": False, "messages": []}
            
            messages = []
            if hasattr(report, "messages") and report.messages:
                for msg in report.messages:
                    messages.append({
                        "text": getattr(msg, "text", "Unknown"),
                        "severity": getattr(msg, "severity", "Unknown"),
                        "category": getattr(msg, "category", "Unknown")
                    })
            
            return {
                "has_messages": getattr(report, "has_check_control_messages", False),
                "messages": messages,
                "count": len(messages)
            }
            
        except Exception as e:
            logger.warning(f"Failed to get check control messages: {e}")
            return {"error": str(e)}
    
    def get_lock_status(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """Get detailed lock status"""
        try:
            doors_windows = vehicle.doors_windows
            
            if not doors_windows:
                return {"status": "Unknown"}
            
            lock_state = getattr(doors_windows, "lock_state", None)
            
            return {
                "lock_state": lock_state.value if lock_state and hasattr(lock_state, "value") else "Unknown",
                "all_windows_closed": getattr(doors_windows, "all_windows_closed", None),
                "all_doors_closed": getattr(doors_windows, "all_doors_closed", None),
                "hood_closed": getattr(doors_windows, "hood_closed", None),
                "trunk_closed": getattr(doors_windows, "trunk_closed", None)
            }
            
        except Exception as e:
            logger.warning(f"Failed to get lock status: {e}")
            return {"error": str(e)}
    
    def is_locked(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """Check if vehicle is locked (simplified)"""
        try:
            doors_windows = vehicle.doors_windows
            
            if not doors_windows:
                return {"locked": "unknown", "reason": "No door/window data available"}
            
            lock_state = getattr(doors_windows, "lock_state", None)
            
            if lock_state and hasattr(lock_state, "value"):
                state_value = lock_state.value.upper()
                
                if state_value == "LOCKED":
                    return {"locked": True, "state": "locked"}
                elif state_value == "UNLOCKED":
                    return {"locked": False, "state": "unlocked"}
                else:
                    return {"locked": "partial", "state": state_value.lower()}
            
            return {"locked": "unknown", "reason": "Lock state not available"}
            
        except Exception as e:
            logger.warning(f"Failed to check lock status: {e}")
            return {"locked": "error", "error": str(e)}
    
    def _get_doors_windows_status(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """Get detailed doors and windows status"""
        try:
            doors_windows = vehicle.doors_windows
            
            if not doors_windows:
                return {"status": "Not available"}
            
            return {
                "lock_state": self.get_lock_status(vehicle),
                "doors": {
                    "all_closed": getattr(doors_windows, "all_doors_closed", None),
                    "driver_front": getattr(doors_windows, "driver_front", None),
                    "passenger_front": getattr(doors_windows, "passenger_front", None),
                    "driver_rear": getattr(doors_windows, "driver_rear", None),
                    "passenger_rear": getattr(doors_windows, "passenger_rear", None)
                },
                "windows": {
                    "all_closed": getattr(doors_windows, "all_windows_closed", None),
                    "driver_front": getattr(doors_windows, "window_driver_front", None),
                    "passenger_front": getattr(doors_windows, "window_passenger_front", None),
                    "driver_rear": getattr(doors_windows, "window_driver_rear", None),
                    "passenger_rear": getattr(doors_windows, "window_passenger_rear", None),
                    "sunroof": getattr(doors_windows, "sunroof", None)
                },
                "trunk": getattr(doors_windows, "trunk_closed", None),
                "hood": getattr(doors_windows, "hood_closed", None)
            }
            
        except Exception as e:
            logger.warning(f"Failed to get doors/windows status: {e}")
            return {"error": str(e)}
    
    def clear_cache(self, wkn: Optional[str] = None) -> None:
        """Clear vehicle cache"""
        if wkn:
            keys_to_remove = [k for k in self.vehicle_cache if k.endswith(f":{wkn}")]
            for key in keys_to_remove:
                del self.vehicle_cache[key]
            logger.info(f"Cleared cache for vehicle {wkn}")
        else:
            self.vehicle_cache.clear()
            logger.info("Cleared all vehicle cache")