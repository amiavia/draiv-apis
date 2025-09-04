# PRP-002-API: Skoda Connect API Backend Integration

**Author**: DRAIV Engineering Team  
**Date**: January 2025  
**Status**: APPROVED  
**Priority**: P0 - Critical Business Feature  
**Impact**: Enables Skoda vehicle support for ~30% of DRAIV's target market
**Document Type**: Backend API Implementation

## Executive Summary

### Problem Statement
DRAIV currently supports only BMW vehicles through the BMW Connected Drive API. Skoda represents a significant portion of the Swiss rental car market (30%+ market share), and our platform cannot serve Skoda vehicle owners/renters. This limits our market reach and competitive positioning.

### Business Value
- **Market Expansion**: Access to 30% additional market share in Switzerland
- **Customer Satisfaction**: Complete vehicle control for Skoda owners/renters
- **Competitive Advantage**: First unified platform supporting multiple manufacturers
- **Revenue Growth**: Estimated 25-35% increase in addressable market

### Success Metrics
- 100% feature parity with BMW API (lock/unlock, status, location)
- <500ms p95 response time for status queries
- <5s response time for remote commands
- 99.9% availability SLA
- Zero security incidents in first 90 days
- 80%+ test coverage

## Current State Analysis

### BMW API Implementation Review
Based on analysis of `/apis/bmw/`, the current implementation includes:

**Architecture Patterns**:
```python
bmw/
├── src/
│   ├── main.py              # FastAPI/Flask entry point
│   ├── auth_manager.py      # OAuth token management
│   ├── vehicle_manager.py   # Vehicle operations
│   ├── remote_services.py   # Command execution
│   └── utils.py            # Shared utilities
```

**Authentication Flow**:
1. User provides email/password via API
2. hCaptcha verification for first-time authentication
3. OAuth tokens obtained from BMW servers
4. Tokens stored in Google Cloud Storage (user-specific)
5. Automatic token refresh on expiry
6. Circuit breaker for failed authentications

**Security Measures**:
- OAuth tokens encrypted in Cloud Storage
- User-specific token isolation (`oauth_tokens/{user_id}_token.json`)
- Rate limiting per user (10 req/min)
- Input validation with Pydantic
- No credential logging
- HTTPS-only communication

**User Onboarding**:
1. User registers on DRAIV platform
2. Links BMW account (email/password)
3. Completes hCaptcha verification
4. System validates with BMW servers
5. Tokens stored securely
6. Ready for vehicle operations

## Proposed Solution

### Skoda API Integration Approach

**Primary Library**: MySkoda (Python)
- Repository: https://github.com/skodaconnect/myskoda
- Actively maintained (2024-2025)
- Async/await architecture
- Home Assistant integration proven
- Replaces deprecated skodaconnect library

**Authentication Method**:
- Username/password authentication
- Optional S-PIN for privileged operations (lock/unlock)
- Session-based token management
- No OAuth flow (simpler than BMW)

**Key Capabilities**:
- Vehicle status (doors, windows, fuel/battery)
- Remote lock/unlock (requires S-PIN)
- Climate control (start/stop)
- Location tracking
- Trip statistics
- Charging control (EVs)
- Service intervals

## Technical Architecture

### Module Structure
```
draiv-apis/
├── apis/
│   ├── bmw/                    # Existing BMW API
│   └── skoda/                  # New Skoda API
│       ├── src/
│       │   ├── main.py         # FastAPI application
│       │   ├── auth_manager.py # Credential management
│       │   ├── vehicle_manager.py # Vehicle operations
│       │   ├── models.py       # Pydantic models
│       │   └── utils.py        # Skoda-specific utilities
│       ├── tests/
│       │   ├── unit/
│       │   └── integration/
│       ├── requirements.txt    # myskoda + dependencies
│       └── Dockerfile
├── shared/                     # Reused components
│   ├── monitoring/            # Logging, metrics
│   ├── circuit_breaker/      # Fault tolerance
│   └── cache/                 # Redis caching
```

### Shared vs. Specific Components

**Shared Components** (from `/shared/`):
- Circuit breaker implementation
- Structured logging
- Metrics collection
- Cache manager
- Error response formatting
- Rate limiting middleware

**Skoda-Specific Components**:
- MySkoda library integration
- S-PIN management
- Session token handling
- Skoda error mapping
- Vehicle capability detection

### API Endpoints

