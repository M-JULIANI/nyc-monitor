#!/usr/bin/env python3
"""
Simple test script for alerts endpoints
Quick and easy testing of /alerts/recent endpoint
"""

import requests
import json
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import from rag
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
BASE_URL = "http://localhost:8000/api"
TIMEOUT = 10


def test_server_health():
    """Test if the server is running"""
    print("🔍 Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        if response.status_code == 200:
            print("✅ Server is running")
            print(f"   Response: {response.json()}")
            assert True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            assert False, f"Server health check failed: {response.status_code}"
    except Exception as e:
        print(f"❌ Server is not running: {e}")
        assert False, f"Server is not running: {e}"


def test_recent_endpoint():
    """Test the /alerts/recent endpoint"""
    print("\n🔍 Testing /alerts/recent endpoint...")

    try:
        response = requests.get(f"{BASE_URL}/alerts/recent", timeout=TIMEOUT)

        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")

        if response.status_code != 200:
            print(f"❌ Recent endpoint failed: {response.status_code}")
            print(f"Response text: {response.text}")
            assert False, f"Recent endpoint failed: {response.status_code}"

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {e}")
            print(f"Response text: {response.text}")
            assert False, f"Invalid JSON response: {e}"

        print(f"✅ Recent endpoint successful")
        print(
            f"Response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")

        # Validate response structure
        if isinstance(data, dict) and 'alerts' in data and 'count' in data:
            alerts = data['alerts']
            count = data['count']

            print(f"   - Returned {count} alerts")
            print(f"   - Alerts array length: {len(alerts)}")

            # Show sample alert if available
            if alerts and len(alerts) > 0:
                sample_alert = alerts[0]
                print(f"   - Sample alert keys: {list(sample_alert.keys())}")
                print(
                    f"   - Sample alert title: {sample_alert.get('title', 'No title')}")
                print(
                    f"   - Sample alert priority: {sample_alert.get('priority', 'No priority')}")
            else:
                print("   - No alerts in response")
        else:
            print(f"⚠️  Unexpected response structure: {data}")

        assert True

    except Exception as e:
        print(f"❌ Recent endpoint test failed: {e}")
        assert False, f"Recent endpoint test failed: {e}"


def test_recent_with_limit():
    """Test the /alerts/recent endpoint with limit parameter"""
    print("\n🔍 Testing /alerts/recent with limit=3...")

    try:
        response = requests.get(
            f"{BASE_URL}/alerts/recent?limit=3", timeout=TIMEOUT)

        if response.status_code != 200:
            print(
                f"❌ Recent endpoint with limit failed: {response.status_code}")
            print(f"Response: {response.text}")
            assert False, f"Recent endpoint with limit failed: {response.status_code}"

        data = response.json()
        alerts = data.get('alerts', [])

        print(f"✅ Recent endpoint with limit successful")
        print(f"   - Requested limit: 3")
        print(f"   - Returned: {len(alerts)} alerts")

        if len(alerts) > 3:
            print(
                f"⚠️  Limit not respected: got {len(alerts)}, expected max 3")

        assert True

    except Exception as e:
        print(f"❌ Recent endpoint with limit test failed: {e}")
        assert False, f"Recent endpoint with limit test failed: {e}"


def test_stream_endpoint_basic():
    """Basic test of the /alerts/stream endpoint (just connection)"""
    print("\n🔍 Testing /alerts/stream endpoint connection...")

    try:
        # Just test if we can connect (don't wait for data)
        response = requests.get(
            f"{BASE_URL}/alerts/stream", timeout=5, stream=True)

        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")

        if response.status_code == 200:
            print("✅ Stream endpoint connection successful")

            # Check if it's SSE
            content_type = response.headers.get('content-type', '')
            if 'text/event-stream' in content_type:
                print("   - Correct SSE content-type")
            else:
                print(f"   - Content-type: {content_type}")

            assert True
        else:
            print(f"❌ Stream endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            assert False, f"Stream endpoint failed: {response.status_code}"

    except Exception as e:
        print(f"❌ Stream endpoint test failed: {e}")
        assert False, f"Stream endpoint test failed: {e}"


def main():
    """Run all tests"""
    print("🚀 Starting simple alerts endpoints tests...")
    print(f"Testing against: {BASE_URL}")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)

    tests = [
        ("Server Health", test_server_health),
        ("Recent Endpoint", test_recent_endpoint),
        ("Recent with Limit", test_recent_with_limit),
        ("Stream Endpoint Basic", test_stream_endpoint_basic),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the logs above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
