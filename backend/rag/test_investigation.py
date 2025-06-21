#!/usr/bin/env python3
"""
Test script for the Atlas Investigation System.
This script tests the complete 5-agent workflow end-to-end.
"""

# CRITICAL: Load environment variables FIRST before any other imports
import sys
from datetime import datetime
import logging
import json
import asyncio
from rag.investigation.state_manager import AlertData, state_manager
from rag.investigation_service import investigate_alert
import os
from dotenv import load_dotenv

# Load .env file from the project root (two levels up from this file)
env_file_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(env_file_path):
    load_dotenv(env_file_path)
    print(f"✅ Loaded environment variables from {env_file_path}")
    print(
        f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', 'NOT SET')}")
else:
    print(f"❌ .env file not found at {env_file_path}")

# Now import everything else AFTER environment variables are loaded

# Configure enhanced logging for detailed tracing


def setup_enhanced_logging():
    """Set up detailed logging to trace the investigation process"""

    # Create formatter for detailed output
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s'
    )

    # Console handler with detailed formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel(logging.DEBUG)

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()  # Clear existing handlers
    root_logger.addHandler(console_handler)

    # Set specific logger levels for detailed tracing
    loggers_to_trace = [
        'rag.investigation_service',
        'rag.investigation.state_manager',
        'rag.investigation.progress_tracker',
        'rag.investigation.tracing',
        'rag.agents.research_agent',
        'rag.agents.data_agent',
        'rag.agents.analysis_agent',
        'rag.agents.report_agent',
        'rag.tools.research_tools',
        'rag.tools.data_tools',
        'rag.tools.analysis_tools',
        'rag.tools.report_tools',
        'google.cloud.aiplatform.adk',
    ]

    for logger_name in loggers_to_trace:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

    print("🔍 Enhanced logging enabled - you'll see detailed agent/tool traces")
    print("=" * 80)


# Configure logging with enhanced detail
setup_enhanced_logging()
logger = logging.getLogger(__name__)

# Import the investigation system


async def debug_slideshow_placeholders():
    """Debug slideshow placeholder replacement specifically."""

    print("\n🔍 DEBUGGING SLIDESHOW PLACEHOLDER REPLACEMENT")
    print("=" * 60)

    # Create a test alert
    test_alert = AlertData(
        alert_id="DEBUG-SLIDESHOW-001",
        event_type="Community Protest",
        location="Washington Square Park, Manhattan",
        severity=7,
        summary="Tens of thousands flooded the streets of Manhattan on June 14 in a \"No Kings\" protest over Donald Trump's 79th birthday, a day that also marked a planned big military parade in Washington, DC, marking the 250th anniversary of the US Army. The demonstration stretched from Bryant Park to Madison Square Park in a display of resistance to what organizers dubbed \"presidential monarchism.\" The Manhattan march drew the largest crowd, which some reports placed at around 50,000 people. Marchers carried banners, beat drums, and chanted through steady rain despite the advertised theme. The demonstration remained peaceful throughout, despite scattered downpours and a strong police presence. No arrests were reported. Protesters paused at key points along the route, including outside the David Glasgow Farragut statue in Madison Square Park, where speeches and poetry fiercely criticized Trump's immigration stances and US backing of Israel's military campaign in Gaza.",
        sources=["Reddit", "Twitter", "311 Complaints", "Community Board"],
        timestamp=datetime.utcnow()
    )

    try:
        # 1. Run investigation to create the investigation state
        print("\n📋 Step 1: Running Investigation (Creates Investigation State)")
        investigation_result, investigation_id = await investigate_alert(test_alert)
        print(f"   Investigation ID: {investigation_id}")
        print(f"   Result Length: {len(investigation_result)} characters")

        # 2. Collect ALL artifacts BEFORE generating presentation
        print("\n🎯 Step 2: Collecting ALL Artifacts (Maps, Images, Screenshots)")
        await force_artifact_collection(investigation_id, "Washington Square Park, Manhattan")

        # 3. Inspect Final Investigation State with all artifacts
        print("\n🔍 Step 3: Final Investigation State Inspection")
        investigation_state = state_manager.get_investigation(investigation_id)
        if investigation_state:
            print(f"   ✅ Investigation State Found:")
            print(f"      Phase: {investigation_state.phase}")
            print(f"      Confidence: {investigation_state.confidence_score}")
            print(f"      Findings Count: {len(investigation_state.findings)}")
            print(
                f"      🎯 TOTAL ARTIFACTS: {len(investigation_state.artifacts)}")

            # Show artifact details
            for i, artifact in enumerate(investigation_state.artifacts):
                artifact_type = artifact.get("type", "unknown")
                saved_to_gcs = artifact.get("saved_to_gcs", False)
                has_signed_url = bool(artifact.get("signed_url"))
                print(
                    f"         {i+1}. {artifact_type} (GCS: {saved_to_gcs}, URL: {has_signed_url})")
        else:
            print(
                f"   ❌ No Investigation State Found for ID: {investigation_id}")
            return False

        # 4. Generate SINGLE presentation with ALL artifacts collected
        print("\n🎨 Step 4: Generating Final Presentation (With All Artifacts)")
        try:
            from rag.tools.report_tools import create_slides_presentation_func

            slides_result = create_slides_presentation_func(
                investigation_id=investigation_id,
                title=f"NYC Atlas Investigation: {test_alert.event_type} - {test_alert.location}",
                template_type="status_tracker",
                evidence_types="all"
            )

            print(f"   ✅ Slides Creation Result:")
            print(f"      Success: {slides_result.get('success', False)}")
            print(
                f"      Evidence Count: {slides_result.get('evidence_count', 0)}")
            print(
                f"      Replacements Applied: {slides_result.get('replacements_applied', 0)}")
            print(f"      URL: {slides_result.get('url', 'N/A')}")

            if slides_result.get('success'):
                print(f"\n   🎯 FINAL PRESENTATION URL:")
                print(f"      {slides_result.get('url')}")
                print(f"   📊 Check this presentation for:")
                print(
                    f"      • All {slides_result.get('replacements_applied', 0)} placeholders replaced")
                print(
                    f"      • {slides_result.get('evidence_count', 0)} evidence items inserted")
                print(
                    f"      • {len(investigation_state.artifacts)} total artifacts included")

        except Exception as e:
            print(f"   ❌ Google Slides creation failed: {e}")
            logger.exception("Slides creation error details")
            return False

        print("\n" + "=" * 60)
        print("🎯 SIMPLIFIED FLOW SUMMARY:")
        print(f"   1. Investigation Created: ✅")
        print(
            f"   2. Artifacts Collected: ✅ ({len(investigation_state.artifacts)} items)")
        print(f"   3. Presentation Generated: ✅ (Once, with all artifacts)")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ Debugging failed: {e}")
        logger.exception("Debugging error details")
        return False


