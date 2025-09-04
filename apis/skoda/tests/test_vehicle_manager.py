"""
Test Suite for Skoda Connect Vehicle Manager
Comprehensive tests for vehicle operations and data handling
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from vehicle_manager import SkodaVehicleManager, VehicleCapability, SkodaAPIError, VehicleNotFoundError, AuthenticationError
from error_handler import error_tracker
from utils.cache_manager import SkodaCacheManager
from utils.circuit_breaker import CircuitBreaker

class TestSkodaVehicleManager:
    """Test cases for SkodaVehicleManager"""
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager fixture"""
        cache_manager = Mock(spec=SkodaCacheManager)
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock()
        cache_manager.delete = AsyncMock()
        cache_manager.delete_pattern = AsyncMock()
        cache_manager.get_stats = AsyncMock(return_value={})
        cache_manager.DEFAULT_TTLS = {
            "vehicle_list": 300,
            "vehicle_status": 60,
            "location": 30,
            "auth_token": 3600
        }
        return cache_manager
    
    @pytest.fixture
    def mock_circuit_breaker(self):
        """Mock circuit breaker fixture"""
        circuit_breaker = Mock(spec=CircuitBreaker)
        circuit_breaker.call = AsyncMock(side_effect=lambda func, *args, **kwargs: func(*args, **kwargs))
        return circuit_breaker
    
    @pytest.fixture
    def mock_myskoda(self):
        """Mock MySkoda instance fixture"""
        myskoda = Mock()
        myskoda.connect = AsyncMock()
        myskoda.get_vehicles = AsyncMock()
        return myskoda
    
    @pytest.fixture
    def mock_vehicle(self):
        """Mock vehicle object fixture"""
        vehicle = Mock()
        vehicle.vin = "TMBJT2N20N1234567"
        
        # Mock vehicle info
        vehicle.info = Mock()
        vehicle.info.model = "Octavia"
        vehicle.info.model_year = "2023"
        vehicle.info.name = "My Skoda"
        vehicle.info.license_plate = "ABC123"
        vehicle.info.color = "Red"
        vehicle.info.capabilities = []
        
        # Mock vehicle status
        vehicle.status = Mock()
        
        # Mock battery status
        vehicle.status.battery = Mock()
        vehicle.status.battery.state_of_charge_percent = 85
        vehicle.status.battery.cruising_range_electric_km = 200
        vehicle.status.battery.charging_state = "NOT_CHARGING"
        vehicle.status.battery.charging_power_kw = 0
        vehicle.status.battery.charging_time_to_complete_minutes = None
        
        # Mock parking position
        vehicle.status.parking_position = Mock()
        vehicle.status.parking_position.latitude = 50.0755
        vehicle.status.parking_position.longitude = 14.4378
        vehicle.status.parking_position.car_captured_timestamp = datetime.now().isoformat()
        
        # Mock overall status
        vehicle.status.overall = Mock()
        vehicle.status.overall.doors_locked = "LOCKED"
        vehicle.status.overall.doors_closed = "CLOSED"
        vehicle.status.overall.windows_closed = "CLOSED"
        vehicle.status.overall.trunk_closed = "CLOSED"
        
        # Mock air conditioning
        vehicle.status.air_conditioning = Mock()
        vehicle.status.air_conditioning.target_temperature_celsius = 22
        vehicle.status.air_conditioning.state = "OFF"
        vehicle.status.air_conditioning.remaining_climatisation_time_minutes = 0
        
        # Mock maintenance
        vehicle.maintenance = Mock()
        vehicle.maintenance.mileage_interval = 15000
        vehicle.maintenance.time_interval_days = 365
        vehicle.maintenance.last_service_mileage = 5000
        
        return vehicle
    
    @pytest.fixture
    def vehicle_manager(self, mock_cache_manager, mock_circuit_breaker):
        """Vehicle manager fixture"""
        return SkodaVehicleManager(
            cache_manager=mock_cache_manager,
            circuit_breaker=mock_circuit_breaker
        )
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, vehicle_manager, mock_myskoda):
        """Test successful initialization"""
        with patch('vehicle_manager.MySkoda', return_value=mock_myskoda):
            result = await vehicle_manager.initialize("test@example.com", "password123")
            
            assert result is True
            assert vehicle_manager.myskoda is not None
            mock_myskoda.connect.assert_called_once_with("test@example.com", "password123")
            mock_myskoda.get_vehicles.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_authentication_failure(self, vehicle_manager):
        """Test initialization with authentication failure"""
        mock_myskoda = Mock()
        mock_myskoda.connect = AsyncMock(side_effect=Exception("Unauthorized"))
        
        with patch('vehicle_manager.MySkoda', return_value=mock_myskoda):
            with pytest.raises(AuthenticationError) as exc_info:
                await vehicle_manager.initialize("test@example.com", "wrong_password")
            
            assert "Authentication failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialize_with_cached_session(self, vehicle_manager, mock_myskoda):
        """Test initialization with cached session"""
        # Mock cached session
        vehicle_manager.cache_manager.get.return_value = {
            "authenticated": True,
            "timestamp": datetime.now().isoformat()
        }
        vehicle_manager.myskoda = mock_myskoda
        
        result = await vehicle_manager.initialize("test@example.com", "password123")
        
        assert result is True
        mock_myskoda.connect.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_vehicles_success(self, vehicle_manager, mock_myskoda, mock_vehicle):
        """Test successful vehicle retrieval"""
        vehicle_manager.myskoda = mock_myskoda
        mock_myskoda.get_vehicles.return_value = [mock_vehicle]
        
        vehicles = await vehicle_manager.get_vehicles()
        
        assert len(vehicles) == 1
        assert vehicles[0]["vin"] == "TMBJT2N20N1234567"
        assert vehicles[0]["brand"] == "Skoda"
        assert vehicles[0]["model"] == "Octavia"
    
    @pytest.mark.asyncio
    async def test_get_vehicles_with_cache(self, vehicle_manager):
        """Test vehicle retrieval with cached data"""
        cached_vehicles = [{
            "vin": "TMBJT2N20N1234567",
            "brand": "Skoda",
            "model": "Octavia"
        }]
        vehicle_manager.cache_manager.get.return_value = cached_vehicles
        
        vehicles = await vehicle_manager.get_vehicles()
        
        assert vehicles == cached_vehicles
        vehicle_manager.cache_manager.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_vehicles_not_initialized(self, vehicle_manager):
        """Test vehicle retrieval without initialization"""
        with pytest.raises(SkodaAPIError) as exc_info:
            await vehicle_manager.get_vehicles()
        
        assert "not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_vehicle_status_success(self, vehicle_manager, mock_myskoda, mock_vehicle):
        """Test successful vehicle status retrieval"""
        vehicle_manager.myskoda = mock_myskoda
        mock_myskoda.get_vehicles.return_value = [mock_vehicle]
        
        status = await vehicle_manager.get_vehicle_status("TMBJT2N20N1234567")
        
        assert status["vin"] == "TMBJT2N20N1234567"
        assert "vehicle_info" in status
        assert "fuel_battery" in status
        assert "location" in status
        assert "doors_windows" in status
        assert "climate" in status
        assert "service_info" in status
        assert "capabilities" in status
        assert "last_updated" in status
    
    @pytest.mark.asyncio
    async def test_get_vehicle_status_with_cache(self, vehicle_manager):
        """Test vehicle status retrieval with cached data"""
        cached_status = {
            "vin": "TMBJT2N20N1234567",
            "vehicle_info": {"model": "Octavia"},
            "last_updated": datetime.now().isoformat()
        }
        vehicle_manager.cache_manager.get.return_value = cached_status
        
        status = await vehicle_manager.get_vehicle_status("TMBJT2N20N1234567")
        
        assert status == cached_status
    
    @pytest.mark.asyncio
    async def test_get_vehicle_status_vehicle_not_found(self, vehicle_manager, mock_myskoda):
        """Test vehicle status retrieval with non-existent VIN"""
        vehicle_manager.myskoda = mock_myskoda
        mock_myskoda.get_vehicles.return_value = []
        
        with pytest.raises(VehicleNotFoundError) as exc_info:
            await vehicle_manager.get_vehicle_status("TMBJT2N20N9999999")
        
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_vehicle_location_success(self, vehicle_manager, mock_myskoda, mock_vehicle):
        """Test successful vehicle location retrieval"""
        vehicle_manager.myskoda = mock_myskoda
        mock_myskoda.get_vehicles.return_value = [mock_vehicle]
        
        location = await vehicle_manager.get_vehicle_location("TMBJT2N20N1234567")
        
        assert location["available"] is True
        assert "coordinates" in location
        assert location["coordinates"]["latitude"] == 50.0755
        assert location["coordinates"]["longitude"] == 14.4378
    
    @pytest.mark.asyncio
    async def test_get_vehicle_location_with_address(self, vehicle_manager, mock_myskoda, mock_vehicle):
        """Test vehicle location retrieval with address resolution"""
        vehicle_manager.myskoda = mock_myskoda
        mock_myskoda.get_vehicles.return_value = [mock_vehicle]
        
        # Mock address resolution
        with patch.object(vehicle_manager, '_resolve_address') as mock_resolve:
            mock_resolve.return_value = {
                "street": "Test Street 123",
                "city": "Prague",
                "country": "Czech Republic"
            }
            
            location = await vehicle_manager.get_vehicle_location("TMBJT2N20N1234567", include_address=True)
            
            assert "address" in location
            assert location["address"]["city"] == "Prague"
            mock_resolve.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_trip_statistics_success(self, vehicle_manager, mock_myskoda, mock_vehicle):
        """Test successful trip statistics retrieval"""
        vehicle_manager.myskoda = mock_myskoda
        mock_myskoda.get_vehicles.return_value = [mock_vehicle]
        
        # Mock trip statistics
        with patch.object(vehicle_manager, '_fetch_trip_statistics') as mock_fetch:
            mock_fetch.return_value = {
                "period": {
                    "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
                    "end_date": datetime.now().isoformat()
                },
                "total_distance": 1500,
                "total_trips": 45,
                "trips": []
            }
            
            stats = await vehicle_manager.get_trip_statistics("TMBJT2N20N1234567")
            
            assert stats["total_distance"] == 1500
            assert stats["total_trips"] == 45
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_service_intervals_success(self, vehicle_manager, mock_myskoda, mock_vehicle):
        """Test successful service intervals retrieval"""
        vehicle_manager.myskoda = mock_myskoda
        mock_myskoda.get_vehicles.return_value = [mock_vehicle]
        
        service = await vehicle_manager.get_service_intervals("TMBJT2N20N1234567")
        
        assert service["available"] is True
        assert service["next_service_km"] == 15000
        assert service["next_service_days"] == 365
        assert service["last_service_km"] == 5000
    
    @pytest.mark.asyncio
    async def test_get_charging_status_success(self, vehicle_manager, mock_myskoda, mock_vehicle):
        """Test successful EV charging status retrieval"""
        vehicle_manager.myskoda = mock_myskoda
        mock_myskoda.get_vehicles.return_value = [mock_vehicle]
        
        # Mock EV capabilities
        with patch.object(vehicle_manager, 'detect_vehicle_capabilities') as mock_capabilities:
            mock_capabilities.return_value = [VehicleCapability.EV_CHARGING.value]
            
            charging = await vehicle_manager.get_charging_status("TMBJT2N20N1234567")
            
            assert charging["battery_level"] == 85
            assert charging["range_km"] == 200
            assert charging["charging_state"] == "NOT_CHARGING"
    
    @pytest.mark.asyncio
    async def test_get_charging_status_non_ev(self, vehicle_manager):
        """Test charging status for non-EV vehicle"""
        with patch.object(vehicle_manager, 'detect_vehicle_capabilities') as mock_capabilities:
            mock_capabilities.return_value = [VehicleCapability.ICE_FUEL.value]
            
            charging = await vehicle_manager.get_charging_status("TMBJT2N20N1234567")
            
            assert charging["is_electric"] is False
            assert "error" in charging
    
    @pytest.mark.asyncio
    async def test_detect_vehicle_capabilities_success(self, vehicle_manager, mock_myskoda, mock_vehicle):
        """Test vehicle capabilities detection"""
        vehicle_manager.myskoda = mock_myskoda
        mock_myskoda.get_vehicles.return_value = [mock_vehicle]
        
        # Mock capabilities in vehicle info
        from myskoda.models.info import CapabilityId
        mock_vehicle.info.capabilities = [
            CapabilityId.CHARGING,
            CapabilityId.VEHICLE_LOCATION,
            CapabilityId.LOCK_UNLOCK
        ]
        
        capabilities = await vehicle_manager.detect_vehicle_capabilities("TMBJT2N20N1234567")
        
        assert VehicleCapability.EV_CHARGING.value in capabilities
        assert VehicleCapability.LOCATION.value in capabilities
        assert VehicleCapability.LOCK_UNLOCK.value in capabilities
    
    @pytest.mark.asyncio
    async def test_detect_vehicle_capabilities_with_cache(self, vehicle_manager):
        """Test capabilities detection with cached data"""
        cached_capabilities = [VehicleCapability.EV_CHARGING.value, VehicleCapability.LOCATION.value]
        vehicle_manager.cache_manager.get.return_value = cached_capabilities
        
        capabilities = await vehicle_manager.detect_vehicle_capabilities("TMBJT2N20N1234567")
        
        assert capabilities == cached_capabilities
    
    @pytest.mark.asyncio
    async def test_normalize_vehicle_data_success(self, vehicle_manager, mock_vehicle):
        """Test vehicle data normalization"""
        normalized = await vehicle_manager.normalize_vehicle_data(mock_vehicle)
        
        assert normalized["vin"] == "TMBJT2N20N1234567"
        assert normalized["brand"] == "Skoda"
        assert normalized["model"] == "Octavia"
        assert normalized["year"] == "2023"
        assert normalized["name"] == "My Skoda"
        assert normalized["license_plate"] == "ABC123"
        assert normalized["color"] == "Red"
        assert normalized["api_provider"] == "skoda_connect"
    
    @pytest.mark.asyncio
    async def test_normalize_vehicle_data_error_handling(self, vehicle_manager):
        """Test vehicle data normalization with errors"""
        # Mock vehicle with missing attributes
        broken_vehicle = Mock()
        broken_vehicle.vin = "TMBJT2N20N1234567"
        del broken_vehicle.info  # Remove info attribute to cause error
        
        normalized = await vehicle_manager.normalize_vehicle_data(broken_vehicle)
        
        assert normalized["vin"] == "TMBJT2N20N1234567"
        assert normalized["brand"] == "Skoda"
        assert "error" in normalized
    
    @pytest.mark.asyncio
    async def test_clear_cache_specific_vin(self, vehicle_manager):
        """Test clearing cache for specific VIN"""
        await vehicle_manager.clear_cache("TMBJT2N20N1234567")
        
        vehicle_manager.cache_manager.delete_pattern.assert_called()
    
    @pytest.mark.asyncio
    async def test_clear_cache_all(self, vehicle_manager):
        """Test clearing all cache"""
        await vehicle_manager.clear_cache()
        
        vehicle_manager.cache_manager.delete_pattern.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, vehicle_manager):
        """Test cache statistics retrieval"""
        mock_stats = {"hits": 100, "misses": 20, "hit_rate": "83.33%"}
        vehicle_manager.cache_manager.get_stats.return_value = mock_stats
        
        stats = await vehicle_manager.get_cache_stats()
        
        assert stats == mock_stats
        vehicle_manager.cache_manager.get_stats.assert_called_once()

class TestVehicleManagerIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.fixture
    def full_setup_manager(self):
        """Fully configured manager for integration tests"""
        cache_manager = Mock(spec=SkodaCacheManager)
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock()
        cache_manager.DEFAULT_TTLS = {"vehicle_list": 300, "vehicle_status": 60}
        
        circuit_breaker = Mock(spec=CircuitBreaker)
        circuit_breaker.call = AsyncMock(side_effect=lambda func, *args, **kwargs: func(*args, **kwargs))
        
        return SkodaVehicleManager(cache_manager=cache_manager, circuit_breaker=circuit_breaker)
    
    @pytest.mark.asyncio
    async def test_full_vehicle_workflow(self, full_setup_manager, mock_vehicle):
        """Test complete vehicle data retrieval workflow"""
        # Mock MySkoda initialization
        mock_myskoda = Mock()
        mock_myskoda.connect = AsyncMock()
        mock_myskoda.get_vehicles = AsyncMock(return_value=[mock_vehicle])
        
        with patch('vehicle_manager.MySkoda', return_value=mock_myskoda):
            # Initialize connection
            await full_setup_manager.initialize("test@example.com", "password123")
            
            # Get vehicle list
            vehicles = await full_setup_manager.get_vehicles()
            assert len(vehicles) == 1
            
            # Get vehicle status
            status = await full_setup_manager.get_vehicle_status("TMBJT2N20N1234567")
            assert status["vin"] == "TMBJT2N20N1234567"
            
            # Get location
            location = await full_setup_manager.get_vehicle_location("TMBJT2N20N1234567")
            assert location["available"] is True
            
            # Verify all components were called
            mock_myskoda.connect.assert_called_once()
            assert mock_myskoda.get_vehicles.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, full_setup_manager):
        """Test error handling and circuit breaker behavior"""
        # Mock failing MySkoda
        mock_myskoda = Mock()
        mock_myskoda.connect = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('vehicle_manager.MySkoda', return_value=mock_myskoda):
            with pytest.raises(AuthenticationError):
                await full_setup_manager.initialize("test@example.com", "password123")
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, full_setup_manager, mock_vehicle):
        """Test caching behavior across multiple calls"""
        mock_myskoda = Mock()
        mock_myskoda.connect = AsyncMock()
        mock_myskoda.get_vehicles = AsyncMock(return_value=[mock_vehicle])
        
        with patch('vehicle_manager.MySkoda', return_value=mock_myskoda):
            await full_setup_manager.initialize("test@example.com", "password123")
            
            # First call should fetch and cache
            await full_setup_manager.get_vehicles()
            
            # Mock cache return for second call
            full_setup_manager.cache_manager.get.return_value = [{"vin": "cached"}]
            
            # Second call should use cache
            cached_vehicles = await full_setup_manager.get_vehicles()
            assert cached_vehicles == [{"vin": "cached"}]

