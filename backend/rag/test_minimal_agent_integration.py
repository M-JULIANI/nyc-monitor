#!/usr/bin/env python3
"""
Test minimal working agent integration with the investigation service.
This tests the complete pipeline from /investigate endpoint to artifact collection.
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


async def test_minimal_agent_integration():
    """Test the minimal working agent integration with investigation service."""

    print("🚀 TESTING MINIMAL AGENT INTEGRATION")
    print("=" * 70)

    try:
        # Import the investigation service
        from rag.investigation_service import investigate_alert
        from rag.investigation.state_manager import AlertData

        # Create test alert data
        alert_data = AlertData(
            alert_id="MINIMAL-AGENT-TEST-001",
            event_type="protest",
            location="Washington Square Park, Manhattan",
            severity=6,
            summary="Test protest for minimal agent integration testing",
            sources=["integration_test"],
            timestamp=datetime.now()
        )

        print(f"📊 Test Alert Created:")
        print(f"   Alert ID: {alert_data.alert_id}")
        print(f"   Location: {alert_data.location}")
        print(f"   Event Type: {alert_data.event_type}")
        print(f"   Severity: {alert_data.severity}")

        # Execute the investigation via the service
        print(f"\n🔧 Executing investigation via service...")

        investigation_result, investigation_id = await investigate_alert(alert_data)

        print(f"\n✅ Investigation Service Completed!")
        print(f"📊 Investigation ID: {investigation_id}")
        print(f"📝 Result Length: {len(investigation_result)} characters")

        # Show first part of result
        print(f"\n📋 Investigation Result Preview:")
        print("=" * 50)
        print(investigation_result[:800] + "..." if len(
            investigation_result) > 800 else investigation_result)
        print("=" * 50)

        # Check if investigation was successful
        success_indicators = [
            "Investigation Complete" in investigation_result,
            "Minimal Working Agent Results" in investigation_result,
            "Maps Generated:" in investigation_result,
            "Images Collected:" in investigation_result,
            investigation_id and len(investigation_id) > 0
        ]

        success_count = sum(success_indicators)

        print(f"\n📊 SUCCESS INDICATORS:")
        print(
            f"   Investigation Complete: {'✅' if 'Investigation Complete' in investigation_result else '❌'}")
        print(
            f"   Agent Results Present: {'✅' if 'Minimal Working Agent Results' in investigation_result else '❌'}")
        print(
            f"   Maps Mentioned: {'✅' if 'Maps Generated:' in investigation_result else '❌'}")
        print(
            f"   Images Mentioned: {'✅' if 'Images Collected:' in investigation_result else '❌'}")
        print(
            f"   Investigation ID: {'✅' if investigation_id and len(investigation_id) > 0 else '❌'}")

        # Check investigation state
        if investigation_id:
            try:
                from rag.investigation.state_manager import state_manager
                final_state = state_manager.get_investigation(investigation_id)

                if final_state:
                    print(f"\n📊 INVESTIGATION STATE CHECK:")
                    print(f"   Total Artifacts: {len(final_state.artifacts)}")
                    print(f"   Is Complete: {final_state.is_complete}")
                    print(
                        f"   Confidence Score: {final_state.confidence_score}")
                    print(f"   Phase: {final_state.phase.value}")

                    # Show artifact breakdown
                    artifact_types = {}
                    for artifact in final_state.artifacts:
                        artifact_type = artifact.get('type', 'unknown')
                        artifact_types[artifact_type] = artifact_types.get(
                            artifact_type, 0) + 1

                    print(f"   Artifact Breakdown: {artifact_types}")

                    # Success criteria
                    artifacts_success = len(final_state.artifacts) >= 8
                    maps_success = artifact_types.get('map_image', 0) >= 2
                    images_success = artifact_types.get('image', 0) >= 6

                    print(f"\n🎯 ARTIFACT SUCCESS CRITERIA:")
                    print(
                        f"   8+ Artifacts: {'✅' if artifacts_success else '❌'} ({len(final_state.artifacts)}/8)")
                    print(
                        f"   2+ Maps: {'✅' if maps_success else '❌'} ({artifact_types.get('map_image', 0)}/2)")
                    print(
                        f"   6+ Images: {'✅' if images_success else '❌'} ({artifact_types.get('image', 0)}/6)")

                    overall_success = (
                        success_count >= 4 and artifacts_success and maps_success and images_success)

                else:
                    print(f"\n❌ Could not retrieve investigation state")
                    overall_success = False

            except Exception as state_error:
                print(f"\n❌ Error checking investigation state: {state_error}")
                overall_success = False
        else:
            print(f"\n❌ No investigation ID returned")
            overall_success = False

        return overall_success

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the integration test."""
    print("🔧 MINIMAL AGENT INTEGRATION TEST")
    print("=" * 80)

    success = await test_minimal_agent_integration()

    print("\n" + "=" * 80)
    if success:
        print("🎉 MINIMAL AGENT INTEGRATION TEST PASSED!")
        print("✅ Investigation service integration working")
        print("✅ Minimal working agent execution successful")
        print("✅ Artifact collection targets met")
        print("✅ Investigation state properly updated")
        print("✅ Results properly formatted")
        print("\n🚀 READY FOR /INVESTIGATE ENDPOINT TESTING!")
    else:
        print("🚨 MINIMAL AGENT INTEGRATION TEST FAILED!")
        print("❌ Integration issues detected")
        print("Need to debug agent integration before endpoint testing")

if __name__ == "__main__":
    asyncio.run(main())
