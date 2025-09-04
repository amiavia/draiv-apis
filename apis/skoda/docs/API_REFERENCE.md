# Skoda Connect API Reference

Complete API reference documentation for the Skoda Connect vehicle integration service.

## Base URL

- **Development**: `http://localhost:8080`
- **Staging**: `https://staging-api.draiv.ch/skoda`
- **Production**: `https://api.draiv.ch/skoda`

## Authentication

All API endpoints require authentication except for health checks and documentation.

### Login

**POST** `/auth/login`

Authenticate with Skoda Connect credentials.

#### Request Body

```json
{
  "username": "string",      // Skoda Connect email/username
  "password": "string",      // Skoda Connect password  
  "force_refresh": false     // Force new authentication
}
```

#### Response

```json
{
  "status": "success",
  "message": "Authentication successful",
  "timestamp": "2025-01-30T10:00:00Z"
}
```

#### Error Response

```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid credentials",
    "timestamp": "2025-01-30T10:00:00Z",
    "suggestions": [
      "Check username and password",
      "Verify account is active"
    ]
  }
}
```

---

## Vehicle Management

### List Vehicles

**GET** `/vehicles`

Retrieve list of all vehicles associated with the authenticated user.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force_refresh` | boolean | `false` | Bypass cache and fetch fresh data |

#### Response

```json
{
  "success": true,
  "vehicles": [
    {
      "vin": "TMBJT2N20N1234567",
      "brand": "Skoda",
      "model": "Octavia", 
      "name": "My Octavia",
      "license_plate": "ABC123",
      "vehicle_type": "electric",
      "capabilities": ["charging", "location", "lock_unlock"]
    }
  ],
  "count": 1,
  "timestamp": "2025-01-30T10:00:00Z",
  "api_provider": "skoda_connect"
}
```

#### Vehicle Types

- `ice` - Internal combustion engine
- `electric` - Battery electric vehicle
- `hybrid` - Hybrid vehicle
- `plug_in_hybrid` - Plug-in hybrid
- `unknown` - Type not determined

### Get Vehicle Status

**GET** `/vehicles/{vin}/status`

Get comprehensive status information for a specific vehicle.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `vin` | string | Vehicle VIN (17 characters) |

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force_refresh` | boolean | `false` | Bypass cache and fetch fresh data |

#### Response

```json
{
  "success": true,
  "vehicle": {
    "vin": "TMBJT2N20N1234567",
    "vehicle_info": {
      "vin": "TMBJT2N20N1234567",
      "brand": "Skoda",
      "model": "Octavia",
      "year": "2023",
      "name": "My Octavia",
      "license_plate": "ABC123",
      "color": "Red",
      "vehicle_type": "electric"
    },
    "energy": {
      "vehicle_type": "electric",
      "battery": {
        "level_percent": 85,
        "range_km": 200,
        "charging_state": "not_connected",
        "charging_power_kw": 0,
        "time_to_full_minutes": null,
        "target_level_percent": 80
      },
      "fuel": null,
      "total_range_km": 200
    },
    "location": {
      "available": true,
      "coordinates": {
        "latitude": 50.0755,
        "longitude": 14.4378
      },
      "address": {
        "street": "Václavské náměstí",
        "city": "Prague",
        "postal_code": "110 00",
        "country": "Czech Republic",
        "formatted_address": "Václavské náměstí, Prague, Czech Republic"
      },
      "timestamp": "2025-01-30T10:00:00Z",
      "accuracy_meters": 5
    },
    "doors_windows": {
      "available": true,
      "locked": "locked",
      "doors_closed": true,
      "windows_closed": true,
      "trunk_closed": true,
      "hood_closed": true
    },
    "climate": {
      "available": true,
      "state": "off",
      "target_temperature_celsius": 22,
      "remaining_time_minutes": 0,
      "defrost_active": false
    },
    "service_info": {
      "available": true,
      "intervals": [
        {
          "name": "Next Service",
          "next_service_km": 15000,
          "next_service_days": 180,
          "overdue": false
        }
      ],
      "last_service_km": 5000,
      "next_inspection_km": 20000
    },
    "capabilities": ["charging", "location", "lock_unlock", "climate"],
    "last_updated": "2025-01-30T10:00:00Z",
    "api_provider": "skoda_connect"
  },
  "timestamp": "2025-01-30T10:00:00Z"
}
```

#### Charging States

- `not_connected` - Charging cable not connected
- `connected` - Cable connected but not charging
- `charging` - Currently charging
- `charge_purpose_reached` - Target charge level reached
- `conservation` - Battery conservation mode
- `error` - Charging error
- `unknown` - State not available

#### Lock States

