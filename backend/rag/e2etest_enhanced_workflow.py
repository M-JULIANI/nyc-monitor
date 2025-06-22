#!/usr/bin/env python3
"""
Enhanced workflow test that collects 8+ artifacts as intended.
This tests the complete pipeline with proper artifact collection targets.
"""

from dotenv import load_dotenv
import os
import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv("../../atlas-bootstrapped/.env")


def test_enhanced_artifact_collection():
    """Test enhanced artifact collection to reach 8+ artifacts target."""

    print("🚀 ENHANCED ARTIFACT COLLECTION TEST")
    print("=" * 70)

    # Step 1: Create investigation state
    try:
        from rag.investigation.state_manager import AlertData, state_manager

        # Create alert data
        alert_data = AlertData(
            alert_id="ENHANCED-001",
            event_type="protest",
            location="Washington Square Park, Manhattan",
            severity=7,
            summary="Enhanced test protest at Washington Square Park with comprehensive artifact collection",
            sources=["test_source"],
            timestamp=datetime.now()
        )

        # Create investigation state
        investigation_state = state_manager.create_investigation(alert_data)
        investigation_id = investigation_state.investigation_id

        print(f"✅ Created investigation state: {investigation_id}")

    except Exception as e:
        print(f"❌ Failed to create investigation state: {e}")
        assert False, f"Failed to create investigation state: {e}"

    # Step 2: Generate MULTIPLE maps (target: 2-3 maps)
    try:
        from rag.tools.map_tools import generate_location_map_func

        print(
            f"\n📍 Generating multiple maps for investigation: {investigation_id}")

        # Map 1: Satellite view, close zoom
        result1 = generate_location_map_func(
            investigation_id=investigation_id,
            location="Washington Square Park, Manhattan",
            zoom_level=16,
            map_type="satellite"
        )
        print(f"Map 1 (satellite, zoom 16): {result1.get('success')}")

        # Map 2: Roadmap view, medium zoom
        result2 = generate_location_map_func(
            investigation_id=investigation_id,
            location="Washington Square Park, Manhattan",
            zoom_level=14,
            map_type="roadmap"
        )
        print(f"Map 2 (roadmap, zoom 14): {result2.get('success')}")

        # Map 3: Hybrid view, wide zoom
        result3 = generate_location_map_func(
            investigation_id=investigation_id,
            location="Washington Square Park, Manhattan",
            zoom_level=12,
            map_type="hybrid"
        )
        print(f"Map 3 (hybrid, zoom 12): {result3.get('success')}")

        maps_success = all([result1.get('success'), result2.get(
            'success'), result3.get('success')])
        if not maps_success:
            print(f"❌ Some map generation failed")
            assert False, "Some map generation failed"

        print(f"✅ Generated 3 maps successfully!")

    except Exception as e:
        print(f"❌ Map generation failed: {e}")
        assert False, f"Map generation failed: {e}"

    # Step 3: Collect MORE images (target: 5+ images)
    try:
        from rag.tools.research_tools import collect_media_content_simple_func

        print(
            f"\n🖼️ Collecting multiple image sets for investigation: {investigation_id}")

        # Image set 1: General protest images
        result1 = collect_media_content_simple_func(
            search_terms="Washington Square Park protest",
            content_types="images",
            investigation_id=investigation_id,
            max_items=5
        )
        print(
            f"Image set 1 (protest): {result1.get('downloaded_count', 0)} downloaded")

        # Image set 2: Location-specific images
        result2 = collect_media_content_simple_func(
            search_terms="Washington Square Park Manhattan",
            content_types="images",
            investigation_id=investigation_id,
            max_items=3
        )
        print(
            f"Image set 2 (location): {result2.get('downloaded_count', 0)} downloaded")

        # Image set 3: Event-specific images
        result3 = collect_media_content_simple_func(
            search_terms="NYC protest demonstration",
            content_types="images",
            investigation_id=investigation_id,
            max_items=3
        )
        print(
            f"Image set 3 (NYC events): {result3.get('downloaded_count', 0)} downloaded")

        total_images = (result1.get('downloaded_count', 0) +
                        result2.get('downloaded_count', 0) +
                        result3.get('downloaded_count', 0))

        print(f"✅ Total images collected: {total_images}")

        if total_images < 5:
            print(
                f"⚠️ Warning: Only collected {total_images} images, target was 5+")

    except Exception as e:
        print(f"❌ Image collection failed: {e}")
        assert False, f"Image collection failed: {e}"

    # Step 4: Generate additional artifacts (screenshots, timeline)
    try:
        print(
            f"\n📸 Generating additional artifacts for investigation: {investigation_id}")

        # Screenshot 1: Google search results
        from rag.tools.research_tools import save_investigation_screenshot_func

        screenshot_result = save_investigation_screenshot_func(
            url="https://www.google.com/search?q=Washington+Square+Park+protest",
            description="Google search results for Washington Square Park protest",
            investigation_id=investigation_id
        )
        print(f"Screenshot 1: {screenshot_result.get('success')}")

        # Timeline generation
        from rag.tools.research_tools import generate_investigation_timeline_func

        timeline_result = generate_investigation_timeline_func(
            investigation_id=investigation_id,
            include_evidence_points=True,
            chart_type="timeline"
        )
        print(f"Timeline: {timeline_result.get('success')}")

        additional_artifacts = sum([
            1 if screenshot_result.get('success') else 0,
            1 if timeline_result.get('success') else 0
        ])

        print(f"✅ Additional artifacts generated: {additional_artifacts}")

    except Exception as e:
        print(f"❌ Additional artifact generation failed: {e}")
        additional_artifacts = 0

    # Step 5: Check total artifact count
    try:
        from rag.investigation.state_manager import state_manager
        investigation_state = state_manager.get_investigation(investigation_id)

        total_artifacts = len(
            investigation_state.artifacts) if investigation_state else 0
        print(f"\n📊 TOTAL ARTIFACTS COLLECTED: {total_artifacts}")

        if total_artifacts >= 8:
            print(
                f"🎯 TARGET ACHIEVED: {total_artifacts} artifacts (target: 8+)")
            assert True
        else:
            print(
                f"⚠️ TARGET MISSED: {total_artifacts} artifacts (target: 8+)")
            assert False, f"TARGET MISSED: {total_artifacts} artifacts (target: 8+)"

        # Show artifact breakdown
        if investigation_state:
            artifact_types = {}
            for artifact in investigation_state.artifacts:
                artifact_type = artifact.get('type', 'unknown')
                artifact_types[artifact_type] = artifact_types.get(
                    artifact_type, 0) + 1

            print(f"📋 Artifact breakdown:")
            for artifact_type, count in artifact_types.items():
                print(f"   {artifact_type}: {count}")

    except Exception as e:
        print(f"❌ Failed to check artifact count: {e}")
        assert False, f"Failed to check artifact count: {e}"


