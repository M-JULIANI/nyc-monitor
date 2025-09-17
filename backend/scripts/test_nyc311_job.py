#!/usr/bin/env python3
"""
Test script for NYC 311 daily job to verify functionality.
"""
from monitor.scheduler.nyc311_job import NYC311Job
import asyncio
import logging
import sys
import os
import pytest
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_nyc311_job():
    """Test the NYC 311 daily job functionality"""

    logger.info("🧪 TESTING NYC 311 DAILY JOB")
    logger.info("=" * 50)

    try:
        # Initialize the job
        logger.info("📞 Initializing NYC 311 daily job...")
        job = NYC311Job()
        logger.info(
            f"✅ Job initialized with collection: {job.collection_name}")

        # Test job execution
        logger.info("🔍 Testing daily collection process...")
        stats = await job.run_daily_collection()

        # Analyze results
        logger.info(f"📊 JOB EXECUTION RESULTS:")
        logger.info(f"   Status: {stats.get('status', 'unknown')}")
        logger.info(
            f"   Execution time: {stats.get('execution_time_seconds', 0):.2f}s")
        logger.info(
            f"   Signals collected: {stats.get('signals_collected', 0)}")
        logger.info(f"   Duplicates found: {stats.get('duplicates_found', 0)}")
        logger.info(f"   New signals stored: {stats.get('signals_stored', 0)}")
        logger.info(
            f"   Efficiency: {stats.get('efficiency_percent', 0):.1f}% new data")

        # Show breakdown analysis
        if stats.get('complaint_type_breakdown'):
            logger.info("📋 Top complaint types:")
            sorted_complaints = sorted(stats['complaint_type_breakdown'].items(),
                                       key=lambda x: x[1], reverse=True)
            for complaint_type, count in sorted_complaints[:5]:
                logger.info(f"   {count:3d} - {complaint_type}")

        if stats.get('borough_breakdown'):
            logger.info("🗺️ Borough distribution:")
            for borough, count in stats['borough_breakdown'].items():
                logger.info(f"   {count:3d} - {borough}")

        # Performance metrics
        logger.info("⚡ Performance metrics:")
        logger.info(
            f"   Collection duration: {stats.get('collection_duration_seconds', 0):.2f}s")
        logger.info(
            f"   Storage duration: {stats.get('storage_duration_seconds', 0):.2f}s")

        if stats.get('errors'):
            logger.warning(f"⚠️  Errors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:3]:  # Show first 3 errors
                logger.warning(f"   - {error}")

        logger.info("=" * 50)
        logger.info("🎉 NYC 311 DAILY JOB TEST COMPLETED")
        logger.info(
            f"📊 Final summary: {stats.get('signals_stored', 0)} new signals stored")

        return stats.get('success', False)

    except Exception as e:
        logger.error(f"❌ NYC 311 job test failed: {e}")
        logger.error(f"   Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        return False


def main():
    """Main test function"""
    logger.info("🚀 Starting NYC 311 daily job test")
    logger.info(f"⏰ Test time: {datetime.utcnow().isoformat()}")

    # Check environment
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    app_token = os.getenv('NYC_311_APP_TOKEN')

    logger.info(f"🔧 Environment check:")
    logger.info(f"   Project ID: {project_id}")
    logger.info(
        f"   NYC 311 App Token: {'✅ SET' if app_token else '❌ MISSING'}")

    # Run the test
    success = asyncio.run(test_nyc311_job())

    if success:
        logger.info("✅ TEST PASSED: NYC 311 daily job is working correctly")
        sys.exit(0)
    else:
        logger.error("❌ TEST FAILED: NYC 311 daily job encountered issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
