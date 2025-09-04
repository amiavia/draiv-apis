# Skoda Connect API Test Suite

Comprehensive test suite for the Skoda Connect API integration with 85%+ code coverage target.

## 📋 Overview

This test suite provides complete coverage for the Skoda Connect API integration, including:

- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: API endpoint and workflow testing  
- **End-to-End Tests**: Complete user journey scenarios
- **Performance Tests**: Response time and load testing
- **Security Tests**: Vulnerability scanning and validation

## 🚀 Quick Start

### Prerequisites

```bash
# Install test dependencies
make install

# Or manually:
pip install -r requirements-test.txt
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test categories
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-e2e          # End-to-end tests only

# Run with coverage
make test-coverage      # Generates HTML coverage report
```

### Test Credentials

Integration tests use these test credentials (mocked by default):
- **Email**: Info@miavia.ai
- **Password**: wozWi9-matvah-xonmyq
- **S-PIN**: 2405

## 📁 Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (85%+ coverage target)
│   ├── test_auth_manager.py      # Authentication & credentials
│   ├── test_vehicle_manager.py   # Vehicle data & status
│   ├── test_remote_services.py   # Remote commands & S-PIN
│   └── test_utils.py             # Circuit breakers & utilities
├── integration/             # Integration tests
│   ├── test_api_endpoints.py     # API endpoint testing
│   └── test_e2e_flow.py          # End-to-end scenarios
├── pytest.ini              # PyTest configuration
├── requirements-test.txt    # Test dependencies
└── Makefile                # Test automation commands
```

## 🧪 Test Categories

### Unit Tests (`tests/unit/`)

#### Authentication Manager (`test_auth_manager.py`)
- ✅ Credential encryption/decryption
- ✅ Session renewal and token refresh
- ✅ S-PIN validation and security
- ✅ MySkoda client integration
- ✅ Rate limiting and circuit breakers
- ✅ Concurrent authentication handling

#### Vehicle Manager (`test_vehicle_manager.py`)  
- ✅ Vehicle data parsing and normalization
- ✅ Status retrieval and caching
- ✅ Capability detection (gasoline vs electric)
- ✅ Battery and climate status handling
- ✅ Multi-vehicle management
- ✅ Error handling and validation

#### Remote Services (`test_remote_services.py`)
- ✅ Lock/unlock command execution
- ✅ Climate control operations
- ✅ Charging control (electric vehicles)
- ✅ S-PIN requirement enforcement
- ✅ Retry logic and timeout handling
- ✅ Command status tracking

#### Utilities (`test_utils.py`)
- ✅ Circuit breaker states and recovery
- ✅ Cache operations and TTL handling
- ✅ Rate limiting algorithms
- ✅ Retry strategies and backoff
- ✅ Data encryption/decryption
- ✅ Input validation (VIN, S-PIN)

### Integration Tests (`tests/integration/`)

#### API Endpoints (`test_api_endpoints.py`)
- ✅ Authentication endpoints (login, refresh, logout)
- ✅ Vehicle management endpoints
- ✅ Status retrieval endpoints  
- ✅ Remote command endpoints
- ✅ Error handling and validation
- ✅ Authorization and security

#### End-to-End Flow (`test_e2e_flow.py`)
- ✅ Complete user registration flow
- ✅ Multi-vehicle management scenarios
- ✅ Error recovery and fallback handling
- ✅ Concurrent user operations
- ✅ Session lifecycle management
- ✅ Performance monitoring
- ✅ Data consistency verification

## ⚡ Performance Testing

Performance tests verify response time requirements from PRP-002:

```bash
# Run performance tests
make test-performance

# Expected targets:
# - Status queries: <500ms p95
# - Remote commands: <5s  
# - Authentication: <2s
```

## 🔒 Security Testing

```bash
# Run security scans
make test-security

# Includes:
# - Bandit vulnerability scanning
# - Dependency security checks
# - S-PIN validation testing
# - Credential encryption verification
```

## 📊 Coverage Requirements

Target: **85%+ code coverage**

```bash
# Generate coverage report
make coverage-report

