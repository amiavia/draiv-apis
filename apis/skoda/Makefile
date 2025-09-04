# Makefile for Skoda Connect API Testing

.PHONY: help install test test-unit test-integration test-e2e test-coverage test-performance clean lint format security

# Default target
help:
	@echo "Skoda Connect API Test Suite"
	@echo "================================"
	@echo "Available targets:"
	@echo "  install           Install test dependencies"
	@echo "  test              Run all tests"
	@echo "  test-unit         Run unit tests only"
	@echo "  test-integration  Run integration tests only"
	@echo "  test-e2e          Run end-to-end tests only"
	@echo "  test-coverage     Run tests with detailed coverage"
	@echo "  test-performance  Run performance tests"
	@echo "  test-security     Run security tests"
	@echo "  lint              Run code linting"
	@echo "  format            Format code"
	@echo "  clean             Clean test artifacts"
	@echo "  ci                Run CI pipeline tests"

# Installation
install:
	@echo "Installing test dependencies..."
	pip install -r requirements-test.txt
	pip install -r ../../../shared/requirements.txt

# Test execution
test: test-unit test-integration test-e2e
	@echo "All tests completed"

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v -m "unit" --tb=short

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v -m "integration" --tb=short

test-e2e:
	@echo "Running end-to-end tests..."
	pytest tests/integration/test_e2e_flow.py -v -m "e2e" --tb=short

test-coverage:
	@echo "Running tests with coverage analysis..."
	pytest tests/ -v \
		--cov=src \
		--cov-report=html:htmlcov \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-fail-under=85

test-performance:
	@echo "Running performance tests..."
	pytest tests/ -v -m "performance" \
		--benchmark-only \
		--benchmark-sort=mean \
		--benchmark-columns=min,max,mean,stddev,median,iqr,outliers,rounds,iterations

test-security:
	@echo "Running security tests..."
	bandit -r src/ -f json -o security-report.json || true
	safety check --json --output security-deps.json || true
	@echo "Security scan completed"

# Code quality
lint:
	@echo "Running code linting..."
	flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	mypy src/ --ignore-missing-imports

format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/ --profile black

# Test categories
test-auth:
	@echo "Running authentication tests..."
	pytest tests/ -v -m "auth"

test-vehicle:
	@echo "Running vehicle management tests..."
	pytest tests/ -v -m "vehicle"

test-remote:
	@echo "Running remote command tests..."
	pytest tests/ -v -m "remote"

test-utils:
	@echo "Running utility tests..."
	pytest tests/ -v -m "utils"

# Parallel testing
test-parallel:
	@echo "Running tests in parallel..."
	pytest tests/ -v -n auto --dist=worksteal

# Specific test environments
test-with-real-credentials:
	@echo "Running tests with real Skoda Connect credentials..."
	@echo "WARNING: This will make actual API calls!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	SKODA_USE_REAL_API=true pytest tests/integration/ -v -m "integration" --tb=short

test-docker:
	@echo "Running tests in Docker environment..."
	docker build -t skoda-api-test -f Dockerfile.test .
	docker run --rm skoda-api-test

# CI/CD Pipeline
ci: install lint test-coverage test-security
	@echo "CI pipeline completed"

ci-fast: install test-unit
	@echo "Fast CI pipeline completed"

# Coverage reporting
coverage-report:
	@echo "Generating coverage report..."
	coverage html --directory=htmlcov
	coverage xml -o coverage.xml
	coverage-badge -o coverage.svg
	@echo "Coverage report generated in htmlcov/"

# Load testing
load-test:
	@echo "Running load tests..."
	pytest tests/ -v -m "performance" --benchmark-warmup=on --benchmark-disable-gc

# Regression testing
test-regression:
	@echo "Running regression tests..."
	pytest tests/ -v -m "regression"

# Test with different Python versions (requires pyenv)
test-py38:
	pyenv local 3.8
	pytest tests/ -v

test-py39:
	pyenv local 3.9
	pytest tests/ -v

test-py310:
	pyenv local 3.10
	pytest tests/ -v

test-py311:
	pyenv local 3.11
	pytest tests/ -v

# Database testing
test-db:
	@echo "Running database tests..."
	pytest tests/ -v -m "database"

# Mock server testing
test-mock-server:
	@echo "Starting mock server for testing..."
	wiremock --port 8089 --root-dir tests/mocks/ &
	pytest tests/integration/ -v --mock-server-port=8089
	pkill -f wiremock

# Cleanup
clean:
	@echo "Cleaning test artifacts..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf coverage.svg
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf tests/__pycache__/
	rm -rf tests/*/__pycache__/
	rm -rf src/__pycache__/
	rm -rf src/*/__pycache__/
	rm -rf security-report.json
	rm -rf security-deps.json
	rm -rf .mypy_cache/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

clean-all: clean
	@echo "Deep cleaning..."
	rm -rf venv/
	rm -rf .venv/
	rm -rf node_modules/

# Development helpers
watch:
	@echo "Watching for changes and running tests..."
	pytest-watch tests/ -- -v

debug:
	@echo "Running tests in debug mode..."
	pytest tests/ -v --tb=long --capture=no -s

profile:
	@echo "Profiling test execution..."
	pytest tests/ -v --profile

# Test data management
test-data-setup:
	@echo "Setting up test data..."
	python scripts/setup_test_data.py

test-data-cleanup:
	@echo "Cleaning up test data..."
	python scripts/cleanup_test_data.py

# Documentation
test-docs:
	@echo "Testing documentation examples..."
	python -m doctest README.md
	python -m doctest docs/*.md

# Environment validation
validate-env:
	@echo "Validating test environment..."
	python -c "import pytest, asyncio, httpx, fastapi; print('Environment OK')"

# Quick smoke test
smoke-test:
	@echo "Running smoke tests..."
	pytest tests/ -v -k "test_health" --tb=short

# Memory profiling
memory-profile:
	@echo "Running memory profile tests..."
	pytest tests/ -v --memprof

# Test with specific markers
test-slow:
	@echo "Running slow tests..."
	pytest tests/ -v -m "slow"

test-quick:
	@echo "Running quick tests only..."
	pytest tests/ -v -m "not slow"

# Generate test report
report:
	@echo "Generating test report..."
	pytest tests/ -v --html=report.html --self-contained-html

# Verify test structure
verify-structure:
	@echo "Verifying test structure..."
	@test -d tests/unit || echo "Missing tests/unit directory"
	@test -d tests/integration || echo "Missing tests/integration directory"
	@test -f tests/conftest.py || echo "Missing tests/conftest.py"
	@test -f pytest.ini || echo "Missing pytest.ini"
	@echo "Test structure verification completed"