def test_enhanced_presentation():
    """Test presentation creation with enhanced artifact collection."""

    print(f"\n🎨 TESTING ENHANCED PRESENTATION CREATION")
    print("=" * 60)

    # Run enhanced artifact collection first
    try:
        test_enhanced_artifact_collection()
    except AssertionError:
        print("❌ Enhanced artifact collection failed, skipping presentation test")
        assert False, "Enhanced artifact collection failed"

    # Get the investigation ID from the last test
    try:
        from rag.investigation.state_manager import state_manager

        # Find the most recent investigation
        investigations = state_manager.investigations
        if not investigations:
            print("❌ No investigations found")
            assert False, "No investigations found"

        # Get the most recent investigation ID
        investigation_id = max(investigations.keys(),
                               key=lambda x: investigations[x].created_at)
        investigation_state = investigations[investigation_id]

        print(f"📊 Using investigation: {investigation_id}")
        print(f"   Total artifacts: {len(investigation_state.artifacts)}")

        # Create presentation
        from rag.tools.report_tools import create_slides_presentation_func

        result = create_slides_presentation_func(
            investigation_id=investigation_id,
            title=f"Enhanced Investigation Report - {investigation_id}",
            evidence_types="all"
        )

        if not result.get("success"):
            print(f"❌ Presentation creation failed: {result.get('error')}")
            assert False, f"Presentation creation failed: {result.get('error')}"

        print(f"✅ Enhanced presentation created successfully!")
        print(f"🌐 URL: {result.get('url')}")

        # Check if we got more images inserted
        images_inserted = result.get("images_inserted", 0)
        images_failed = result.get("images_failed", 0)
        total_evidence = result.get("evidence_count", 0)

        print(f"📊 Enhanced presentation stats:")
        print(f"   Total evidence items: {total_evidence}")
        print(f"   Images successfully inserted: {images_inserted}")
        print(f"   Images failed to insert: {images_failed}")
        print(
            f"   Text replacements applied: {result.get('replacements_applied', 0)}")

        # Success criteria: 8+ evidence items, 6+ images inserted
        success = (total_evidence >= 8 and images_inserted >= 6)

        if success:
            print(f"🎯 ENHANCED PRESENTATION SUCCESS!")
            assert True
        else:
            print(f"⚠️ Enhancement targets not fully met")
            print(f"   Target: 8+ evidence, 6+ images inserted")
            print(
                f"   Actual: {total_evidence} evidence, {images_inserted} images inserted")
            assert False, f"Enhancement targets not fully met: {total_evidence} evidence, {images_inserted} images inserted"

    except Exception as e:
        print(f"❌ Enhanced presentation creation failed: {e}")
        assert False, f"Enhanced presentation creation failed: {e}"


if __name__ == "__main__":
    print("🔧 TESTING ENHANCED WORKFLOW FOR 8+ ARTIFACTS")
    print("=" * 80)

    success = test_enhanced_presentation()

    print("\n" + "=" * 80)
    if success:
        print("🎉 ENHANCED WORKFLOW TEST PASSED!")
        print("✅ 8+ artifacts collected successfully")
        print("✅ 6+ images inserted into presentation")
        print("✅ Multiple maps generated (satellite, roadmap, hybrid)")
        print("✅ Multiple image sets collected")
        print("✅ Additional artifacts (screenshots, timeline) generated")
        print("\nReady to create minimal agent with enhanced artifact collection!")
    else:
        print("🚨 ENHANCED WORKFLOW TEST FAILED!")
        print("Need to fix artifact collection before proceeding to agents")
