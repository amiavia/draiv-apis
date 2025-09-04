"""
Test configuration and fixtures for Skoda Connect API tests
"""
import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock

from src.main import app
from src.models import SkodaVehicle, VehicleStatus, VehicleType, get_example_vehicle, get_example_status

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_auth_manager():
    """Mock authentication manager"""
    auth_manager = MagicMock()
    auth_manager.validate_credentials = AsyncMock(return_value={"username": "test", "validated_at": "2025-01-01T00:00:00Z", "session_valid": True})
    auth_manager.store_credentials = AsyncMock(return_value=None)
    auth_manager.get_credentials = AsyncMock(return_value={
        "username": "test@example.com",
        "password": "password123",
        "s_pin": "1234",
        "has_spin": True,
        "created_at": "2025-01-01T00:00:00Z",
        "last_validated": "2025-01-01T00:00:00Z"
    })
    auth_manager.validate_session = AsyncMock(return_value=True)
    auth_manager.validate_spin = AsyncMock(return_value=True)
    auth_manager.remove_credentials = AsyncMock(return_value=True)
    return auth_manager

@pytest.fixture
def mock_vehicle_manager():
    """Mock vehicle manager"""
    vehicle_manager = MagicMock()
    
    # Mock vehicles list
    test_vehicles = [get_example_vehicle()]
    vehicle_manager.get_vehicles = AsyncMock(return_value=test_vehicles)
    
    # Mock vehicle status
    test_status = get_example_status()
    vehicle_manager.get_vehicle_status = AsyncMock(return_value=test_status)
    
    # Mock vehicle location
    vehicle_manager.get_vehicle_location = AsyncMock(return_value=test_status.location)
    
    # Mock trip history
    vehicle_manager.get_trip_history = AsyncMock(return_value=[])
    
    # Mock charging status
    from src.models import ChargingStatus
    vehicle_manager.get_charging_status = AsyncMock(return_value=ChargingStatus(
        is_charging=False,
        charging_power=None,
        charge_rate=None,
        time_to_full_minutes=None,
        target_charge_level=None,
        charging_location=None,
        last_charge_session=None
    ))
    
    # Mock command execution
    vehicle_manager.execute_command = AsyncMock(return_value={
        "command": "lock",
        "vin": "TMBJB7NE6L1234567",
        "success": True,
        "result": {"status": "completed"},
        "executed_at": "2025-01-01T00:00:00Z"
    })
    
    return vehicle_manager

@pytest.fixture
def mock_cache():
    """Mock cache manager"""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.delete_pattern = AsyncMock(return_value=5)
    cache.exists = AsyncMock(return_value=False)
    cache.size = AsyncMock(return_value=0)
    cache.close = AsyncMock(return_value=None)
    return cache

@pytest.fixture
def mock_circuit_breaker():
    """Mock circuit breaker"""
    circuit_breaker = MagicMock()
    circuit_breaker.call = AsyncMock(side_effect=lambda func, *args, **kwargs: func(*args, **kwargs))
    circuit_breaker.state = "closed"
    return circuit_breaker

@pytest.fixture
def mock_metrics():
    """Mock metrics collector"""
    metrics = MagicMock()
    metrics.increment = MagicMock()
    metrics.timing = MagicMock()
    metrics.gauge = MagicMock()
    metrics.get_all_metrics = MagicMock(return_value={
        "service": "skoda-api",
        "timestamp": "2025-01-01T00:00:00Z",
        "uptime_seconds": 3600,
        "counters": {},
        "gauges": {},
        "timers": {},
        "requests": {"total_requests": 100, "total_errors": 5},
        "cache": {"hit_rate": 85.5},
        "circuit_breaker": {"recent_events": 0}
    })
    return metrics

@pytest.fixture
def valid_auth_setup_request():
    """Valid authentication setup request data"""
    return {
        "username": "test@example.com",
        "password": "password123",
        "s_pin": "1234",
        "user_id": "test_user_123"
    }

@pytest.fixture
def valid_vehicle_command_request():
    """Valid vehicle command request data"""
    return {
        "s_pin": "1234",
        "user_id": "test_user_123"
    }

@pytest.fixture
def test_headers():
    """Standard test headers"""
    return {
        "X-User-ID": "test_user_123",
        "Content-Type": "application/json"
    }

@pytest.fixture
def mock_myskoda_client():
    """Mock MySkoda client"""
    client = MagicMock()
    
    # Mock authentication
    auth = MagicMock()
    auth.authenticate = AsyncMock()
    client.auth = auth
    
    # Mock disconnect
    client.disconnect = AsyncMock()
    
    # Mock vehicle operations
    client.get_vehicles = AsyncMock(return_value=[])
    client.get_status = AsyncMock(return_value=MagicMock())
    client.get_position = AsyncMock(return_value=MagicMock(latitude=47.3769, longitude=8.5417))
    client.lock = AsyncMock(return_value={"status": "completed"})
    client.unlock = AsyncMock(return_value={"status": "completed"})
    client.start_climate = AsyncMock(return_value={"status": "completed"})
    client.stop_climate = AsyncMock(return_value={"status": "completed"})
    
    return client

@pytest.fixture(autouse=True)
def setup_app_state(mock_auth_manager, mock_vehicle_manager, mock_cache, mock_circuit_breaker, mock_metrics):
    """Set up app state with mocked dependencies"""
    app.state.auth_manager = mock_auth_manager
    app.state.vehicle_manager = mock_vehicle_manager
    app.state.cache = mock_cache
    app.state.circuit_breaker = mock_circuit_breaker
    app.state.metrics = mock_metrics

# Test data fixtures
@pytest.fixture
def example_vin():
    """Example VIN for testing"""
    return "TMBJB7NE6L1234567"

@pytest.fixture
def example_user_id():
    """Example user ID for testing"""
    return "test_user_123"

@pytest.fixture
def example_vehicle_data():
    """Example vehicle data for testing"""
    return {
        "vin": "TMBJB7NE6L1234567",
        "name": "My Octavia",
        "model": "Octavia",
        "year": 2024,
        "color": "White",
        "vehicle_type": "fuel",
        "registration": "ZH-123456",
        "capabilities": {
            "remote_lock": True,
            "remote_unlock": True,
            "climate_control": True,
            "flash_lights": True,
            "location_tracking": True,
            "trip_history": True,
            "charging_control": False
        }
    }

# Error simulation fixtures
@pytest.fixture
def auth_manager_with_errors():
    """Authentication manager that simulates various errors"""
    auth_manager = MagicMock()
    auth_manager.validate_credentials = AsyncMock(side_effect=Exception("Invalid credentials"))
    auth_manager.store_credentials = AsyncMock(side_effect=Exception("Storage failed"))
    auth_manager.get_credentials = AsyncMock(return_value=None)
    auth_manager.validate_session = AsyncMock(return_value=False)
    auth_manager.validate_spin = AsyncMock(return_value=False)
    return auth_manager

@pytest.fixture
def vehicle_manager_with_errors():
    """Vehicle manager that simulates various errors"""
    vehicle_manager = MagicMock()
    vehicle_manager.get_vehicles = AsyncMock(side_effect=Exception("Failed to get vehicles"))
    vehicle_manager.get_vehicle_status = AsyncMock(side_effect=Exception("Failed to get status"))
    vehicle_manager.execute_command = AsyncMock(side_effect=Exception("Command failed"))
    return vehicle_manager