#!/usr/bin/env python3
"""
Test script for NYC 311 collector to verify it's working correctly.
"""
from monitor.collectors.nyc_311_collector import NYC311Collector
import asyncio
import logging
import sys
import os
import json
import pytest
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the NYC 311 collector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_nyc_311_collector():
    """Test the NYC 311 collector functionality"""

    logger.info("🧪 TESTING NYC 311 COLLECTOR")
    logger.info("=" * 50)

    try:
        # Initialize the collector
        logger.info("📞 Initializing NYC 311 collector...")
        collector = NYC311Collector()
        logger.info(f"✅ Collector initialized: {collector.source_name}")

        # Test signal collection
        logger.info("🔍 Testing signal collection...")
        signals = await collector.collect_signals()

        # Save top 5 signals to JSON file for inspection
        if signals:
            top_5_signals = signals[:5]
            output_file = f"nyc_311_sample_signals_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

            # Create a JSON-serializable version of the signals
            serializable_signals = []
            for signal in top_5_signals:
                # Convert datetime objects to ISO strings for JSON serialization
                serializable_signal = {}
                for key, value in signal.items():
                    if isinstance(value, datetime):
                        serializable_signal[key] = value.isoformat()
                    elif isinstance(value, dict):
                        # Handle nested datetime objects in metadata
                        serializable_metadata = {}
                        for meta_key, meta_value in value.items():
                            if isinstance(meta_value, datetime):
                                serializable_metadata[meta_key] = meta_value.isoformat(
                                )
                            else:
                                serializable_metadata[meta_key] = meta_value
                        serializable_signal[key] = serializable_metadata
                    else:
                        serializable_signal[key] = value
                serializable_signals.append(serializable_signal)

            # Write to JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "collection_info": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "total_signals_collected": len(signals),
                        "sample_size": len(top_5_signals),
                        "collection_source": "nyc_311_collector"
                    },
                    "sample_signals": serializable_signals
                }, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 SAVED SAMPLE SIGNALS: {output_file}")
            logger.info(
                f"   📊 Saved top {len(top_5_signals)} signals for inspection")

        # Analyze results
        logger.info(f"📊 COLLECTION RESULTS:")
        logger.info(f"   Total signals collected: {len(signals)}")

        if signals:
            # Analyze signal categories
            emergency_count = sum(1 for s in signals if s.get(
                'metadata', {}).get('is_emergency', False))
            event_count = sum(1 for s in signals if s.get(
                'metadata', {}).get('is_event', False))

            complaint_types = set()
            boroughs = set()
            agencies = set()

            for signal in signals:
                metadata = signal.get('metadata', {})
                complaint_types.add(metadata.get('complaint_type', 'Unknown'))
                boroughs.add(metadata.get('borough', 'Unknown'))
                agencies.add(metadata.get('agency_name', 'Unknown'))

            logger.info(f"   Emergency signals: {emergency_count}")
            logger.info(f"   Event signals: {event_count}")
            logger.info(f"   Unique complaint types: {len(complaint_types)}")
            logger.info(f"   Boroughs represented: {len(boroughs)}")
            logger.info(f"   Agencies involved: {len(agencies)}")

            # Show sample signals
            logger.info("📋 SAMPLE SIGNALS:")
            for i, signal in enumerate(signals[:3]):
                metadata = signal.get('metadata', {})
                logger.info(f"   Signal {i+1}:")
                logger.info(
                    f"     Title: {signal.get('title', 'No title')[:80]}...")
                logger.info(
                    f"     Type: {metadata.get('complaint_type', 'Unknown')}")
                logger.info(
                    f"     Borough: {metadata.get('borough', 'Unknown')}")
                logger.info(
                    f"     Emergency: {metadata.get('is_emergency', False)}")
                logger.info(f"     Event: {metadata.get('is_event', False)}")
                logger.info(
                    f"     Coordinates: {metadata.get('has_coordinates', False)}")

            if complaint_types:
                logger.info(
                    f"📝 COMPLAINT TYPES FOUND: {', '.join(list(complaint_types)[:10])}")

            if boroughs:
                logger.info(f"🗺️ BOROUGHS ACTIVE: {', '.join(boroughs)}")

        else:
            logger.info(
                "ℹ️  No signals collected (this may be normal during low-activity periods)")
            logger.info(
                "💡 NYC 311 API might have no recent requests matching our filters")

        # Test standardization
        logger.info("🔧 Testing signal standardization...")
        for signal in signals[:1]:  # Test first signal
            required_fields = ['source', 'title', 'content',
                               'url', 'timestamp', 'engagement', 'metadata']
            missing_fields = [
                field for field in required_fields if field not in signal]

            if missing_fields:
                logger.error(
                    f"❌ Signal missing required fields: {missing_fields}")
            else:
                logger.info("✅ Signal standardization format correct")

        logger.info("=" * 50)
        logger.info("🎉 NYC 311 COLLECTOR TEST COMPLETED")
        logger.info(f"📊 Final count: {len(signals)} signals collected")

        return len(signals) > 0  # Return True if we got any signals

    except Exception as e:
        logger.error(f"❌ NYC 311 collector test failed: {e}")
        logger.error(f"   Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        return False


def main():
    """Main test function"""
    logger.info("🚀 Starting NYC 311 collector test")
    logger.info(f"⏰ Test time: {datetime.utcnow().isoformat()}")

    # Check environment
    app_token = os.getenv('NYC_311_APP_TOKEN')
    if app_token:
        logger.info(f"🔑 Using NYC 311 app token: {app_token[:10]}...")
    else:
        logger.info("🔑 Using public API access (no app token)")

    # Run the test
    success = asyncio.run(test_nyc_311_collector())

    if success:
        logger.info("✅ TEST PASSED: NYC 311 collector is working correctly")
        sys.exit(0)
    else:
        logger.error("❌ TEST FAILED: NYC 311 collector encountered issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