- `locked` - Vehicle is locked
- `unlocked` - Vehicle is unlocked  
- `partial` - Some doors/windows unlocked
- `unknown` - State not available

---

## Location Services

### Get Vehicle Location

**GET** `/vehicles/{vin}/location`

Get current vehicle location with optional address resolution.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `vin` | string | Vehicle VIN (17 characters) |

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_address` | boolean | `true` | Resolve coordinates to human-readable address |

#### Response

```json
{
  "success": true,
  "vin": "TMBJT2N20N1234567",
  "location": {
    "available": true,
    "coordinates": {
      "latitude": 50.0755,
      "longitude": 14.4378
    },
    "address": {
      "street": "Václavské náměstí",
      "city": "Prague", 
      "postal_code": "110 00",
      "country": "Czech Republic",
      "formatted_address": "Václavské náměstí, Prague, Czech Republic"
    },
    "timestamp": "2025-01-30T10:00:00Z",
    "accuracy_meters": 5
  },
  "timestamp": "2025-01-30T10:00:00Z"
}
```

---

## Trip Statistics

### Get Trip History

**GET** `/vehicles/{vin}/trips`

Get vehicle trip statistics and history for a specified period.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `vin` | string | Vehicle VIN (17 characters) |

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | `30` | Number of days to include (1-365) |

#### Response

```json
{
  "success": true,
  "vin": "TMBJT2N20N1234567",
  "statistics": {
    "period_start": "2025-01-01T00:00:00Z",
    "period_end": "2025-01-30T23:59:59Z",
    "total_distance_km": 1250.5,
    "total_trips": 45,
    "avg_consumption": 18.5,
    "avg_trip_distance_km": 27.8,
    "trips": [
      {
        "start_time": "2025-01-30T08:00:00Z",
        "end_time": "2025-01-30T08:30:00Z",
        "distance_km": 15.2,
        "duration_minutes": 30,
        "consumption": 2.8,
        "start_location": {
          "city": "Prague",
          "formatted_address": "Prague, Czech Republic"
        },
        "end_location": {
          "city": "Prague",
          "formatted_address": "Prague, Czech Republic"  
        }
      }
    ]
  },
  "timestamp": "2025-01-30T10:00:00Z"
}
```

---

## Electric Vehicle Features

### Get Charging Status

**GET** `/vehicles/{vin}/charging`

Get detailed charging status for electric vehicles.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `vin` | string | Vehicle VIN (17 characters) |

#### Response

```json
{
  "success": true,
  "vin": "TMBJT2N20N1234567",
  "charging": {
    "level_percent": 85,
    "range_km": 200,
    "charging_state": "charging",
    "charging_power_kw": 7.4,
    "time_to_full_minutes": 45,
    "target_level_percent": 90
  },
  "timestamp": "2025-01-30T10:00:00Z"
}
```

#### Non-EV Response

```json
{
  "success": true,
  "vin": "TMBJT2N20N1234567", 
  "charging": {
    "error": "Vehicle does not support EV charging",
    "is_electric": false
  },
  "timestamp": "2025-01-30T10:00:00Z"
}
```

---

## Service Information

### Get Service Intervals

**GET** `/vehicles/{vin}/service`

Get vehicle maintenance schedule and service intervals.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `vin` | string | Vehicle VIN (17 characters) |

#### Response

```json
{
  "success": true,
  "vin": "TMBJT2N20N1234567",
  "service": {
    "available": true,
    "intervals": [
      {
        "name": "Oil Change",
        "next_service_km": 15000,
        "next_service_days": 180,
        "overdue": false
      },
      {
        "name": "Brake Inspection",
        "next_service_km": 25000,
        "next_service_days": 365,
        "overdue": false
      }
    ],
    "last_service_km": 5000,
    "next_inspection_km": 20000
  },
  "timestamp": "2025-01-30T10:00:00Z"
}
```

---

## Vehicle Capabilities

### Get Vehicle Capabilities

**GET** `/vehicles/{vin}/capabilities`

Get list of features and capabilities supported by the vehicle.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `vin` | string | Vehicle VIN (17 characters) |

#### Response

```json
{
  "success": true,
  "vin": "TMBJT2N20N1234567",
  "capabilities": [
    "charging",
    "location", 
    "lock_unlock",
    "climate",
    "honk_flash",
    "trip_statistics",
    "service_info"
  ],
  "timestamp": "2025-01-30T10:00:00Z"
}
```

#### Available Capabilities

- `charging` - EV charging control and status
- `fuel` - Fuel level monitoring (ICE vehicles)
- `location` - GPS location tracking
- `climate` - Climate control
- `lock_unlock` - Door lock/unlock
- `honk_flash` - Horn and flash lights
- `trip_statistics` - Trip history and analytics
- `service_info` - Service intervals and maintenance

---

## System Endpoints

### Health Check

**GET** `/health`

Check service health and get system status.

#### Response

```json
{
  "status": "healthy",
  "timestamp": "2025-01-30T10:00:00Z",
  "version": "1.0.0",
  "service": "skoda-connect-api",
  "uptime_seconds": 3600,
  "cache_stats": {
    "hits": 150,
    "misses": 25,
    "hit_rate": "85.71%",
    "size": 42
  },
  "error_stats": {
    "status": "healthy",
    "total_errors": 0
  }
}
```

### Cache Statistics

**GET** `/admin/cache/stats`

Get detailed cache performance statistics (admin only).

#### Response

```json
{
  "size": 42,
  "max_size": 1000,
  "hits": 150,
  "misses": 25,
  "hit_rate": "85.71%",
  "evictions": 0,
  "expirations": 5,
  "total_requests": 175
}
```

### Error Statistics

**GET** `/admin/errors/stats`

Get error tracking and analytics (admin only).

#### Response

```json
{
  "total_errors": 3,
  "unique_error_types": 2,
  "error_counts_by_type": {
    "AuthenticationError": 2,
    "VehicleNotFoundError": 1
  },
  "most_common_errors": [
    ["AuthenticationError", 2],
    ["VehicleNotFoundError", 1]
  ],
  "recent_errors": [
    {
      "message": "Vehicle with VIN ABC123 not found",
      "code": "VEHICLE_NOT_FOUND",
      "timestamp": "2025-01-30T09:45:00Z",
      "vin": "ABC123"
    }
  ],
  "statistics_generated": "2025-01-30T10:00:00Z"
}
```

### Clear Cache

**POST** `/admin/cache/clear`

Clear application cache (admin only).

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vin` | string | No | Clear cache for specific VIN only |