```python
# Base URL: /api/skoda

POST   /auth/setup           # Initial account setup
POST   /auth/validate        # Validate credentials
DELETE /auth/remove          # Remove account

GET    /vehicles             # List all vehicles
GET    /vehicles/{vin}       # Get specific vehicle
GET    /vehicles/{vin}/status # Detailed status

POST   /vehicles/{vin}/lock   # Lock vehicle
POST   /vehicles/{vin}/unlock # Unlock vehicle
POST   /vehicles/{vin}/climate/start # Start climate
POST   /vehicles/{vin}/climate/stop  # Stop climate
GET    /vehicles/{vin}/location # Get location
GET    /vehicles/{vin}/trips    # Trip history

# EV-specific
GET    /vehicles/{vin}/charging # Charging status
POST   /vehicles/{vin}/charging/start # Start charging
POST   /vehicles/{vin}/charging/stop  # Stop charging
```

## Security Considerations

### Authentication & Authorization

**Credential Storage**:
```python
# Following BMW pattern but adapted for username/password
storage_path = f"credentials/skoda/{user_id}_creds.json"

encrypted_data = {
    "username": encrypt(username),
    "password": encrypt(password),
    "s_pin": encrypt(s_pin) if s_pin else None,
    "created_at": datetime.utcnow(),
    "last_validated": datetime.utcnow()
}
```

**S-PIN Management**:
- Optional but required for lock/unlock
- Stored separately from main credentials
- Additional encryption layer
- User can update independently

**Session Management**:
- MySkoda sessions expire after 30 minutes
- Automatic session renewal
- Circuit breaker for failed renewals
- Graceful degradation without S-PIN

### Data Privacy

- No logging of credentials or S-PIN
- Vehicle data cached for 60 seconds
- Location data requires explicit consent
- GDPR-compliant data handling
- User can delete all data anytime

### Rate Limiting

```python
RATE_LIMITS = {
    "status_query": "30/minute",
    "remote_command": "10/minute",
    "auth_operation": "5/minute",
    "vehicle_list": "10/minute"
}
```

## Implementation Plan

### Phase 1: Core Authentication (Week 1-2)
- [ ] Set up Skoda module structure
- [ ] Integrate MySkoda library
- [ ] Implement credential management
- [ ] S-PIN handling
- [ ] Session management
- [ ] Unit tests for auth

### Phase 2: Vehicle Status (Week 3)
- [ ] Vehicle listing endpoint
- [ ] Status query endpoint
- [ ] Location endpoint
- [ ] Caching implementation
- [ ] Error handling
- [ ] Integration tests

### Phase 3: Vehicle Control (Week 4)
- [ ] Lock/unlock endpoints
- [ ] Climate control
- [ ] Circuit breaker integration
- [ ] Command queueing
- [ ] Retry logic
- [ ] E2E tests

### Phase 4: Advanced Features (Week 5)
- [ ] EV charging control
- [ ] Trip statistics
- [ ] Service intervals
- [ ] Notification webhooks
- [ ] Performance optimization

### Phase 5: Production Readiness (Week 6)
- [ ] Security audit
- [ ] Load testing
- [ ] Documentation
- [ ] Monitoring setup
- [ ] Deployment pipeline
- [ ] Rollback procedures

## Testing Strategy

### Unit Tests (Target: 85% coverage)
```python
# Example test structure
def test_credential_encryption():
    """Verify credentials are properly encrypted"""
    
def test_session_renewal():
    """Test automatic session renewal"""
    
def test_spin_validation():
    """Validate S-PIN format and storage"""
```

### Integration Tests
- Mock MySkoda responses
- Test all API endpoints
- Verify error handling
- Circuit breaker behavior
- Cache invalidation

### Security Tests
- Credential encryption verification
- Rate limiting enforcement
- Input validation
- SQL injection prevention
- Token leakage prevention

### Performance Tests
- 1000 concurrent users
- Response time benchmarks
- Cache hit ratios
- Circuit breaker thresholds
- Memory usage patterns

## Deployment Considerations

### Environment Configuration
```yaml
# Environment variables
SKODA_API_BASE_URL: "https://api.myskoda.com"
SKODA_CACHE_TTL: 60
SKODA_SESSION_TIMEOUT: 1800
SKODA_MAX_RETRIES: 3
ENCRYPTION_KEY: "${SECRET_ENCRYPTION_KEY}"
REDIS_URL: "${REDIS_CONNECTION_STRING}"
```

