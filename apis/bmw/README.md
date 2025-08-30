# BMW Connected Drive API

> **Production-ready integration with BMW's Connected Drive platform**

## 📋 Overview

This API provides comprehensive integration with BMW Connected Drive, enabling remote vehicle control, status monitoring, and data retrieval for BMW vehicles.

## 🚀 Features

### Remote Control
- **Lock/Unlock**: Secure remote door control
- **Climate Control**: Pre-condition vehicle temperature
- **Light Flash**: Locate vehicle in parking lots
- **Horn Honk**: Audio vehicle location

### Vehicle Information
- **Location**: GPS coordinates and address
- **Fuel Status**: Level, range, and consumption
- **Mileage**: Total distance traveled
- **Check Control**: Warning messages and alerts
- **Door/Window Status**: Open/closed states

## 🔧 Setup

### Prerequisites
- BMW Connected Drive account
- Vehicle with ConnectedDrive services enabled
- Google Cloud Storage bucket for OAuth tokens

### Environment Variables

Create a `.env` file:
```env
# BMW API Configuration
BMW_OAUTH_BUCKET=bmw-api-bucket
GCP_PROJECT=your-project-id
ENVIRONMENT=development

# Optional
LOG_LEVEL=INFO
CACHE_TTL=300
CIRCUIT_BREAKER_THRESHOLD=5
```

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python src/main.py
```

## 📚 API Reference

### Authentication

All requests require BMW account credentials:
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "wkn": "VEHICLE_WKN",
  "hcaptcha": "token"  // Required for first-time auth
}
```

### Endpoints

#### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "bmw-api",
  "version": "2.0.0",
  "metrics": {...}
}
```

#### Vehicle Status
```http
POST /bmw_api
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password",
  "wkn": "WKN123",
  "action": "status"
}
```

#### Lock Vehicle
```http
POST /bmw_api
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password",
  "wkn": "WKN123",
  "action": "lock"
}
```

#### Get Location
```http
POST /bmw_api
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password",
  "wkn": "WKN123",
  "action": "location"
}
```

Response:
```json
{
  "success": true,
  "vehicle_name": "BMW 330i",
  "result": {
    "latitude": 47.3769,
    "longitude": 8.5417,
    "address": "Zurich, Switzerland",
    "google_maps_url": "https://maps.google.com/..."
  }
}
```

### Available Actions

| Action | Description | Response Time |
|--------|-------------|---------------|
| `status` | Full vehicle status | <1s |
| `lock` | Lock doors | <90s |
| `unlock` | Unlock doors | <90s |
| `flash` | Flash lights | <30s |
| `ac` | Activate climate | <120s |
| `fuel` | Fuel level & range | <1s |
| `location` | GPS location | <1s |
| `mileage` | Odometer reading | <1s |
| `lock_status` | Door lock state | <1s |
| `is_locked` | Simple lock check | <1s |
| `check_control` | Warning messages | <1s |

## 🧪 Testing

### Run Tests
```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=src --cov-report=html
```

### Test Structure
```
tests/
├── unit/
│   ├── test_auth_manager.py
│   ├── test_vehicle_manager.py
│   ├── test_remote_services.py
│   └── test_utils/
├── integration/
│   ├── test_bmw_api.py
│   └── test_end_to_end.py
└── fixtures/
    └── mock_responses.json
```

## 🐳 Docker Development

### Build Image
```bash
docker build -t bmw-api .
```

### Run Container
```bash
docker run -p 8080:8080 \
  -e BMW_OAUTH_BUCKET=test-bucket \
  -e ENVIRONMENT=development \
  bmw-api
```

### Docker Compose
```yaml
version: '3.8'
services:
  bmw-api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - BMW_OAUTH_BUCKET=test-bucket
      - ENVIRONMENT=development
    volumes:
      - ./src:/app/src
```

## 🚀 Deployment

### Google Cloud Functions

#### Using gcloud CLI
```bash
gcloud functions deploy bmw_api \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point bmw_api \
  --source src/ \
  --set-env-vars BMW_OAUTH_BUCKET=bmw-api-bucket \
  --memory 256MB \
  --timeout 540s
```

#### Using GitHub Actions
Push to `main` branch triggers automatic deployment.

## 📊 Monitoring

### Metrics
- Request count
- Success/failure rates
- Average response time
- Circuit breaker state
- Cache hit ratio

### Logging
Structured JSON logs include:
- Request ID
- User ID
- Action performed
- Duration
- Success/failure status

### Alerts
- Circuit breaker open
- High error rate (>5%)
- Response time >5s
- Authentication failures

## 🔒 Security

### Best Practices
- OAuth tokens stored encrypted in GCS
- No passwords in logs
- Input validation on all fields
- Rate limiting per user
- Automatic token rotation

### hCaptcha Integration
First-time authentication requires hCaptcha token:
```javascript
// Frontend implementation
const token = await hcaptcha.execute(siteKey, { async: true });
```

## 🐛 Troubleshooting

### Common Issues

#### Authentication Failed
```json
{
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid credentials"
  }
}
```
**Solution**: Verify email/password, check if account has 2FA enabled.

#### Circuit Breaker Open
```json
{
  "error": {
    "code": "CIRCUIT_BREAKER_OPEN",
    "message": "Service temporarily unavailable"
  }
}
```
**Solution**: Wait 60 seconds for automatic recovery.

#### Rate Limit Exceeded
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests"
  }
}
```
**Solution**: Implement exponential backoff on client.

## 📈 Performance

### Benchmarks
- Health check: <50ms
- Status query: <200ms (cached)
- Remote command: <5s average
- Concurrent requests: 100+

### Optimization Tips
- Enable caching for read operations
- Use batch requests when possible
- Implement client-side retries
- Monitor circuit breaker state

## 🔄 Changelog

### v2.0.0 (2025-01-30)
- Complete refactor with modular architecture
- Added circuit breaker pattern
- Implemented caching layer
- Enhanced error handling
- Structured logging
- Performance improvements

### v1.0.0 (2025-01-01)
- Initial release
- Basic BMW API integration

## 📚 References

- [BMW Connected Drive Documentation](https://github.com/bimmerconnected/bimmer_connected)
- [Google Cloud Functions](https://cloud.google.com/functions/docs)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)

---

**Maintained by DRAIV Engineering Team**