#### Response

```json
{
  "status": "success",
  "message": "Cache cleared (all)"
}
```

---

## Error Handling

### Error Response Format

All error responses follow a consistent format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "timestamp": "2025-01-30T10:00:00Z",
    "type": "error_category",
    "details": "Additional context",
    "suggestions": [
      "Possible solution 1",
      "Possible solution 2"
    ]
  }
}
```

### HTTP Status Codes

| Status Code | Description | Common Causes |
|-------------|-------------|---------------|
| `200` | Success | Request completed successfully |
| `400` | Bad Request | Invalid input parameters |
| `401` | Unauthorized | Authentication required or failed |
| `404` | Not Found | Vehicle or resource not found |
| `422` | Unprocessable Entity | Valid syntax but semantically incorrect |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server-side error |
| `503` | Service Unavailable | Circuit breaker open or service down |

### Error Codes

#### Authentication Errors
- `AUTHENTICATION_ERROR` - Invalid credentials or authentication failure
- `SPIN_VALIDATION_ERROR` - S-PIN validation failed

#### Vehicle Errors  
- `VEHICLE_NOT_FOUND` - Vehicle with specified VIN not found
- `VEHICLE_CAPABILITY_ERROR` - Vehicle doesn't support requested feature

#### System Errors
- `VALIDATION_ERROR` - Request validation failed
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `EXTERNAL_SERVICE_ERROR` - Skoda Connect API unavailable
- `CIRCUIT_BREAKER_OPEN` - Service temporarily unavailable

## Rate Limiting

API requests are rate limited to prevent abuse:

- **Default Limit**: 60 requests per minute per IP
- **Burst Limit**: 10 requests per second
- **Headers**: Rate limit information included in response headers

### Rate Limit Headers

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45  
X-RateLimit-Reset: 1643546400
```

## Caching

The API implements intelligent caching to optimize performance:

### Cache TTL by Data Type

| Data Type | TTL | Reason |
|-----------|-----|--------|
| Vehicle List | 5 minutes | Vehicles rarely added/removed |
| Vehicle Status | 1 minute | Dynamic data updates frequently |
| Location | 30 seconds | Location changes frequently |
| Auth Tokens | 1 hour | Based on token expiry |
| Capabilities | 24 hours | Static vehicle features |
| Trip Statistics | 15 minutes | Historical data updates slowly |

### Cache Control

- Use `force_refresh=true` to bypass cache
- Cache keys include VIN and user context
- Automatic cache invalidation on errors
- Distributed cache with Redis in production

## Pagination

For endpoints returning large datasets, pagination is available:

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number |
| `limit` | integer | `50` | Items per page (max 100) |

### Response Format

```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

---

*Last Updated: January 2025*  
*API Version: 1.0.0*