### Google Cloud Functions Deployment
```yaml
# Function configuration
runtime: python310
entry_point: main
memory: 512MB
timeout: 60s
max_instances: 100
min_instances: 1

environment_variables:
  SERVICE_NAME: "skoda-api"
  LOG_LEVEL: "INFO"
```

### Rollback Strategy
1. Blue-green deployment
2. Canary releases (5% → 25% → 100%)
3. Automatic rollback on error rate >5%
4. Manual override capability
5. Previous version retention (3 versions)

## API Specification

### Lock Vehicle Example
```http
POST /api/skoda/vehicles/{vin}/lock
Content-Type: application/json

{
    "user_id": "user_123",
    "s_pin": "1234"  // Optional but required for this operation
}

Response 200 OK:
{
    "success": true,
    "data": {
        "operation": "lock",
        "status": "completed",
        "vehicle": {
            "vin": "TMBJB7NE6L1234567",
            "model": "Octavia",
            "year": 2024
        },
        "timestamp": "2025-01-30T10:30:00Z"
    }
}

Response 403 Forbidden:
{
    "success": false,
    "error": {
        "code": "SPIN_REQUIRED",
        "message": "S-PIN required for lock operation",
        "details": "Please provide S-PIN or set it up in account settings"
    }
}
```

### Vehicle Status Example
```http
GET /api/skoda/vehicles/{vin}/status

Response 200 OK:
{
    "success": true,
    "data": {
        "vehicle": {
            "vin": "TMBJB7NE6L1234567",
            "model": "Octavia",
            "year": 2024
        },
        "status": {
            "doors": {
                "locked": true,
                "driver": "closed",
                "passenger": "closed",
                "rear_left": "closed",
                "rear_right": "closed"
            },
            "windows": {
                "driver": "closed",
                "passenger": "closed",
                "rear_left": "closed",
                "rear_right": "closed"
            },
            "fuel": {
                "level": 65,
                "range_km": 520
            },
            "mileage_km": 15234,
            "location": {
                "latitude": 47.3769,
                "longitude": 8.5417,
                "address": "Zürich, Switzerland",
                "updated_at": "2025-01-30T10:25:00Z"
            }
        },
        "cached": false,
        "timestamp": "2025-01-30T10:30:00Z"
    }
}
```

## Risks & Mitigations

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| MySkoda API changes | High | Medium | Version pinning, monitoring, abstraction layer |
| Rate limiting by Skoda | High | Medium | Request queuing, caching, circuit breaker |
| Session management issues | Medium | Medium | Automatic renewal, retry logic, fallbacks |
| S-PIN complexity | Medium | Low | Clear documentation, optional for non-critical ops |
| Library maintenance | High | Low | Fork capability, alternative library research |

### Security Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Credential leakage | Critical | Low | Encryption, secure storage, audit logging |
| Man-in-the-middle | High | Low | Certificate pinning, HTTPS only |
| Brute force attacks | Medium | Medium | Rate limiting, account lockout |
| S-PIN exposure | High | Low | Separate encryption, memory clearing |

### Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Low adoption | Medium | Medium | User education, seamless onboarding |
| Support burden | Medium | Medium | Comprehensive documentation, FAQs |
| Skoda API shutdown | Critical | Low | Contract negotiation, alternative solutions |

## Success Criteria

### Technical Metrics
- ✅ All endpoints operational with <500ms p95 latency
- ✅ 99.9% uptime over 30 days
- ✅ Zero critical security vulnerabilities
- ✅ 85%+ test coverage
- ✅ <5% error rate

### Business Metrics
- ✅ 100+ Skoda vehicles onboarded in first month
- ✅ 90%+ user satisfaction score
- ✅ <2% support ticket rate
- ✅ Feature parity with BMW API
- ✅ Successful operations for all Skoda models 2020+

### Operational Metrics
- ✅ <5 minute mean time to recovery
- ✅ Automated deployment pipeline
- ✅ Comprehensive monitoring dashboards
- ✅ Alert response time <15 minutes
- ✅ Documentation completeness score >90%

## Timeline & Resources

### Development Timeline (6 weeks)
- **Week 1-2**: Core authentication & setup
- **Week 3**: Vehicle status implementation
- **Week 4**: Vehicle control features
- **Week 5**: Advanced features & optimization
- **Week 6**: Testing, security audit, deployment

### Required Resources
- **Development**: 1 senior engineer (full-time)
- **Testing**: 1 QA engineer (50%)
- **DevOps**: 1 engineer (25%)
- **Security**: Security audit (external)
- **Documentation**: Technical writer (25%)

