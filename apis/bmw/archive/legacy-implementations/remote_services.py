"""
BMW Remote Services
Handles remote vehicle control operations (lock, unlock, climate, etc.)
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from bimmer_connected.vehicle import MyBMWVehicle
from bimmer_connected.vehicle.remote_services import RemoteServices, Services

from utils.error_handler import RemoteServiceError, BMWAPIError

logger = logging.getLogger(__name__)

class BMWRemoteServices:
    """Manages BMW remote vehicle control services"""
    
    def __init__(self):
        self.default_timeout = 90  # seconds
        self.retry_attempts = 3
        self.retry_delay = 5  # seconds
        
    async def lock_vehicle(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """
        Lock the vehicle doors
        
        Args:
            vehicle: BMW vehicle instance
            
        Returns:
            Operation result dictionary
        """
        logger.info(f"Initiating door lock for {vehicle.name}")
        
        try:
            remote_services = RemoteServices(vehicle)
            
            # Execute with retry logic
            result = await self._execute_with_retry(
                remote_services.trigger_remote_door_lock(),
                "door_lock",
                vehicle.name
            )
            
            return {
                "operation": "lock",
                "status": "success",
                "state": result.state.value if result and hasattr(result, "state") else "completed",
                "timestamp": datetime.now().isoformat(),
                "vehicle": vehicle.name
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Lock operation timed out for {vehicle.name}")
            raise RemoteServiceError(
                f"Lock operation timed out after {self.default_timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Failed to lock vehicle {vehicle.name}: {e}")
            raise RemoteServiceError(f"Failed to lock vehicle: {str(e)}")
    
    async def unlock_vehicle(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """
        Unlock the vehicle doors
        
        Args:
            vehicle: BMW vehicle instance
            
        Returns:
            Operation result dictionary
        """
        logger.info(f"Initiating door unlock for {vehicle.name}")
        
        try:
            remote_services = RemoteServices(vehicle)
            
            # Execute with retry logic
            result = await self._execute_with_retry(
                remote_services.trigger_remote_door_unlock(),
                "door_unlock",
                vehicle.name
            )
            
            return {
                "operation": "unlock",
                "status": "success",
                "state": result.state.value if result and hasattr(result, "state") else "completed",
                "timestamp": datetime.now().isoformat(),
                "vehicle": vehicle.name,
                "warning": "Vehicle is now unlocked. Please ensure security."
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Unlock operation timed out for {vehicle.name}")
            raise RemoteServiceError(
                f"Unlock operation timed out after {self.default_timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Failed to unlock vehicle {vehicle.name}: {e}")
            raise RemoteServiceError(f"Failed to unlock vehicle: {str(e)}")
    
    async def flash_lights(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """
        Flash the vehicle lights
        
        Args:
            vehicle: BMW vehicle instance
            
        Returns:
            Operation result dictionary
        """
        logger.info(f"Initiating light flash for {vehicle.name}")
        
        try:
            remote_services = RemoteServices(vehicle)
            
            # Light flash typically completes quickly
            result = await asyncio.wait_for(
                remote_services.trigger_remote_light_flash(),
                timeout=30
            )
            
            return {
                "operation": "flash_lights",
                "status": "success",
                "state": result.state.value if result and hasattr(result, "state") else "completed",
                "timestamp": datetime.now().isoformat(),
                "vehicle": vehicle.name,
                "duration": "3 seconds"
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Light flash operation timed out for {vehicle.name}")
            raise RemoteServiceError("Light flash operation timed out after 30 seconds")
        except Exception as e:
            logger.error(f"Failed to flash lights for {vehicle.name}: {e}")
            raise RemoteServiceError(f"Failed to flash lights: {str(e)}")
    
    async def activate_climate(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """
        Activate the vehicle's air conditioning/climate control
        
        Args:
            vehicle: BMW vehicle instance
            
        Returns:
            Operation result dictionary
        """
        logger.info(f"Initiating climate control for {vehicle.name}")
        
        try:
            remote_services = RemoteServices(vehicle)
            
            # Climate control may take longer to initialize
            result = await self._execute_with_retry(
                remote_services.trigger_remote_service(Services.AIR_CONDITIONING),
                "climate_control",
                vehicle.name,
                timeout=120
            )
            
            return {
                "operation": "climate_control",
                "status": "success",
                "state": result.state.value if result and hasattr(result, "state") else "activated",
                "timestamp": datetime.now().isoformat(),
                "vehicle": vehicle.name,
                "duration": "Will run for 30 minutes or until manually stopped",
                "note": "Climate control activated with last known temperature settings"
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Climate control operation timed out for {vehicle.name}")
            raise RemoteServiceError("Climate control operation timed out after 120 seconds")
        except Exception as e:
            logger.error(f"Failed to activate climate for {vehicle.name}: {e}")
            raise RemoteServiceError(f"Failed to activate climate control: {str(e)}")
    
    async def honk_horn(self, vehicle: MyBMWVehicle) -> Dict[str, Any]:
        """
        Honk the vehicle horn
        
        Args:
            vehicle: BMW vehicle instance
            
        Returns:
            Operation result dictionary
        """
        logger.info(f"Initiating horn honk for {vehicle.name}")
        
        try:
            remote_services = RemoteServices(vehicle)
            
            # Horn honk is typically quick
            result = await asyncio.wait_for(
                remote_services.trigger_remote_horn(),
                timeout=30
            )
            
            return {
                "operation": "honk_horn",
                "status": "success",
                "state": result.state.value if result and hasattr(result, "state") else "completed",
                "timestamp": datetime.now().isoformat(),
                "vehicle": vehicle.name,
                "duration": "2 short honks"
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Horn honk operation timed out for {vehicle.name}")
            raise RemoteServiceError("Horn honk operation timed out after 30 seconds")
        except Exception as e:
            logger.error(f"Failed to honk horn for {vehicle.name}: {e}")
            raise RemoteServiceError(f"Failed to honk horn: {str(e)}")
    
    async def _execute_with_retry(
        self,
        operation: Any,
        operation_name: str,
        vehicle_name: str,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Execute a remote operation with retry logic
        
        Args:
            operation: The async operation to execute
            operation_name: Name of the operation for logging
            vehicle_name: Vehicle name for logging
            timeout: Custom timeout in seconds
            
        Returns:
            Operation result
            
        Raises:
            RemoteServiceError: If all retries fail
        """
        timeout = timeout or self.default_timeout
        last_error = None
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                logger.info(
                    f"Executing {operation_name} for {vehicle_name} "
                    f"(attempt {attempt}/{self.retry_attempts})"
                )
                
                # Execute with timeout
                result = await asyncio.wait_for(operation, timeout=timeout)
                
                # If successful, return result
                logger.info(f"Successfully executed {operation_name} for {vehicle_name}")
                return result
                
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt} timed out for {operation_name} on {vehicle_name}"
                )
                
                if attempt < self.retry_attempts:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    await asyncio.sleep(self.retry_delay)
                    
            except Exception as e:
                last_error = e
                logger.error(
                    f"Attempt {attempt} failed for {operation_name} on {vehicle_name}: {e}"
                )
                
                # Check if error is retryable
                if self._is_retryable_error(e) and attempt < self.retry_attempts:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    # Non-retryable error, raise immediately
                    raise RemoteServiceError(
                        f"{operation_name} failed: {str(e)}"
                    )
        
        # All retries exhausted
        logger.error(f"All retry attempts failed for {operation_name} on {vehicle_name}")
        
        if isinstance(last_error, asyncio.TimeoutError):
            raise RemoteServiceError(
                f"{operation_name} timed out after {self.retry_attempts} attempts"
            )
        else:
            raise RemoteServiceError(
                f"{operation_name} failed after {self.retry_attempts} attempts: {str(last_error)}"
            )
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable
        
        Args:
            error: The exception to check
            
        Returns:
            True if error is retryable, False otherwise
        """
        # Define retryable error patterns
        retryable_patterns = [
            "timeout",
            "connection",
            "temporary",
            "503",
            "504",
            "network"
        ]
        
        error_str = str(error).lower()
        return any(pattern in error_str for pattern in retryable_patterns)