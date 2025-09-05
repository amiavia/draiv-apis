"""
Comprehensive tests for BMW API quota handling functionality
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.error_handler import QuotaLimitError, AuthenticationError, BMWAPIError
from utils.user_agent_manager import UserAgentManager
from utils.circuit_breaker import CircuitBreaker, CircuitState
from auth_manager import BMWAuthManager


class TestUserAgentManager:
    """Test dynamic user agent generation"""
    
    def test_instance_id_generation(self):
        """Test stable instance ID generation"""
        manager1 = UserAgentManager()
        manager2 = UserAgentManager()
        
        # Should generate different IDs for different managers
        id1 = manager1.instance_id
        id2 = manager2.instance_id
        
        assert id1 != id2
        assert len(id1) == 36  # UUID length
    
    def test_user_agent_format(self):
        """Test user agent string format"""
        manager = UserAgentManager()
        user_agent = manager.user_agent
        
        assert user_agent.startswith("draiv-bmw-api/")
        assert len(user_agent.split("/")[1]) == 16  # Hash length
    
    def test_user_agent_consistency(self):
        """Test user agent remains consistent"""
        manager = UserAgentManager()
        agent1 = manager.user_agent
        agent2 = manager.user_agent
        
        assert agent1 == agent2
    
    def test_headers_generation(self):
        """Test HTTP headers generation"""
        manager = UserAgentManager()
        headers = manager.get_headers()
        
        assert "x-user-agent" in headers
        assert "User-Agent" in headers
        assert headers["x-user-agent"] == headers["User-Agent"]
        assert headers["x-user-agent"].startswith("draiv-bmw-api/")
    
    def test_reset_functionality(self):
        """Test user agent reset functionality"""
        manager = UserAgentManager()
        original_agent = manager.user_agent
        new_agent = manager.reset_user_agent()
        
        assert original_agent != new_agent
        assert new_agent.startswith("draiv-bmw-api/")


class TestQuotaErrorParsing:
    """Test BMW quota error message parsing"""
    
    def test_parse_quota_error_with_time(self):
        """Test parsing quota error with replenishment time"""
        auth_manager = BMWAuthManager("test-bucket")
        
        error_message = "Out of call volume quota. Quota will be replenished in 01:20:30"
        result = auth_manager._parse_quota_error(error_message)
        
        assert result is not None
        assert result["retry_after"] == 4830  # 1*3600 + 20*60 + 30
        assert "BMW API quota limit exceeded" in result["message"]
    
    def test_parse_quota_error_simple_time(self):
        """Test parsing quota error with simple time format"""
        auth_manager = BMWAuthManager("test-bucket")
        
        error_message = "Too many requests. Wait 300 seconds"
        result = auth_manager._parse_quota_error(error_message)
        
        assert result is not None
        assert result["retry_after"] == 300
    
    def test_parse_quota_error_minutes(self):
        """Test parsing quota error with minutes"""
        auth_manager = BMWAuthManager("test-bucket")
        
        error_message = "Quota limit exceeded. Retry after 5 minutes"
        result = auth_manager._parse_quota_error(error_message)
        
        assert result is not None
        assert result["retry_after"] == 300  # 5 * 60
    
    def test_parse_non_quota_error(self):
        """Test parsing non-quota error returns None"""
        auth_manager = BMWAuthManager("test-bucket")
        
        error_message = "Invalid credentials provided"
        result = auth_manager._parse_quota_error(error_message)
        
        assert result is None
    
    def test_parse_quota_error_no_time(self):
        """Test parsing quota error without time information"""
        auth_manager = BMWAuthManager("test-bucket")
        
        error_message = "Out of call volume quota"
        result = auth_manager._parse_quota_error(error_message)
        
        assert result is not None
        assert result["retry_after"] is None


class TestCircuitBreakerQuotaHandling:
    """Test circuit breaker quota handling functionality"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing"""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            name="TestBreaker"
        )
    
    def test_quota_error_triggers_pause(self, circuit_breaker):
        """Test that quota error triggers circuit pause"""
        # Simulate quota error
        quota_error = QuotaLimitError("Quota exceeded", retry_after=300)
        circuit_breaker._on_quota_error(quota_error)
        
        assert circuit_breaker.state == CircuitState.QUOTA_PAUSED
        assert circuit_breaker.quota_retry_count == 1
        assert circuit_breaker.quota_pause_until is not None
    
    def test_quota_pause_duration(self, circuit_breaker):
        """Test quota pause duration calculation"""
        quota_error = QuotaLimitError("Quota exceeded", retry_after=120)
        circuit_breaker._on_quota_error(quota_error)
        
        # Should pause for exactly 120 seconds
        expected_resume = datetime.now() + timedelta(seconds=120)
        actual_resume = circuit_breaker.quota_pause_until
        
        # Allow 2 second tolerance for test execution time
        assert abs((actual_resume - expected_resume).total_seconds()) < 2
    
    def test_quota_pause_without_retry_after(self, circuit_breaker):
        """Test quota pause with default exponential backoff"""
        quota_error = QuotaLimitError("Quota exceeded")  # No retry_after
        circuit_breaker._on_quota_error(quota_error)
        
        # Should use default 60 seconds for first retry
        expected_resume = datetime.now() + timedelta(seconds=60)
        actual_resume = circuit_breaker.quota_pause_until
        
        assert abs((actual_resume - expected_resume).total_seconds()) < 2
    
    def test_quota_exponential_backoff(self, circuit_breaker):
        """Test exponential backoff for multiple quota errors"""
        quota_error = QuotaLimitError("Quota exceeded")
        
        # First error: 60 seconds
        circuit_breaker._on_quota_error(quota_error)
        assert circuit_breaker.quota_retry_count == 1
        
        # Second error: 120 seconds  
        circuit_breaker._on_quota_error(quota_error)
        assert circuit_breaker.quota_retry_count == 2
        
        # Third error: 240 seconds
        circuit_breaker._on_quota_error(quota_error)
        assert circuit_breaker.quota_retry_count == 3
    
    def test_quota_resume_condition(self, circuit_breaker):
        """Test quota resume condition"""
        # Set quota pause in the past
        circuit_breaker.quota_pause_until = datetime.now() - timedelta(seconds=10)
        
        assert circuit_breaker._should_resume_from_quota() is True
        
        # Set quota pause in the future
        circuit_breaker.quota_pause_until = datetime.now() + timedelta(seconds=60)
        
        assert circuit_breaker._should_resume_from_quota() is False
    
    async def test_circuit_quota_pause_blocks_calls(self, circuit_breaker):
        """Test that quota paused circuit blocks calls"""
        # Set circuit to quota paused state
        circuit_breaker.state = CircuitState.QUOTA_PAUSED
        circuit_breaker.quota_pause_until = datetime.now() + timedelta(seconds=60)
        
        async def test_func():
            return "success"
        
        with pytest.raises(QuotaLimitError) as exc_info:
            await circuit_breaker.call(test_func)
        
        assert "BMW API quota limit active" in str(exc_info.value)
        assert exc_info.value.retry_after is not None
    
    def test_success_resets_quota_count(self, circuit_breaker):
        """Test that successful call resets quota retry count"""
        circuit_breaker.quota_retry_count = 3
        circuit_breaker._on_success()
        
        assert circuit_breaker.quota_retry_count == 0
    
    def test_circuit_stats_include_quota_info(self, circuit_breaker):
        """Test that circuit stats include quota information"""
        quota_error = QuotaLimitError("Quota exceeded", retry_after=300)
        circuit_breaker._on_quota_error(quota_error)
        
        stats = circuit_breaker.get_stats()
        
        assert "quota_retry_count" in stats
        assert "quota_pause_until" in stats
        assert "time_until_quota_resume" in stats
        assert stats["quota_retry_count"] == 1
        assert stats["quota_pause_until"] is not None