### Dependencies
- MySkoda library (v2.x)
- Google Cloud Storage access
- Redis instance
- Monitoring infrastructure
- Test Skoda vehicles (2-3)

## Monitoring & Observability

### Key Metrics Dashboard
```python
METRICS = {
    "api_requests_total": Counter,
    "api_request_duration": Histogram,
    "auth_success_rate": Gauge,
    "cache_hit_ratio": Gauge,
    "circuit_breaker_state": Enum,
    "active_sessions": Gauge,
    "error_rate": Gauge
}
```

### Alerts Configuration
- API error rate >5% (P1)
- Response time >1s p95 (P2)
- Circuit breaker open (P1)
- Authentication failures >10/min (P2)
- Cache miss ratio >50% (P3)

### Logging Standards
```python
logger.info("Skoda API request", extra={
    "user_id": user_id,
    "operation": "lock",
    "vin": vin,
    "duration_ms": 234,
    "cache_hit": False,
    "success": True
})
```

## Post-Launch Considerations

### Phase 2 Enhancements (Month 2-3)
- Batch operations for fleet management
- Predictive maintenance alerts
- Geofencing capabilities
- Mobile SDK integration
- Voice assistant support

### Long-term Roadmap
- Unified vehicle abstraction layer
- Multi-manufacturer operations
- ML-based optimization
- Real-time telemetry streaming
- Partner API access

## Conclusion

The Skoda Connect API integration represents a critical business opportunity for DRAIV, enabling access to 30% of the Swiss rental market. By following the established patterns from our BMW implementation while adapting to Skoda's authentication model, we can deliver a secure, performant, and maintainable solution.

The use of the MySkoda library provides a solid foundation with proven reliability, while our layered architecture ensures flexibility for future enhancements. With comprehensive testing, security measures, and monitoring in place, we can confidently deploy this integration to production within 6 weeks.

This implementation will position DRAIV as the leading multi-manufacturer vehicle management platform in Switzerland, with a clear path to expanding to additional manufacturers using the same architectural patterns.

## Appendix

### A. MySkoda Library Documentation
- GitHub: https://github.com/skodaconnect/myskoda
- PyPI: https://pypi.org/project/myskoda/
- Home Assistant Integration: https://github.com/home-assistant/core/tree/dev/homeassistant/components/myskoda

### B. Reference Implementation
```python
from myskoda import MySkoda

async def example_usage():
    # Initialize client
    myskoda = MySkoda(username, password)
    await myskoda.connect()
    
    # Get vehicles
    vehicles = await myskoda.get_vehicles()
    
    # Lock vehicle (requires S-PIN)
    await myskoda.lock(vin, s_pin)
    
    # Get status
    status = await myskoda.get_status(vin)
    
    # Cleanup
    await myskoda.disconnect()
```

### C. Error Codes Mapping
| Skoda Error | DRAIV Error Code | HTTP Status |
|-------------|------------------|-------------|
| Invalid credentials | AUTH_FAILED | 401 |
| S-PIN required | SPIN_REQUIRED | 403 |
| Vehicle not found | VEHICLE_NOT_FOUND | 404 |
| Rate limited | RATE_LIMITED | 429 |
| API unavailable | SERVICE_UNAVAILABLE | 503 |

### D. Configuration Template
```yaml
# skoda-api-config.yaml
service:
  name: skoda-api
  version: 1.0.0
  
authentication:
  session_timeout: 1800
  max_sessions_per_user: 5
  
rate_limiting:
  enabled: true
  limits:
    status: 30/minute
    control: 10/minute
    
caching:
  provider: redis
  ttl:
    vehicle_list: 300
    vehicle_status: 60
    location: 30
    
monitoring:
  provider: prometheus
  port: 9090
  
logging:
  level: INFO
  format: json
  destination: stdout
```

---

**Document Version**: 1.0.0  
**Last Updated**: January 2025  
**Next Review**: February 2025  
**Approval Status**: READY FOR IMPLEMENTATION

**Related Documents**:
- PRP-002-UI.md - Frontend and Edge Function Implementation
- PRP-002-Skoda-Connect-API-Integration.md - Original comprehensive PRP

*This document focuses exclusively on the backend API implementation for the Skoda Connect integration. For frontend components, UI/UX flows, and edge function specifications, refer to PRP-002-UI.md.*