class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.fixture
    def error_manager(self):
        """Manager configured for error testing"""
        cache_manager = Mock()
        cache_manager.get = AsyncMock(side_effect=Exception("Cache error"))
        
        circuit_breaker = Mock()
        circuit_breaker.call = AsyncMock(side_effect=Exception("Circuit breaker error"))
        
        return SkodaVehicleManager(cache_manager=cache_manager, circuit_breaker=circuit_breaker)
    
    @pytest.mark.asyncio
    async def test_cache_failure_handling(self, error_manager):
        """Test handling of cache failures"""
        # Should not raise exception even with cache errors
        # The manager should continue working without cache
        pass
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self, error_manager):
        """Test behavior when circuit breaker is open"""
        # Circuit breaker should prevent cascading failures
        pass

class TestUtilityFunctions:
    """Test utility and helper functions"""
    
    @pytest.fixture
    def manager(self):
        return SkodaVehicleManager()
    
    @pytest.mark.asyncio
    async def test_address_resolution(self, manager):
        """Test GPS coordinate to address resolution"""
        address = await manager._resolve_address(50.0755, 14.4378)
        
        # Should return placeholder address structure
        assert "formatted_address" in address
        assert "Coordinates:" in address["formatted_address"]
    
    @pytest.mark.asyncio 
    async def test_trip_statistics_fetch(self, manager, mock_vehicle):
        """Test trip statistics fetching"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        stats = await manager._fetch_trip_statistics(mock_vehicle, start_date, end_date)
        
        assert "period" in stats
        assert "total_distance" in stats
        assert "total_trips" in stats

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])