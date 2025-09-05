"""
BMW API Stateless - Docker Workaround + bimmer_connected
========================================================
UPDATED: Now uses proven Docker workaround approach with bimmer_connected.
Applies Android fingerprint patch then uses standard bimmer_connected authentication.

This replaces the manual OAuth PKCE implementation with:
- Android patch applied first (Docker workaround approach)
- Standard bimmer_connected authentication (proven library)
- Each deployment gets unique android() fingerprint for quota isolation
"""

import asyncio
import json
import logging
import os
import functions_framework
from flask import jsonify
from datetime import datetime
from typing import Dict, Any, Optional

# CRITICAL: Apply Android patch BEFORE importing bimmer_connected
# This replicates the Docker workaround approach
try:
    from utils.bmw_android_patch import apply_android_patch, get_patch_info
    patch_success = apply_android_patch()
    print(f"🔧 Android patch result: {'✅ Success' if patch_success else '❌ Failed'}")
except Exception as e:
    print(f"⚠️ Android patch error: {e}")
    patch_success = False

# NOW import bimmer_connected (after patch is applied)
try:
    from bimmer_connected.account import MyBMWAccount
    from bimmer_connected.api.regions import Regions
    print("✅ bimmer_connected imported successfully")
except ImportError as e:
    print(f"❌ Failed to import bimmer_connected: {e}")
    MyBMWAccount = None
    Regions = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def authenticate_bmw_simple(email: str, password: str, hcaptcha_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple BMW authentication using bimmer_connected library (with Android patch applied)
    
    Args:
        email: BMW account email
        password: BMW account password  
        hcaptcha_token: Optional hCaptcha token
        
    Returns:
        Dict with success status and account or error
    """
    try:
        print(f"🔐 Docker workaround authentication for {email}...")
        
        if not MyBMWAccount:
            return {
                'success': False,
                'error': 'bimmer_connected library not available'
            }
        
        # Create BMW account using standard bimmer_connected approach
        # The Android patch ensures BMW sees our unique fingerprint
        print("🚗 Creating MyBMWAccount with Docker workaround patch...")
        
        # bimmer_connected doesn't accept hcaptcha_token parameter directly
        # The library should handle auth internally
        account = MyBMWAccount(
            username=email,
            password=password,
            region=Regions.REST_OF_WORLD
        )
        
        # Test authentication by getting vehicles
        print("📋 Testing authentication by fetching vehicles...")
        vehicles = await account.get_vehicles()
        
        print(f"✅ Authentication successful! Found {len(vehicles)} vehicles")
        return {
            'success': True,
            'account': account,
            'vehicles_count': len(vehicles)
        }
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }


async def get_vehicles_simple(account: MyBMWAccount) -> Dict[str, Any]:
    """
    Get vehicles using bimmer_connected account
    
    Args:
        account: Authenticated MyBMWAccount instance
        
    Returns:
        Dict with vehicles list or error
    """
    try:
        print("🚗 Fetching vehicles...")
        vehicles = await account.get_vehicles()
        
        # Convert vehicles to serializable format
        vehicles_data = []
        for vehicle in vehicles:
            vehicle_data = {
                'vin': vehicle.vin,
                'name': vehicle.name,
                'brand': vehicle.brand,
                'model': getattr(vehicle, 'model', 'Unknown'),
                'year': getattr(vehicle, 'year', 'Unknown'),
            }
            vehicles_data.append(vehicle_data)
        
        return {
            'success': True,
            'vehicles': vehicles_data,
            'count': len(vehicles_data)
        }
        
    except Exception as e:
        print(f"❌ Error fetching vehicles: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def execute_remote_service_simple(account: MyBMWAccount, vin: str, service: str) -> Dict[str, Any]:
    """
    Execute remote service using bimmer_connected
    
    Args:
        account: Authenticated MyBMWAccount instance
        vin: Vehicle identification number
        service: Service to execute (lock, unlock, flash, etc.)
        
    Returns:
        Dict with service result or error
    """
    try:
        print(f"🔧 Executing {service} on vehicle {vin}...")
        
        # Find the vehicle
        vehicles = await account.get_vehicles()
        target_vehicle = None
        
        for vehicle in vehicles:
            if vehicle.vin == vin:
                target_vehicle = vehicle
                break
        
        if not target_vehicle:
            return {
                'success': False,
                'error': f'Vehicle {vin} not found'
            }
        
        # Execute the service based on type
        if service == 'lock':
            await target_vehicle.remote_services.trigger_remote_door_lock()
            message = 'Vehicle locked successfully'
        elif service == 'unlock':
            await target_vehicle.remote_services.trigger_remote_door_unlock()
            message = 'Vehicle unlocked successfully'
        elif service == 'flash':
            await target_vehicle.remote_services.trigger_remote_light_flash()
            message = 'Lights flashed successfully'
        elif service == 'horn':
            await target_vehicle.remote_services.trigger_remote_horn()
            message = 'Horn activated successfully'
        elif service == 'climate':
            await target_vehicle.remote_services.trigger_remote_air_conditioning()
            message = 'Climate control activated successfully'
        else:
            return {
                'success': False,
                'error': f'Unknown service: {service}'
            }
        
        print(f"✅ Service {service} executed successfully")
        return {
            'success': True,
            'service': service,
            'vehicle': vin,
            'message': message
        }
        
    except Exception as e:
        print(f"❌ Error executing service {service}: {e}")
        return {
            'success': False,
            'error': str(e),
            'service': service,
            'vehicle': vin
        }


async def get_vehicle_status_simple(account: MyBMWAccount, vin: str) -> Dict[str, Any]:
    """
    Get vehicle status using bimmer_connected
    
    Args:
        account: Authenticated MyBMWAccount instance
        vin: Vehicle identification number
        
    Returns:
        Dict with vehicle status or error
    """
    try:
        print(f"📊 Getting status for vehicle {vin}...")
        
        # Find the vehicle
        vehicles = await account.get_vehicles()
        target_vehicle = None
        
        for vehicle in vehicles:
            if vehicle.vin == vin:
                target_vehicle = vehicle
                break
        
        if not target_vehicle:
            return {
                'success': False,
                'error': f'Vehicle {vin} not found'
            }
        
        # Get basic vehicle info
        status = {
            'vin': target_vehicle.vin,
            'name': target_vehicle.name,
            'brand': target_vehicle.brand,
            'model': getattr(target_vehicle, 'model', 'Unknown'),
        }
        
        # Try to get additional status if available
        try:
            if hasattr(target_vehicle, 'fuel_and_battery'):
                fuel_battery = target_vehicle.fuel_and_battery
                status['fuel'] = {
                    'level': getattr(fuel_battery, 'remaining_fuel_percent', None),
                    'range': getattr(fuel_battery, 'remaining_range_fuel', None)
                }
        except:
            pass
        
        try:
            if hasattr(target_vehicle, 'vehicle_location'):
                location = target_vehicle.vehicle_location
                status['location'] = {
                    'latitude': getattr(location, 'latitude', None),
                    'longitude': getattr(location, 'longitude', None),
                    'address': getattr(location, 'address', None)
                }
        except:
            pass
        
        try:
            if hasattr(target_vehicle, 'doors_and_windows'):
                doors = target_vehicle.doors_and_windows
                status['doors'] = {
                    'locked': getattr(doors, 'door_lock_state', None),
                }
        except:
            pass
        
        return {
            'success': True,
            'vehicle_status': status
        }
        
    except Exception as e:
        print(f"❌ Error getting vehicle status: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@functions_framework.http
def bmw_api(request):
    """
    BMW API Stateless - Now using Docker workaround approach with bimmer_connected
    
    UPDATED: Replaced manual OAuth PKCE with proven Docker workaround + bimmer_connected
    """
    
    # Handle CORS
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return ("", 204, headers)
    
    # Health check endpoint  
    if request.method == "GET" and request.path == "/health":
        patch_info = get_patch_info()
        health_data = {
            "status": "healthy",
            "service": "bmw-api-stateless",
            "version": "3.0.0",
            "implementation": "docker_workaround_with_bimmer_connected",
            "patch_info": patch_info,
            "bimmer_connected_available": MyBMWAccount is not None,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Updated to use Docker workaround approach"
        }
        return jsonify(health_data)
    
    # Parse request
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Request body must be valid JSON"
            }), 400
        
        # Check required fields - make hcaptcha optional for testing
        required_fields = ["email", "password", "wkn"]
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "required": required_fields,
                "optional": ["hcaptcha", "action"]
            }), 400
            
    except Exception as e:
        return jsonify({
            "error": "Invalid JSON format",
            "details": str(e)
        }), 400
    
    # Extract parameters
    email = data["email"]
    password = data["password"]
    wkn = data["wkn"] 
    action = data.get("action", "status")
    hcaptcha_token = data.get("hcaptcha")
    
    print(f"🚗 Processing BMW API Stateless (Docker Workaround) request...")
    print(f"📧 Email: {email}")
    print(f"📋 Action: {action}")
    print(f"🎯 WKN: {wkn}")
    print(f"🔧 Android patch: {'✅ Applied' if patch_success else '❌ Failed'}")
    
    # Create event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        async def process_request():
            # Step 1: Authenticate with BMW (using patched bimmer_connected)
            print("🔐 Step 1: Authenticating with Docker workaround...")
            auth_result = await authenticate_bmw_simple(email, password, hcaptcha_token)
            
            if not auth_result['success']:
                return {
                    "error": "Authentication failed",
                    "details": auth_result.get('error'),
                    "error_type": auth_result.get('error_type'),
                    "hint": "Check credentials or try with hCaptcha token",
                    "implementation": "docker_workaround"
                }, 401
            
            account = auth_result['account']
            
            # Step 2: Handle different actions
            if action == "status":
                if wkn:
                    # Get specific vehicle status
                    status_result = await get_vehicle_status_simple(account, wkn)
                    if status_result['success']:
                        return {
                            "success": True,
                            "action": "status",
                            "vehicle": status_result['vehicle_status'],
                            "implementation": "docker_workaround",
                            "patch_info": get_patch_info()
                        }, 200
                    else:
                        return {
                            "error": status_result['error'],
                            "implementation": "docker_workaround"
                        }, 404
                else:
                    # Get all vehicles
                    vehicles_result = await get_vehicles_simple(account)
                    if vehicles_result['success']:
                        return {
                            "success": True,
                            "action": "status",
                            "vehicles": vehicles_result['vehicles'],
                            "count": vehicles_result['count'],
                            "implementation": "docker_workaround",
                            "patch_info": get_patch_info()
                        }, 200
                    else:
                        return {
                            "error": vehicles_result['error'],
                            "implementation": "docker_workaround"
                        }, 500
            
            elif action in ["lock", "unlock", "flash", "horn", "climate"]:
                # Execute remote service
                service_result = await execute_remote_service_simple(account, wkn, action)
                
                if service_result['success']:
                    return {
                        "success": True,
                        "action": action,
                        "vehicle": wkn,
                        "message": service_result['message'],
                        "implementation": "docker_workaround",
                        "patch_info": get_patch_info()
                    }, 200
                else:
                    return {
                        "error": service_result['error'],
                        "action": action,
                        "vehicle": wkn,
                        "implementation": "docker_workaround"
                    }, 500
            
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "available_actions": ["status", "lock", "unlock", "flash", "horn", "climate"],
                    "implementation": "docker_workaround"
                }, 400
        
        # Run the async process
        result, status_code = loop.run_until_complete(process_request())
        
        # Add CORS headers to response
        response = jsonify(result)
        response.headers["Access-Control-Allow-Origin"] = "*"
        
        return response, status_code
        
    except Exception as e:
        print(f"❌ Error processing request: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": "Internal server error",
            "details": str(e),
            "implementation": "docker_workaround",
            "patch_applied": patch_success,
            "message": "UPDATED: Now uses Docker workaround approach"
        }), 500
    
    finally:
        try:
            loop.close()
        except:
            pass


# Local testing
if __name__ == "__main__":
    print("BMW API Stateless - Docker Workaround Mode")
    print("=" * 50)
    
    # Show patch info
    patch_info = get_patch_info()
    print(f"Patch info: {patch_info}")
    
    print("\n✅ Ready for testing with Docker workaround approach!")
    print("This now uses bimmer_connected + Android fingerprint patching")