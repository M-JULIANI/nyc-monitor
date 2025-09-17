#!/usr/bin/env python3
"""
Test script for Twitter collector.
Tests Twitter API connectivity and signal collection for NYC monitoring.
"""
from monitor.collectors.twitter_collector import TwitterCollector
from monitor.collectors.base_collector import BaseCollector
import asyncio
import sys
import os
import logging
import pytest
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_twitter_collector():
    """Test the Twitter collector functionality"""
    logger.info("=== Testing Twitter Collector ===")

    try:
        # Initialize collector
        logger.info("🔧 Initializing Twitter collector...")
        collector = TwitterCollector()
        logger.info("✅ Twitter collector initialized successfully")

        # Test signal collection
        logger.info("🔍 Testing signal collection...")
        start_time = datetime.utcnow()
        signals = await collector.collect_signals()
        end_time = datetime.utcnow()

        collection_time = (end_time - start_time).total_seconds()
        logger.info(f"✅ Collection completed in {collection_time:.2f} seconds")

        # Analyze results
        if signals:
            logger.info(f"📊 Collected {len(signals)} Twitter signals")

            # Analyze signal types and priorities
            priority_count = sum(1 for s in signals if s['metadata'].get(
                'has_priority_content', False))
            emergency_count = sum(1 for s in signals
                                  if any(keyword in s['metadata'].get('priority_flags', [])
                                         for keyword in ['911', 'emergency', 'fire', 'shooting', 'explosion', 'ambulance', 'police']))

            logger.info(f"   🚨 Priority signals: {priority_count}")
            logger.info(f"   🆘 Emergency signals: {emergency_count}")

            # Show top 3 signals
            logger.info("📰 Top signals:")
            for i, signal in enumerate(signals[:3], 1):
                title = signal.get('title', 'No title')[:80]
                score = signal.get('engagement', {}).get('score', 0)
                keywords = signal['metadata'].get('priority_keywords', [])
                locations = signal['metadata'].get('locations', [])
                context = signal['metadata'].get('context', 'Unknown')

                logger.info(f"   {i}. [{context}] {title}...")
                logger.info(
                    f"      Score: {score} | Keywords: {keywords[:3]} | Locations: {len(locations)}")
                logger.info(f"      URL: {signal.get('url', 'No URL')}")

                if signal['metadata'].get('has_coordinates'):
                    lat = signal['metadata'].get('latitude')
                    lng = signal['metadata'].get('longitude')
                    logger.info(f"      Coordinates: {lat}, {lng}")

                logger.info("")

            # Test location extraction
            signals_with_locations = [
                s for s in signals if s['metadata'].get('locations')]
            signals_with_coords = [
                s for s in signals if s['metadata'].get('has_coordinates')]

            logger.info(f"🗺️  Location Analysis:")
            logger.info(
                f"   Signals with location mentions: {len(signals_with_locations)}")
            logger.info(
                f"   Signals with coordinates: {len(signals_with_coords)}")

            # Test engagement metrics
            avg_engagement = sum(s.get('engagement', {}).get('score', 0)
                                 for s in signals) / len(signals) if signals else 0
            max_engagement = max(s.get('engagement', {}).get('score', 0)
                                 for s in signals) if signals else 0

            logger.info(f"📈 Engagement Analysis:")
            logger.info(f"   Average engagement score: {avg_engagement:.1f}")
            logger.info(f"   Max engagement score: {max_engagement}")

        else:
            logger.warning("⚠️  No Twitter signals collected")
            logger.info("🔍 Check Twitter API credentials and search queries")

        # Test credential validation
        logger.info("🔑 Testing credential validation...")
        logger.info(
            f"   API Key: {'✅ SET' if collector.api_key else '❌ MISSING'}")
        logger.info(
            f"   API Secret: {'✅ SET' if collector.api_key_secret else '❌ MISSING'}")
        logger.info(
            f"   Bearer Token: {'✅ SET' if collector.bearer_token else '❌ MISSING'}")

        # Test monitoring contexts
        logger.info(f"🔍 Monitoring Contexts ({len(collector.nyc_contexts)}):")
        for i, context in enumerate(collector.nyc_contexts, 1):
            logger.info(f"   {i}. {context['name']}: {context['query']}")

        # Show priority keywords
        logger.info(
            f"🔑 Priority Keywords ({len(collector.priority_keywords)}):")
        for i, keyword in enumerate(collector.priority_keywords[:5], 1):
            logger.info(f"   {i}. {keyword}")
        if len(collector.priority_keywords) > 5:
            logger.info(
                f"   ... and {len(collector.priority_keywords) - 5} more keywords")

        logger.info("✅ Twitter collector test completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Twitter collector test failed: {str(e)}")
        logger.error(f"   Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        return False


def main():
    """Main test function"""
    logger.info("🚀 Starting Twitter collector test")

    # Check environment variables
    required_env_vars = ['TWITTER_API_KEY',
                         'TWITTER_API_KEY_SECRET', 'TWITTER_BEARER_TOKEN']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        logger.error("❌ Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"   - {var}")
        logger.error("Please set these environment variables and try again.")
        sys.exit(1)

    # Run the test
    success = asyncio.run(test_twitter_collector())

    if success:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
