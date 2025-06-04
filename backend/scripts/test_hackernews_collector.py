#!/usr/bin/env python3
"""
Test script for HackerNews collector
Verifies that the collector can fetch and filter NYC-relevant stories
"""
import logging
from monitor.collectors.hackernews_collector import HackerNewsCollector
import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_hackernews_collector():
    """Test the HackerNews collector"""
    print("🔍 Testing HackerNews Collector...")
    print(f"   Timestamp: {datetime.utcnow().isoformat()}")
    print()

    try:
        # Initialize collector
        print("📡 Initializing HackerNews collector...")
        collector = HackerNewsCollector()
        print(f"✅ HackerNews collector initialized")
        print(f"   Priority keywords: {len(collector.priority_keywords)}")
        print(
            f"   Location extractor: {collector.location_extractor.get_location_count()} locations")
        print(f"   Time window: {collector.time_window_hours} hours")
        print(f"   Max stories to check: {collector.max_stories_to_check}")
        print()

        # Test signal collection
        print("🔍 Collecting signals from HackerNews...")
        signals = await collector.collect_signals()
        print(f"✅ Collected {len(signals)} relevant signals")
        print()

        if not signals:
            print(
                "ℹ️  No relevant signals found (this is normal if no recent relevant stories)")
            print(
                "🔍 HackerNews may not have relevant stories in the current time window")
            return True

        # Print story titles
        print("📰 Story Titles Found:")
        for i, signal in enumerate(signals, 1):
            print(f"   [{i}] {signal['title']}")
            print(
                f"       Score: {signal.get('score', 0)} | Comments: {signal.get('comments', 0)}")
            print(f"       URL: {signal.get('url', 'N/A')}")
            print()

        # Analyze collected signals
        print("📊 Signal Analysis:")
        priority_count = sum(1 for s in signals if s['metadata'].get(
            'has_priority_content', False))
        located_count = sum(
            1 for s in signals if s['metadata'].get('has_coordinates', False))

        print(f"   Total signals: {len(signals)}")
        print(f"   Priority signals: {priority_count}")
        print(f"   Signals with coordinates: {located_count}")
        print()

        # Show sample signals
        print("📝 Sample Signals:")
        for i, signal in enumerate(signals[:3]):  # Show first 3
            metadata = signal['metadata']
            print(f"   [{i+1}] {signal['title'][:80]}...")
            print(f"       Score: {signal.get('score', 0)}")
            print(f"       Source: {signal['source']}")
            print(
                f"       Priority: {metadata.get('has_priority_content', False)}")
            print(f"       Keywords: {metadata.get('priority_keywords', [])}")
            print(f"       Locations: {metadata.get('locations', [])}")
            if metadata.get('has_coordinates'):
                print(
                    f"       Coordinates: ({metadata.get('latitude')}, {metadata.get('longitude')})")
            print(f"       URL: {signal.get('url', 'N/A')}")
            print()

        # Verify signal structure
        print("🔍 Signal Structure Verification:")
        sample = signals[0]
        required_fields = ['source', 'title', 'content',
                           'url', 'timestamp', 'engagement', 'metadata']

        missing_fields = [
            field for field in required_fields if field not in sample]
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        else:
            print(f"✅ All required fields present")

        # Check metadata structure
        required_metadata = [
            'story_id', 'author', 'priority_keywords', 'has_priority_content', 'nyc_relevant']
        missing_metadata = [
            field for field in required_metadata if field not in sample['metadata']]
        if missing_metadata:
            print(f"❌ Missing required metadata: {missing_metadata}")
            return False
        else:
            print(f"✅ All required metadata present")

        print()
        print("🎉 HackerNews collector test PASSED!")
        return True

    except Exception as e:
        print(f"❌ HackerNews collector test FAILED: {str(e)}")
        print(f"   Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_connectivity():
    """Test basic HackerNews API connectivity"""
    print("🔗 Testing HackerNews API connectivity...")

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            # Test fetching new stories
            async with session.get("https://hacker-news.firebaseio.com/v0/newstories.json") as response:
                if response.status == 200:
                    story_ids = await response.json()
                    print(
                        f"✅ API connectivity verified: {len(story_ids)} new stories available")

                    # Test fetching a single story
                    if story_ids:
                        story_id = story_ids[0]
                        async with session.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json") as story_response:
                            if story_response.status == 200:
                                story_data = await story_response.json()
                                print(
                                    f"✅ Story fetch verified: '{story_data.get('title', 'No title')[:50]}...'")
                                return True
                            else:
                                print(
                                    f"❌ Failed to fetch story: HTTP {story_response.status}")
                                return False
                else:
                    print(f"❌ API connectivity failed: HTTP {response.status}")
                    return False

    except Exception as e:
        print(f"❌ API connectivity test failed: {str(e)}")
        return False


async def main():
    """Run all tests"""
    print("🧪 HackerNews Collector Test Suite")
    print("=" * 50)
    print()

    # Test 1: API connectivity
    api_test = await test_api_connectivity()
    print()

    # Test 2: Collector functionality
    if api_test:
        collector_test = await test_hackernews_collector()
    else:
        print("⚠️  Skipping collector test due to API connectivity issues")
        collector_test = False

    print()
    print("📊 Test Results:")
    print(f"   API Connectivity: {'✅ PASS' if api_test else '❌ FAIL'}")
    print(f"   Collector Test: {'✅ PASS' if collector_test else '❌ FAIL'}")
    print()

    if api_test and collector_test:
        print("🎉 All tests PASSED! HackerNews collector is ready to use.")
        return 0
    else:
        print("❌ Some tests FAILED. Check the logs above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