# Coverage is measured for:
# - src/ directory (implementation code)
# - Excludes tests/, __pycache__, etc.
```

## 🔧 Configuration

### PyTest Configuration (`pytest.ini`)
- Async test support
- Coverage reporting  
- Test markers and filtering
- Timeout settings (300s default)

### Test Dependencies (`requirements-test.txt`)
- Core: pytest, pytest-asyncio, pytest-cov
- HTTP: httpx, requests-mock, responses
- FastAPI: testclient integration
- Mocking: factory-boy, faker, freezegun  
- Performance: pytest-benchmark
- Security: bandit, safety

## 🎯 Test Markers

Use markers to run specific test categories:

```bash
# Run by marker
pytest -m "auth"         # Authentication tests
pytest -m "vehicle"      # Vehicle management tests  
pytest -m "remote"       # Remote command tests
pytest -m "utils"        # Utility tests
pytest -m "performance" # Performance tests
pytest -m "security"    # Security tests

# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m "integration"
```

## 🚀 CI/CD Integration

```bash
# Full CI pipeline
make ci                  # Lint + test + coverage + security

# Fast CI (for PRs)  
make ci-fast            # Unit tests only

# Docker testing
make test-docker        # Run tests in container
```

## 🛠️ Development Workflow

### Test-Driven Development (TDD)
1. Write failing test
2. Implement minimal code to pass
3. Refactor while keeping tests green
4. Verify coverage remains >85%

### Before Committing
```bash
make lint               # Code linting
make format             # Code formatting
make test-coverage      # Verify coverage target
make test-security      # Security checks
```

### Debugging Tests
```bash
make debug              # Run with full traceback
make watch              # Auto-run tests on file changes
pytest tests/ -s        # Show print statements
pytest tests/ --pdb     # Drop into debugger on failure
```

## 📈 Performance Benchmarks

Based on PRP-002 requirements:

| Operation | Target | Maximum | Test Status |
|-----------|--------|---------|-------------|
| Health check | <100ms | 200ms | ✅ Covered |
| Status query | <500ms p95 | 1s | ✅ Covered |  
| Remote command | <5s | 10s | ✅ Covered |
| Authentication | <2s | 5s | ✅ Covered |

## 🔍 Mock Data

### Test Vehicles
- **Gasoline**: VIN TMBJB41Z5N1234567 (Octavia)
- **Electric**: VIN TMBJB41Z5N1234568 (Enyaq iV)

### Mock Responses
All tests use realistic mock data matching MySkoda API structure:
- Vehicle lists and specifications
- Status responses (doors, fuel, battery, position)
- Command responses (success/failure scenarios)
- Error responses with proper error codes

## 🆘 Troubleshooting

### Common Issues

**Tests timing out:**
```bash
# Increase timeout
pytest tests/ --timeout=600
```

**Import errors:**
```bash
# Install in development mode
pip install -e .
```

**Coverage too low:**
```bash
# See uncovered lines
make test-coverage
open htmlcov/index.html
```

**Mock failures:**
```bash
# Reset mocks
make clean
make test
```

### Environment Variables

```bash
# Use real API (dangerous!)
export SKODA_USE_REAL_API=true

# Debug mode
export SKODA_DEBUG=true

# Custom timeout
export PYTEST_TIMEOUT=600
```

## 📚 Resources

- [PyTest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [MySkoda Library](https://github.com/skodaconnect/myskoda)
- [PRP-002 Requirements](../../../PRPs/PRP-002-Skoda-Connect-API-Integration.md)

## 🤝 Contributing

### Adding New Tests
1. Follow existing naming conventions
2. Add appropriate markers
3. Mock external dependencies  
4. Aim for >85% coverage
5. Document test purpose

### Test Guidelines
- **Unit tests**: Test single functions/classes
- **Integration tests**: Test API endpoints
- **E2E tests**: Test complete user flows
- **Performance tests**: Verify response times
- **Security tests**: Check vulnerabilities

---

**Test Coverage Target: 85%+**  
**Response Time Target: <500ms p95 for status queries**  
**Security: Zero tolerance for credential leaks**