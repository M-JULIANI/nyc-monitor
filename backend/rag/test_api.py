#!/usr/bin/env python3
"""
Test script for the Atlas Investigation API endpoint.
This script tests the investigation via the /investigate endpoint.
"""

import asyncio
import json
import aiohttp
import pytest
from datetime import datetime


@pytest.mark.asyncio
async def test_investigation_api():
    """Test the investigation system via API."""

    print("🌐 Testing Atlas Investigation API")
    print("=" * 40)

    # Test alert data
    test_alert = {
        "alert_id": "API-TEST-2024-001",
        "event_type": "Infrastructure Issue",
        "location": "Brooklyn Bridge, Manhattan",
        "severity": 6,
        "summary": "Reports of unusual structural sounds and minor debris falling from Brooklyn Bridge. Multiple witnesses posting on social media. NYCDOT investigating.",
        "sources": ["Twitter", "Reddit", "311", "News"],
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "bridge_section": "pedestrian_walkway",
            "weather_conditions": "clear",
            "traffic_impact": "minimal"
        }
    }

    print(f"📋 Test Alert:")
    print(f"   ID: {test_alert['alert_id']}")
    print(f"   Type: {test_alert['event_type']}")
    print(f"   Location: {test_alert['location']}")
    print(f"   Severity: {test_alert['severity']}/10")
    print()

    try:
        # Test the API endpoint
        async with aiohttp.ClientSession() as session:
            print("🔗 Sending request to /investigate endpoint...")

            # Adjust URL based on your setup
            url = "http://localhost:8000/api/investigate/"

            # Add investigation method parameter
            params = {"method": "adk"}  # or "simple" for testing

            async with session.post(url, json=test_alert, params=params) as response:
                status = response.status
                result = await response.json()

                print(f"📊 API Response:")
                print(f"   Status: {status}")

                if status == 200:
                    print(f"   ✅ Investigation successful!")
                    print(
                        f"   Investigation ID: {result.get('investigation_id', 'N/A')}")
                    print(f"   Method: {result.get('method', 'N/A')}")
                    print(
                        f"   Result length: {len(str(result.get('result', '')))}")
                    print()

                    print("📄 Investigation Result:")
                    print("-" * 30)
                    print(result.get('result', 'No result'))
                    print("-" * 30)
                    print()

                    return True
                else:
                    print(f"   ❌ API Error: {result}")
                    return False

    except aiohttp.ClientError as e:
        print(f"❌ Connection Error: {e}")
        print("💡 Make sure the API server is running:")
        print("   cd backend && python -m rag.main")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test the health endpoint to ensure API is running."""

    print("🏥 Testing Health Endpoint")
    print("-" * 25)

    try:
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:8000/api/health"

            async with session.get(url) as response:
                status = response.status
                result = await response.json()

                if status == 200:
                    print(f"✅ Health check passed: {result}")
                    return True
                else:
                    print(f"❌ Health check failed: {status} - {result}")
                    return False

    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


async def main():
    """Main test function."""

    print("🔌 Atlas Investigation System - API Test")
    print("=" * 45)
    print()

    # Test health endpoint first
    health_ok = await test_health_endpoint()
    print()

    if health_ok:
        # Test investigation endpoint
        api_ok = await test_investigation_api()

        print("📊 API Test Summary:")
        print(f"   Health: {'✅ PASS' if health_ok else '❌ FAIL'}")
        print(f"   Investigation: {'✅ PASS' if api_ok else '❌ FAIL'}")
        print()

        if api_ok:
            print("🎉 API TEST PASSED! Investigation system working via API.")
            return 0
        else:
            print("🚨 API TEST FAILED! Check server logs.")
            return 1
    else:
        print("🚨 API SERVER NOT RUNNING!")
        print("💡 Start the server with: cd backend && python -m rag.main")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
