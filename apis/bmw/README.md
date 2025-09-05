# BMW API - Stateless Implementation

Clean, stateless BMW Connected Drive API integration using bimmer_connected v0.17.3.

## Production Endpoint

```
https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless
```

## Features

- ✅ Completely stateless - no OAuth token storage
- ✅ Fresh authentication on every request
- ✅ hCaptcha integration for quota management
- ✅ Support for all BMW Connected Drive operations
- ✅ Clean single-file implementation

## Quick Start

### Test Health Endpoint
```bash
curl https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless/health
```

### Lock Vehicle
```bash
curl -X POST "https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password",
    "wkn": "your-vehicle-wkn",
    "hcaptcha": "hcaptcha-token",
    "action": "lock"
  }'
```

## Deployment

Deploy to Google Cloud Functions using the provided script:

```bash
./deploy_stateless.sh
```

For production deployment:
```bash
./deploy_stateless.sh --production
```

## Project Structure

```
apis/bmw/
├── src/
│   ├── main_stateless.py      # Main implementation
│   └── __init__.py
├── deploy_stateless.sh         # Deployment script
├── requirements-stateless.txt  # Dependencies
├── README_STATELESS.md         # Detailed documentation
├── .env.example               # Environment template
└── archive/                   # Legacy implementations (archived)
```

## Documentation

- [README_STATELESS.md](README_STATELESS.md) - Detailed stateless implementation guide
- [archive/ARCHIVE_INDEX.md](archive/ARCHIVE_INDEX.md) - Index of archived legacy code

## Requirements

- Python 3.11+
- bimmer_connected==0.17.3
- Google Cloud Functions (Gen 2)
- Valid BMW ConnectedDrive credentials

## Support

This is a production-ready, stateless implementation optimized for scalability and security.