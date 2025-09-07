# Viewport Performance Testing

This directory contains comprehensive performance testing for the new `/alerts/viewport` endpoint that implements the enhanced alert serving strategy with NYC-optimized spatial caching.

## Test Script: `test_viewport_performance.py`

A Python script that tests the viewport endpoint performance, cache efficiency, and load handling capabilities. The script is located within the backend project structure to utilize the proper dependencies from `pyproject.toml`.

### Features

- **Performance Scenarios**: Tests various viewport sizes and date ranges
- **Cache Pattern Analysis**: Validates spatial grid caching behavior  
- **Load Testing**: Simulates 3 concurrent users for 15 seconds (lightweight testing)
- **Comprehensive Reporting**: Generates detailed results in timestamped files (`perf-test-api-YYYYMMDD-HHMMSS.txt`)
- **Automatic File Management**: Saves all output files in the `backend/performance/` directory

### Usage

**From the backend directory (recommended):**
```bash
cd backend

# ⚠️  IMPORTANT: Use --perf-test for local development (bypasses auth)
poetry run python performance/test_viewport_performance.py --perf-test

# For production testing with authentication
poetry run python performance/test_viewport_performance.py --auth-token your_token

# With custom base URL
poetry run python performance/test_viewport_performance.py --base-url http://your-api-host:8000

# With authentication token (for production testing)
poetry run python performance/test_viewport_performance.py --auth-token your_oauth_token

# Custom output file
poetry run python performance/test_viewport_performance.py --output-file my-test-results.txt

# Local development testing (most common)
poetry run python performance/test_viewport_performance.py \
  --perf-test \
  --base-url http://localhost:8000 \
  --output-file local-dev-test.txt

# Production testing with auth
poetry run python performance/test_viewport_performance.py \
  --base-url http://api.example.com \
  --auth-token abc123 \
  --output-file production-perf-test.txt
```

**From the performance directory:**
```bash
cd backend/performance

# Using poetry (run from parent directory)
cd .. && poetry run python performance/test_viewport_performance.py --perf-test
```

### Dependencies

The script uses the project dependencies from `pyproject.toml`. Ensure dependencies are installed:

```bash
cd backend

# Install dependencies with poetry
poetry install
```

Key dependencies used:
- `aiohttp` - Async HTTP client for API requests
- `asyncio` - Async/await support
- Built-in libraries: `json`, `statistics`, `time`, `argparse`

### Test Scenarios

The script tests the exact scenarios outlined in the strategy document:

1. **Performance Comparison**:
   - Legacy `/alerts/recent` endpoint (baseline)
   - New `/alerts/viewport` with 7 days, 30 days, and 6 months of data
   - Different zoom levels (street, neighborhood, borough, city)
   - Metro area handling (outside NYC bounds)

2. **Cache Pattern Analysis**:
   - Overlapping viewports
   - Zoom level transitions
   - Grid snapping validation

3. **Load Testing**:
   - 10 concurrent users for 30 seconds
   - Mixed viewport scenarios
   - Error rate and performance under load

### Success Criteria

The test evaluates against these targets:

- **Cache Hit Rate**: >75% after warming
- **Response Times**: 
  - Cache hits: <100ms
  - Cache misses: <600ms
- **Load Testing**: <5% error rate
- **Historical Data**: 6+ months with acceptable performance

### Output

Results are saved to `perf-test-api.txt` (or custom file) containing:

- Performance metrics for each test scenario
- Cache hit/miss analysis
- Load testing statistics  
- Success criteria evaluation
- Complete raw data in JSON format

### Example Output Snippet

```
PERFORMANCE SCENARIOS SUMMARY
----------------------------------------

VIEWPORT_7_DAYS:
  Description: New caching system - 1 week Manhattan
  Cold Cache Avg: 450ms
  Warm Cache Avg: 85ms
  Cache Hit Rate: 87%
  Performance Improvement: 81%
  Sample Alert Count: 1247

CACHE PATTERNS ANALYSIS
----------------------------------------

viewport_a:
  First Request: Cache Hit = False, Time = 380ms
  Second Request: Cache Hit = True, Time = 12ms
  Cache Key Type: street
```

## Running Tests Against Local Development

1. Start the backend server:
```bash
cd backend
make run
```

2. In another terminal, run the performance tests:
```bash
cd backend
poetry run python performance/test_viewport_performance.py --perf-test
```

3. Check results:
```bash
# Results are automatically saved with timestamp
ls -la *.txt
cat perf-test-api-*.txt
```

## Quick Start

**⚠️ CRITICAL**: The backend server must be started with `PERF_TEST=true` for authentication bypass to work!

```bash
# Terminal 1: Start backend with performance testing mode
cd backend
PERF_TEST=true make run
# ☝️ This sets the environment variable for the SERVER

# Terminal 2: Run performance tests
cd backend
poetry run python performance/test_viewport_performance.py --perf-test
# ☝️ This just tells the script that you intend to test without auth

# Check results (automatically saved with timestamp)
ls -la performance/perf-test-api-*.txt
cat performance/perf-test-api-*.txt | head -50
```

### Output File Management

- **Automatic Timestamping**: Files are saved as `perf-test-api-YYYYMMDD-HHMMSS.txt`
- **Location**: All files saved in `backend/performance/` directory
- **Custom Names**: Use `--output-file custom-name.txt` to override default naming
- **History**: Previous test results are preserved automatically

## Troubleshooting

### 🚨 "No session" or 401 Errors

If you see authentication errors even with `--perf-test`:

```bash
❌ Cold run 1 failed: {"detail":"No session"}
```

**Problem**: The backend server wasn't started with `PERF_TEST=true`.

**Solution**: 
1. Stop the current backend server (Ctrl+C)
2. Restart with the environment variable:
   ```bash
   cd backend
   PERF_TEST=true make run
   ```
3. Run the test again:
   ```bash
   poetry run python performance/test_viewport_performance.py --perf-test
   ```

### ✅ Successful Test Output

When working correctly, you should see:
```bash
🚀 Performance testing mode enabled - authentication bypassed
✅ Cold run 1 completed: 245ms
✅ Cache hit rate: 85%
```

## Integration with CI/CD

The script can be integrated into automated testing pipelines:

```bash
# Exit with error code if tests fail
python test_viewport_performance.py --base-url $API_URL --auth-token $AUTH_TOKEN

# Check specific success criteria
if grep -q "Cache Hit Rate Status: ✅ PASS" perf-test-api.txt; then
  echo "Performance tests passed!"
else
  echo "Performance tests failed!"
  exit 1
fi
```
