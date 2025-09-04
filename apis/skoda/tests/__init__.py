"""
Skoda Connect API Test Suite

This package contains comprehensive tests for the Skoda Connect API integration,
including unit tests, integration tests, and end-to-end scenarios.

Test Structure:
- unit/: Unit tests for individual components
- integration/: Integration tests for API endpoints and workflows
- conftest.py: Shared fixtures and test configuration

Usage:
    # Run all tests
    pytest tests/
    
    # Run specific test categories
    pytest tests/unit/ -m "auth"
    pytest tests/integration/ -m "vehicle"
    
    # Run with coverage
    pytest tests/ --cov=src --cov-report=html

Test Credentials (for integration testing):
    Email: Info@miavia.ai
    Password: wozWi9-matvah-xonmyq
    S-PIN: 2405

Note: Integration tests use mocked MySkoda responses by default.
Set SKODA_USE_REAL_API=true to test against real API (use with caution).
"""

__version__ = "1.0.0"
__author__ = "DRAIV Engineering Team"