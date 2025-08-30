"""
BMW Connected Drive API
Production-ready integration with BMW's vehicle platform
"""

__version__ = "2.0.0"
__author__ = "DRAIV Engineering Team"

from .main import bmw_api, bmw_service
from .auth_manager import BMWAuthManager
from .vehicle_manager import BMWVehicleManager
from .remote_services import BMWRemoteServices

__all__ = [
    "bmw_api",
    "bmw_service",
    "BMWAuthManager",
    "BMWVehicleManager",
    "BMWRemoteServices"
]