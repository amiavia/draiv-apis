"""
Unit tests for Skoda Connect API components.

This module contains unit tests for individual components of the Skoda Connect API,
including authentication, vehicle management, remote services, and utilities.

Test Files:
- test_auth_manager.py: Authentication and credential management
- test_vehicle_manager.py: Vehicle data parsing and status normalization  
- test_remote_services.py: Remote command execution and S-PIN validation
- test_utils.py: Circuit breakers, caching, rate limiting, and validation

All unit tests use mocks and don't make external API calls.
"""