class TestQuotaLimitErrorHandling:
    """Test QuotaLimitError exception handling"""
    
    def test_quota_error_creation(self):
        """Test QuotaLimitError creation with retry_after"""
        error = QuotaLimitError("Quota exceeded", retry_after=300)
        
        assert str(error) == "Quota exceeded"
        assert error.code == "QUOTA_LIMIT_EXCEEDED"
        assert error.retry_after == 300
    
    def test_quota_error_without_retry_after(self):
        """Test QuotaLimitError creation without retry_after"""
        error = QuotaLimitError("Quota exceeded")
        
        assert str(error) == "Quota exceeded"
        assert error.code == "QUOTA_LIMIT_EXCEEDED"
        assert error.retry_after is None


class TestIntegrationScenarios:
    """Integration tests for quota handling scenarios"""
    
    @pytest.fixture
    def mock_bmw_account(self):
        """Mock BMW account for testing"""
        account = Mock()
        account.get_vehicles = Mock()
        return account
    
    @patch('auth_manager.MyBMWAccount')
    @patch('auth_manager.load_oauth_store_from_file')
    async def test_auth_quota_error_flow(self, mock_load_oauth, mock_account_class, mock_bmw_account):
        """Test complete authentication quota error flow"""
        # Setup mocks
        mock_account_class.return_value = mock_bmw_account
        mock_bmw_account.get_vehicles.side_effect = Exception(
            "Out of call volume quota. Quota will be replenished in 00:30:00"
        )
        
        auth_manager = BMWAuthManager("test-bucket")
        auth_manager._download_oauth_token = Mock(return_value=True)
        
        with pytest.raises(QuotaLimitError) as exc_info:
            await auth_manager.authenticate("test@example.com", "password")
        
        assert "BMW API quota limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after == 1800  # 30 minutes
    
    async def test_circuit_breaker_quota_integration(self):
        """Test circuit breaker integration with quota errors"""
        circuit_breaker = CircuitBreaker(failure_threshold=3, name="IntegrationTest")
        
        async def failing_function():
            raise QuotaLimitError("API quota exceeded", retry_after=60)
        
        # First call should trigger quota pause
        with pytest.raises(QuotaLimitError):
            await circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitState.QUOTA_PAUSED
        
        # Subsequent calls should be blocked
        with pytest.raises(QuotaLimitError) as exc_info:
            await circuit_breaker.call(failing_function)
        
        assert "BMW API quota limit active" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])