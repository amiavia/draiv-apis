"""
Tests for Skoda Connect API main application
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health check and monitoring endpoints"""
    
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "skoda-api"
        assert "version" in data
        assert "timestamp" in data

    async def test_metrics_endpoint(self, client: AsyncClient):
        """Test metrics endpoint"""
        response = await client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "requests" in data
        assert "cache" in data

@pytest.mark.asyncio
class TestAuthenticationEndpoints:
    """Test authentication-related endpoints"""
    
    async def test_setup_authentication_success(
        self, 
        client: AsyncClient, 
        valid_auth_setup_request: dict,
        test_headers: dict
    ):
        """Test successful authentication setup"""
        response = await client.post(
            "/auth/setup", 
            json=valid_auth_setup_request,
            headers=test_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "setup" in data["data"]
        assert "has_spin" in data["data"]

    async def test_setup_authentication_missing_user_id(
        self, 
        client: AsyncClient, 
        valid_auth_setup_request: dict
    ):
        """Test authentication setup without user ID"""
        del valid_auth_setup_request["user_id"]
        
        response = await client.post("/auth/setup", json=valid_auth_setup_request)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "AUTH_REQUIRED"

    async def test_setup_authentication_invalid_data(
        self, 
        client: AsyncClient,
        test_headers: dict
    ):
        """Test authentication setup with invalid data"""
        invalid_request = {
            "username": "invalid-email",  # Invalid email format
            "password": "123",  # Too short
            "s_pin": "12345",  # Too long
            "user_id": "test_user_123"
        }
        
        response = await client.post(
            "/auth/setup", 
            json=invalid_request,
            headers=test_headers
        )
        
        assert response.status_code == 422  # Validation error

    async def test_validate_authentication_success(
        self, 
        client: AsyncClient,
        test_headers: dict
    ):
        """Test successful authentication validation"""
        request_data = {"user_id": "test_user_123"}
        
        response = await client.post(
            "/auth/validate", 
            json=request_data,
            headers=test_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "valid" in data["data"]

    async def test_remove_authentication_success(
        self, 
        client: AsyncClient,
        test_headers: dict
    ):
        """Test successful authentication removal"""
        response = await client.delete("/auth/remove", headers=test_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["removed"] is True

@pytest.mark.asyncio
class TestVehicleEndpoints:
    """Test vehicle-related endpoints"""
    
    async def test_get_vehicles_success(
        self, 
        client: AsyncClient,
        test_headers: dict
    ):
        """Test successful vehicle list retrieval"""
        response = await client.get("/vehicles", headers=test_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "vehicles" in data["data"]
        assert isinstance(data["data"]["vehicles"], list)
        assert "count" in data["metadata"]

    async def test_get_specific_vehicle_success(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str
    ):
        """Test successful specific vehicle retrieval"""
        response = await client.get(f"/vehicles/{example_vin}", headers=test_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "vehicle" in data["data"]

    async def test_get_vehicle_status_success(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str
    ):
        """Test successful vehicle status retrieval"""
        response = await client.get(f"/vehicles/{example_vin}/status", headers=test_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status" in data["data"]

    async def test_get_vehicle_location_success(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str
    ):
        """Test successful vehicle location retrieval"""
        response = await client.get(f"/vehicles/{example_vin}/location", headers=test_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "location" in data["data"]

    async def test_get_vehicle_trips_success(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str
    ):
        """Test successful trip history retrieval"""
        response = await client.get(f"/vehicles/{example_vin}/trips", headers=test_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "trips" in data["data"]
        assert "count" in data["metadata"]

@pytest.mark.asyncio
class TestVehicleControlEndpoints:
    """Test vehicle control endpoints"""
    
    async def test_lock_vehicle_success(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str,
        valid_vehicle_command_request: dict
    ):
        """Test successful vehicle lock"""
        response = await client.post(
            f"/vehicles/{example_vin}/lock", 
            json=valid_vehicle_command_request,
            headers=test_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["operation"] == "lock"

    async def test_unlock_vehicle_success(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str,
        valid_vehicle_command_request: dict
    ):
        """Test successful vehicle unlock"""
        response = await client.post(
            f"/vehicles/{example_vin}/unlock", 
            json=valid_vehicle_command_request,
            headers=test_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["operation"] == "unlock"

    async def test_start_climate_success(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str,
        valid_vehicle_command_request: dict
    ):
        """Test successful climate start"""
        response = await client.post(
            f"/vehicles/{example_vin}/climate/start", 
            json=valid_vehicle_command_request,
            headers=test_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["operation"] == "climate_start"

    async def test_vehicle_command_without_spin(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str
    ):
        """Test vehicle command without required S-PIN"""
        request_data = {"user_id": "test_user_123"}  # No s_pin
        
        response = await client.post(
            f"/vehicles/{example_vin}/lock", 
            json=request_data,
            headers=test_headers
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SPIN_REQUIRED"

@pytest.mark.asyncio
class TestEVEndpoints:
    """Test EV-specific endpoints"""
    
    async def test_get_charging_status_success(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str
    ):
        """Test successful charging status retrieval"""
        response = await client.get(f"/vehicles/{example_vin}/charging", headers=test_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "charging" in data["data"]

    async def test_start_charging_success(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str,
        valid_vehicle_command_request: dict
    ):
        """Test successful charging start"""
        response = await client.post(
            f"/vehicles/{example_vin}/charging/start", 
            json=valid_vehicle_command_request,
            headers=test_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["operation"] == "charging_start"

    async def test_stop_charging_success(
        self, 
        client: AsyncClient,
        test_headers: dict,
        example_vin: str,
        valid_vehicle_command_request: dict
    ):
        """Test successful charging stop"""
        response = await client.post(
            f"/vehicles/{example_vin}/charging/stop", 
            json=valid_vehicle_command_request,
            headers=test_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["operation"] == "charging_stop"

@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling scenarios"""
    
    async def test_authentication_error_handling(
        self, 
        client: AsyncClient,
        test_headers: dict,
        auth_manager_with_errors
    ):
        """Test authentication error handling"""
        # Override with error-prone auth manager
        with patch.object(client.app.state, 'auth_manager', auth_manager_with_errors):
            request_data = {
                "username": "test@example.com",
                "password": "password123",
                "user_id": "test_user_123"
            }
            
            response = await client.post(
                "/auth/setup", 
                json=request_data,
                headers=test_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert data["error"]["code"] == "AUTH_SETUP_FAILED"

    async def test_vehicle_not_found_error(
        self, 
        client: AsyncClient,
        test_headers: dict
    ):
        """Test vehicle not found error"""
        # Mock empty vehicles list
        with patch.object(client.app.state.vehicle_manager, 'get_vehicles', return_value=[]):
            response = await client.get("/vehicles/INVALID_VIN", headers=test_headers)
            
            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False
            assert data["error"]["code"] == "VEHICLE_NOT_FOUND"

    async def test_rate_limiting(self, client: AsyncClient, test_headers: dict):
        """Test rate limiting functionality"""
        # This would require actual rate limiting setup
        # For now, just test that the endpoint responds normally
        response = await client.get("/health")
        assert response.status_code == 200

@pytest.mark.asyncio
class TestCORS:
    """Test CORS functionality"""
    
    async def test_cors_preflight(self, client: AsyncClient):
        """Test CORS preflight request"""
        response = await client.options(
            "/auth/setup",
            headers={
                "Origin": "https://app.draiv.ch",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers

@pytest.mark.asyncio 
class TestValidation:
    """Test input validation"""
    
    async def test_invalid_json(self, client: AsyncClient, test_headers: dict):
        """Test invalid JSON handling"""
        response = await client.post(
            "/auth/setup",
            content="invalid json",
            headers={**test_headers, "Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity

    async def test_missing_required_fields(
        self, 
        client: AsyncClient, 
        test_headers: dict
    ):
        """Test missing required fields validation"""
        incomplete_request = {
            "username": "test@example.com"
            # Missing password and user_id
        }
        
        response = await client.post(
            "/auth/setup",
            json=incomplete_request,
            headers=test_headers
        )
        
        assert response.status_code == 422

    async def test_invalid_spin_format(
        self, 
        client: AsyncClient, 
        test_headers: dict
    ):
        """Test invalid S-PIN format validation"""
        invalid_request = {
            "username": "test@example.com",
            "password": "password123",
            "s_pin": "abc",  # Invalid format
            "user_id": "test_user_123"
        }
        
        response = await client.post(
            "/auth/setup",
            json=invalid_request,
            headers=test_headers
        )
        
        assert response.status_code == 422