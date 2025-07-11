# Backend Test Suite

This directory contains comprehensive unit tests for the RAG backend service, designed to provide protection against regressions and ensure system reliability.

## Test Structure

### Core Test Files

- **`test_config.py`** - Configuration management tests
  - Environment variable loading and validation
  - Global configuration initialization
  - Production vs development behavior

- **`test_auth.py`** - Authentication and security tests
  - Google OAuth token verification
  - Error handling for invalid tokens
  - Security edge cases and logging

- **`test_endpoints_chat.py`** - Chat endpoint tests
  - Chat functionality and session management
  - History retrieval and session clearing
  - Error handling and validation

- **`test_endpoints_investigation.py`** - Investigation endpoint tests
  - Investigation workflow (both simple and ADK approaches)
  - Progress tracking and streaming
  - Configuration and tracing endpoints

- **`test_main.py`** - Main application tests
  - Health checks and app metadata
  - CORS and middleware configuration
  - Rate limiting and security headers

### Test Fixtures & Configuration

- **`conftest.py`** - Shared test fixtures and configuration
- **`pytest.ini`** - Pytest settings and test discovery
- **`requirements-test.txt`** - Testing dependencies

## Running Tests

### Prerequisites

Install testing dependencies:
```bash
pip install -r requirements-test.txt
```

### Running All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_config.py

# Run specific test class
pytest tests/test_auth.py::TestGoogleTokenVerification

# Run specific test
pytest tests/test_main.py::TestHealthEndpoints::test_health_check_endpoint
```

### Running Tests by Markers

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only API tests
pytest -m api

# Skip slow tests
pytest -m "not slow"
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=rag --cov-report=html

# View coverage in terminal
pytest --cov=rag --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov-fail-under=80
```

## Test Coverage Areas

### 🔧 Configuration Management
- Environment variable loading (development vs production)
- Configuration validation and error handling
- Global config initialization and access

### 🔐 Authentication & Security
- Google OAuth token verification
- Invalid token handling
- Security headers and CORS configuration
- Rate limiting functionality

### 💬 Chat Functionality
- Chat message processing and response generation
- Session management and conversation history
- Error handling for missing RAG corpus
- Session clearing and retrieval

### 🔍 Investigation System
- Both simple and ADK investigation approaches
- Progress tracking and real-time streaming
- State management and artifact handling
- Configuration and tracing endpoints

### 🌐 API & Infrastructure
- Health checks and service status
- FastAPI app configuration and metadata
- Middleware stack (CORS, rate limiting)
- HTTP exception handling

## Test Patterns & Best Practices

### Mocking Strategy
- **External Services**: All external API calls (Google Auth, Vertex AI) are mocked
- **Configuration**: Environment variables mocked for isolated testing
- **Database/State**: In-memory state management mocked to avoid side effects

### Error Testing
- **Authentication Failures**: Invalid tokens, missing client IDs
- **Service Failures**: Network errors, invalid configurations
- **Validation Errors**: Malformed requests, missing required fields

### Security Testing
- **Authorization**: Unauthenticated access attempts
- **Input Validation**: Edge cases and malformed data
- **Information Disclosure**: Server headers and error messages

## Continuous Integration

These tests are designed to run in CI/CD pipelines with:
- **Fast Execution**: Most tests complete in under 10 seconds
- **No External Dependencies**: All external services mocked
- **Deterministic Results**: No flaky tests or race conditions
- **Clear Failure Messages**: Detailed assertions and error reporting

## Extending the Test Suite

When adding new functionality:

1. **Add corresponding tests** in the appropriate test file
2. **Mock external dependencies** to keep tests isolated
3. **Test both success and failure scenarios**
4. **Include validation and security edge cases**
5. **Update this README** if adding new test categories

## Troubleshooting

### Common Issues

**Import Errors**: Ensure the `backend` directory is in your Python path
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"
```

**Async Test Issues**: Make sure pytest-asyncio is installed and `asyncio_mode = auto` is set in pytest.ini

**Mock Conflicts**: Tests may fail if modules are imported before mocking. Use `importlib.reload()` when needed.

### Test Environment

Tests run with:
- `ENV=test` environment variable
- Mocked Google Client ID and other credentials
- In-memory state management
- Disabled external network calls 