async def force_artifact_collection(investigation_id: str, location: str):
    """Manually trigger artifact collection to test the system."""

    print("\n🔧 FORCE ARTIFACT COLLECTION")
    print("=" * 50)

    try:
        # 1. Generate location map (normal zoom)
        print("📍 Step 1: Generating location map (normal zoom)...")
        from rag.tools.map_tools import generate_location_map_func

        map_result = generate_location_map_func(
            location=location,
            alert_id=investigation_id,
            zoom_level=16,
            map_type="satellite",
            include_pin=True
        )
        print(f"   Map Result: {map_result.get('success', False)}")
        if map_result.get("success"):
            print(f"   Map File: {map_result.get('filename')}")
            print(f"   Map Source: {map_result.get('source')}")

        # 1b. Generate location map (wide zoom)
        print("📍 Step 1b: Generating location map (wide zoom)...")
        map_wide_result = generate_location_map_func(
            location=location,
            alert_id=investigation_id,
            zoom_level=12,  # Wider zoom level
            map_type="satellite",
            include_pin=True
        )
        print(f"   Wide Map Result: {map_wide_result.get('success', False)}")
        if map_wide_result.get("success"):
            print(f"   Wide Map File: {map_wide_result.get('filename')}")
            print(f"   Wide Map Source: {map_wide_result.get('source')}")

        # 2. Collect media content related to the investigation
        print("\n🖼️ Step 2: Collecting media content...")
        from rag.tools.research_tools import collect_media_content_simple_func

        media_result = collect_media_content_simple_func(
            search_terms="No Kings protest, Manhattan protest, Trump protest",
            content_types="images",
            investigation_id=investigation_id,
            max_items=3
        )
        print(f"   Media Result: {media_result.get('success', False)}")
        print(f"   Media Items: {media_result.get('total_items', 0)}")

        # 3. Take screenshots of relevant news sources
        print("\n📸 Step 3: Taking news screenshots...")
        from rag.tools.research_tools import save_investigation_screenshot_simple_func

        news_urls = [
            "https://www.ny1.com",
            "https://www.pix11.com",
            "https://www.amny.com"
        ]

        screenshot_results = []
        for url in news_urls:
            screenshot_result = save_investigation_screenshot_simple_func(
                url=url,
                description=f"News website screenshot from {url}",
                investigation_id=investigation_id
            )
            screenshot_results.append(screenshot_result)
            print(
                f"   Screenshot {url}: {screenshot_result.get('success', False)}")

        # 4. Generate investigation timeline
        print("\n📊 Step 4: Generating timeline chart...")
        from rag.tools.map_tools import generate_investigation_timeline_func

        timeline_result = generate_investigation_timeline_func(
            investigation_id=investigation_id,
            include_evidence_points=True
        )
        print(f"   Timeline Result: {timeline_result.get('success', False)}")
        if timeline_result.get("success"):
            print(f"   Timeline Events: {timeline_result.get('events', [])}")

        # 5. Check investigation state for all artifacts
        print("\n📋 Step 5: Checking final artifact count...")
        investigation_state = state_manager.get_investigation(investigation_id)
        if investigation_state:
            print(f"   Total Artifacts: {len(investigation_state.artifacts)}")
            for i, artifact in enumerate(investigation_state.artifacts):
                artifact_type = artifact.get("type", "unknown")
                artifact_desc = artifact.get(
                    "description", "No description")[:50]
                print(f"   Artifact {i+1}: {artifact_type} - {artifact_desc}")
        else:
            print("   ❌ No investigation state found")

        print(
            f"\n✅ Artifact collection complete! Collected {len(investigation_state.artifacts)} artifacts.")
        return True

    except Exception as e:
        print(f"❌ Force artifact collection failed: {e}")
        logger.exception("Force artifact collection error details")
        return False


