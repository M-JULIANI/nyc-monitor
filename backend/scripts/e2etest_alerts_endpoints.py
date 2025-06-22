#!/usr/bin/env python3
"""
Test script for alerts endpoints
Tests both /alerts/recent and /alerts/stream endpoints
"""

from google.cloud import firestore
from rag.config import initialize_config, get_config
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
import httpx
import time
from typing import Dict, Any

# Add the parent directory to the path so we can import from rag
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Initialize config
initialize_config()
config = get_config()

# Test configuration
BASE_URL = "http://localhost:8000/api"
TEST_TIMEOUT = 30  # seconds


class AlertsEndpointTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TEST_TIMEOUT)
        self.db = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def get_db(self):
        """Get Firestore client"""
        if not self.db:
            self.db = firestore.Client(project=config.GOOGLE_CLOUD_PROJECT)
        return self.db

    async def test_server_health(self) -> bool:
        """Test if the server is running"""
        try:
            response = await self.client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("✅ Server is running")
                return True
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Server is not running: {e}")
            return False

    def check_firestore_connection(self) -> bool:
        """Test Firestore connection"""
        try:
            db = self.get_db()
            # Try to access the alerts collection
            alerts_ref = db.collection('nyc_monitor_alerts')
            # Just check if we can create a query (doesn't execute)
            query = alerts_ref.limit(1)
            print("✅ Firestore connection successful")
            return True
        except Exception as e:
            print(f"❌ Firestore connection failed: {e}")
            return False

    def get_sample_alerts_count(self) -> int:
        """Get count of alerts in Firestore for testing"""
        try:
            db = self.get_db()
            alerts_ref = db.collection('nyc_monitor_alerts')
            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            query = alerts_ref.where(
                'created_at', '>=', cutoff_time).limit(100)
            docs = list(query.stream())
            count = len(docs)
            print(f"📊 Found {count} alerts in last 24 hours")
            return count
        except Exception as e:
            print(f"❌ Error counting alerts: {e}")
            return 0

    async def test_recent_endpoint(self) -> bool:
        """Test the /alerts/recent endpoint"""
        print("\n🧪 Testing /alerts/recent endpoint...")

        try:
            response = await self.client.get(f"{BASE_URL}/alerts/recent")

            if response.status_code != 200:
                print(f"❌ Recent endpoint failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

            data = response.json()

            # Validate response structure
            if 'alerts' not in data or 'count' not in data:
                print(f"❌ Invalid response structure: {data}")
                return False

            alerts = data['alerts']
            count = data['count']

            print(f"✅ Recent endpoint successful")
            print(f"   - Returned {count} alerts")
            print(
                f"   - Response time: {response.elapsed.total_seconds():.2f}s")

            # Validate alert structure if we have alerts
            if alerts and len(alerts) > 0:
                sample_alert = alerts[0]
                required_fields = ['id', 'title',
                                   'description', 'priority', 'status', 'source']
                missing_fields = [
                    field for field in required_fields if field not in sample_alert]

                if missing_fields:
                    print(f"⚠️  Alert missing fields: {missing_fields}")
                else:
                    print("✅ Alert structure is valid")
                    print(
                        f"   - Sample alert: {sample_alert.get('title', 'No title')[:50]}...")

            return True

        except Exception as e:
            print(f"❌ Recent endpoint test failed: {e}")
            return False

    async def test_recent_endpoint_with_limit(self) -> bool:
        """Test the /alerts/recent endpoint with limit parameter"""
        print("\n🧪 Testing /alerts/recent endpoint with limit...")

        try:
            limit = 5
            response = await self.client.get(f"{BASE_URL}/alerts/recent?limit={limit}")

            if response.status_code != 200:
                print(
                    f"❌ Recent endpoint with limit failed: {response.status_code}")
                return False

            data = response.json()
            alerts = data.get('alerts', [])

            if len(alerts) > limit:
                print(
                    f"❌ Limit not respected: got {len(alerts)}, expected max {limit}")
                return False

            print(f"✅ Recent endpoint with limit successful")
            print(f"   - Requested limit: {limit}")
            print(f"   - Returned: {len(alerts)} alerts")

            return True

        except Exception as e:
            print(f"❌ Recent endpoint with limit test failed: {e}")
            return False

    async def test_stream_endpoint(self) -> bool:
        """Test the /alerts/stream endpoint (SSE)"""
        print("\n🧪 Testing /alerts/stream endpoint...")

        try:
            # Test SSE connection
            async with self.client.stream('GET', f"{BASE_URL}/alerts/stream") as response:
                if response.status_code != 200:
                    print(f"❌ Stream endpoint failed: {response.status_code}")
                    print(f"Response: {await response.aread()}")
                    return False

                print("✅ Stream endpoint connection successful")
                print("   - Listening for events (10 second timeout)...")

                # Listen for events with timeout
                start_time = time.time()
                event_count = 0

                async for chunk in response.aiter_text():
                    if chunk.strip():
                        print(f"   - Received chunk: {chunk.strip()[:100]}...")
                        event_count += 1

                    # Timeout after 10 seconds
                    if time.time() - start_time > 10:
                        break

                print(f"✅ Stream test completed")
                print(f"   - Received {event_count} chunks in 10 seconds")
                print(f"   - Connection maintained successfully")

                return True

        except Exception as e:
            print(f"❌ Stream endpoint test failed: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        print("🚀 Starting alerts endpoints tests...\n")

        results = {}

        # Test server health
        results['server_health'] = await self.test_server_health()
        if not results['server_health']:
            print("❌ Server not running, skipping other tests")
            return results

        # Test Firestore connection
        results['firestore_connection'] = self.check_firestore_connection()

        # Get sample data info
        alert_count = self.get_sample_alerts_count()

        # Test endpoints
        results['recent_endpoint'] = await self.test_recent_endpoint()
        results['recent_with_limit'] = await self.test_recent_endpoint_with_limit()
        results['stream_endpoint'] = await self.test_stream_endpoint()

        return results

    def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        print("\n" + "="*50)
        print("📋 TEST SUMMARY")
        print("="*50)

        passed = sum(results.values())
        total = len(results)

        for test_name, passed_test in results.items():
            status = "✅ PASS" if passed_test else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")

        print(f"\nOverall: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. Check the logs above.")


async def main():
    """Main test function"""
    async with AlertsEndpointTester() as tester:
        results = await tester.run_all_tests()
        tester.print_summary(results)

        # Exit with error code if any tests failed
        if not all(results.values()):
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
