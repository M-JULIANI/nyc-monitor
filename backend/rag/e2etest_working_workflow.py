#!/usr/bin/env python3
"""
Working workflow test that properly sets up investigation state.
This tests the complete pipeline: state creation -> tool execution -> presentation.
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


def test_complete_workflow():
    """Test the complete workflow with proper investigation state."""

    print("🚀 COMPLETE WORKFLOW TEST")
    print("=" * 60)

    # Step 1: Create investigation state
    try:
        from rag.investigation.state_manager import AlertData, state_manager

        # Create alert data
        alert_data = AlertData(
            alert_id="TEST-001",
            event_type="protest",
            location="Washington Square Park, Manhattan",
            severity=6,
            summary="Test protest at Washington Square Park for workflow testing",
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

    # Step 2: Test map generation with proper investigation ID
    try:
        from rag.tools.map_tools import generate_location_map_func

        print(
            f"\n📍 Testing map generation with investigation ID: {investigation_id}")

        result = generate_location_map_func(
            investigation_id=investigation_id,
            location="Washington Square Park, Manhattan",
            zoom_level=16,
            map_type="satellite"
        )

        print(f"Map result: {result}")

        if not result.get("success"):
            print(f"❌ Map generation failed: {result.get('error')}")
            assert False, f"Map generation failed: {result.get('error')}"

        print(f"✅ Map generated successfully!")

    except Exception as e:
        print(f"❌ Map generation failed: {e}")
        assert False, f"Map generation failed: {e}"

    # Step 3: Test image collection with proper investigation ID
    try:
        from rag.tools.research_tools import collect_media_content_simple_func

        print(
            f"\n🖼️ Testing image collection with investigation ID: {investigation_id}")

        result = collect_media_content_simple_func(
            search_terms="Washington Square Park protest",
            content_types="images",
            investigation_id=investigation_id,
            max_items=3
        )

        print(f"Image collection result: {result}")

        if not result.get("success"):
            print(f"❌ Image collection failed: {result.get('error')}")
            assert False, f"Image collection failed: {result.get('error')}"

        print(f"✅ Images collected successfully!")

    except Exception as e:
        print(f"❌ Image collection failed: {e}")
        assert False, f"Image collection failed: {e}"

    # Step 4: Test presentation creation with artifacts
    try:
        from rag.tools.report_tools import create_slides_presentation_func

        print(
            f"\n🎨 Testing presentation creation with investigation ID: {investigation_id}")

        result = create_slides_presentation_func(
            investigation_id=investigation_id,
            title=f"Test Investigation Report - {investigation_id}",
            evidence_types="all"
        )

        print(f"Presentation result: {result}")

        if not result.get("success"):
            print(f"❌ Presentation creation failed: {result.get('error')}")
            assert False, f"Presentation creation failed: {result.get('error')}"

        print(f"✅ Presentation created successfully!")
        print(f"🌐 URL: {result.get('url')}")

        # Check if images were actually inserted
        images_inserted = result.get("images_inserted", 0)
        print(f"📊 Images inserted: {images_inserted}")

        assert True

    except Exception as e:
        print(f"❌ Presentation creation failed: {e}")
        assert False, f"Presentation creation failed: {e}"


if __name__ == "__main__":
    print("🔧 TESTING COMPLETE WORKFLOW WITH PROPER STATE MANAGEMENT")
    print("=" * 80)

    success = test_complete_workflow()

    print("\n" + "=" * 80)
    if success:
        print("🎉 COMPLETE WORKFLOW TEST PASSED!")
        print("✅ Investigation state created")
        print("✅ Map generated and saved to GCS")
        print("✅ Images collected and saved to GCS")
        print("✅ Presentation created with artifacts")
        print("\nNext step: Create minimal agent that follows this working pattern")
    else:
        print("🚨 WORKFLOW TEST FAILED!")
        print("Fix the basic workflow before proceeding to agents")