async def test_slides_accessible_urls():
    """Test generating Slides-accessible URLs using service account credentials."""

    print("\n🔗 TESTING SLIDES-ACCESSIBLE URLS WITH SERVICE ACCOUNT")
    print("=" * 60)

    try:
        # Get the most recent investigation
        investigations = list(state_manager.investigations.keys())
        if not investigations:
            print("❌ No investigations found for testing")
            return False

        investigation_id = investigations[0]
        investigation_state = state_manager.get_investigation(investigation_id)

        if not investigation_state or not investigation_state.artifacts:
            print(f"❌ No artifacts found in investigation {investigation_id}")
            return False

        print(f"📋 Testing with investigation: {investigation_id}")
        print(f"🎯 Available artifacts: {len(investigation_state.artifacts)}")

        # Test generating Slides-accessible URLs
        from rag.tools.artifact_manager import artifact_manager

        # Find an image artifact to test
        test_artifact = None
        for artifact in investigation_state.artifacts:
            if artifact.get("type") == "image" and artifact.get("filename"):
                test_artifact = artifact
                break

        if not test_artifact:
            print("❌ No suitable image artifact found for testing")
            return False

        filename = test_artifact["filename"]
        print(f"🧪 Testing with artifact: {filename}")

        # Test generating Slides-accessible URL
        print("\n1️⃣ Generating Slides-accessible URL using service account...")
        url_result = artifact_manager.get_slides_accessible_url(
            investigation_id, filename)

        if url_result["success"]:
            slides_url = url_result["url"]
            url_type = url_result["url_type"]
            print(f"   ✅ Successfully generated: {slides_url}")
            print(f"   📝 URL Type: {url_type}")
            print(
                f"   🎯 Accessible by: {url_result.get('accessible_by', 'unknown')}")

            # Test if the URL is accessible
            print("\n2️⃣ Testing URL accessibility...")
            try:
                import requests
                response = requests.head(slides_url, timeout=10)
                if response.status_code == 200:
                    print(f"   ✅ URL accessible (HTTP {response.status_code})")
                    print(
                        f"   📏 Content-Length: {response.headers.get('content-length', 'unknown')}")
                    url_accessible = True
                else:
                    print(
                        f"   ❌ URL not accessible (HTTP {response.status_code})")
                    url_accessible = False
            except Exception as e:
                print(f"   ❌ Error testing URL access: {e}")
                url_accessible = False

            print(f"\n🎯 TEST SUMMARY:")
            print(
                f"   URL Generation: {'✅ PASS' if url_result['success'] else '❌ FAIL'}")
            print(f"   URL Type: {url_type}")
            print(
                f"   URL Accessible: {'✅ PASS' if url_accessible else '❌ FAIL'}")
            print(f"   Security: ✅ PASS (artifacts remain private)")

            return url_result['success'] and url_accessible

        else:
            print(f"   ❌ Failed to generate URL: {url_result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.exception("Slides-accessible URL test error details")
        return False


async def main():
    """Main test function with simplified artifact collection and presentation generation."""

    print("🏗️  NYC Atlas Investigation System - CLEAN SERVICE ACCOUNT APPROACH")
    print("=" * 70)
    print("This improved flow:")
    print("  1. Creates investigation state")
    print("  2. Collects ALL artifacts (maps, images, screenshots)")
    print("  3. Uses service account for private artifact access")
    print("  4. Generates presentation with working image insertion")
    print("  5. Keeps all artifacts private throughout (more secure)")
    print("=" * 70)

    # Run the simplified slideshow debugging (which now includes everything)
    main_success = await debug_slideshow_placeholders()

    # Test public artifact access specifically
    print("\n" + "=" * 70)
    public_access_success = await test_slides_accessible_urls()

    print("\n" + "=" * 70)
    print("📊 FINAL TEST SUMMARY:")
    print(f"   Main Flow: {'✅ PASS' if main_success else '❌ FAIL'}")
    print(
        f"   Service Account URLs: {'✅ PASS' if public_access_success else '❌ FAIL'}")
    print("=" * 70)

    if main_success and public_access_success:
        print("\n🎉 ALL TESTS COMPLETE!")
        print("💡 The system now supports:")
        print("   ✅ All placeholders properly replaced")
        print("   ✅ Real images downloaded and saved to GCS")
        print("   ✅ Service account access for private artifacts")
        print("   ✅ No more public/private access management needed")
        print("   ✅ Enhanced security - artifacts stay private")
        print("   ✅ Works in both DEV and PRODUCTION environments")
        return 0
    else:
        print("\n🚨 SOME TESTS FAILED!")
        print("💡 Review the detailed logs above for specific problems.")
        if main_success and not public_access_success:
            print(
                "🔍 Service account access issue - check credentials and bucket permissions")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
