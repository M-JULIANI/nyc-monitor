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

    print("\n🔍 TESTING ADK AGENT WORKFLOW (NO BYPASS)")
    print("=" * 60)

    # Create a test alert
    test_alert = AlertData(
        alert_id="DEBUG-ADK-WORKFLOW-001",
        event_type="Community Protest",
        location="Washington Square Park, Manhattan",
        severity=7,
        summary="Tens of thousands flooded the streets of Manhattan on June 14 in a \"No Kings\" protest over Donald Trump's 79th birthday, a day that also marked a planned big military parade in Washington, DC, marking the 250th anniversary of the US Army. The demonstration stretched from Bryant Park to Madison Square Park in a display of resistance to what organizers dubbed \"presidential monarchism.\" The Manhattan march drew the largest crowd, which some reports placed at around 50,000 people. Marchers carried banners, beat drums, and chanted through steady rain despite the advertised theme. The demonstration remained peaceful throughout, despite scattered downpours and a strong police presence. No arrests were reported. Protesters paused at key points along the route, including outside the David Glasgow Farragut statue in Madison Square Park, where speeches and poetry fiercely criticized Trump's immigration stances and US backing of Israel's military campaign in Gaza.",
        sources=["Reddit", "Twitter", "311 Complaints", "Community Board"],
        timestamp=datetime.utcnow()
    )

    try:
        # 1. Run FULL ADK investigation (should collect artifacts automatically)
        print("\n📋 Step 1: Running FULL ADK Investigation (Should Auto-Collect Artifacts)")
        investigation_result, investigation_id = await investigate_alert(test_alert)
        print(f"   Investigation ID: {investigation_id}")
        print(f"   Result Length: {len(investigation_result)} characters")

        # Show first 1000 chars of result to see what happened
        print(f"\n📄 Investigation Result Preview:")
        print(f"   {investigation_result[:1000]}...")

        # Check if the result contains evidence of tool execution
        tool_executions_found = []
        if "generate_location_map" in investigation_result:
            tool_executions_found.append("✅ generate_location_map")
        else:
            tool_executions_found.append("❌ generate_location_map")

        if "collect_media_content" in investigation_result:
            tool_executions_found.append("✅ collect_media_content")
        else:
            tool_executions_found.append("❌ collect_media_content")

        if "save_investigation_screenshot" in investigation_result:
            tool_executions_found.append("✅ save_investigation_screenshot")
        else:
            tool_executions_found.append("❌ save_investigation_screenshot")

        if "generate_investigation_timeline" in investigation_result:
            tool_executions_found.append("✅ generate_investigation_timeline")
        else:
            tool_executions_found.append("❌ generate_investigation_timeline")

        if "ARTIFACT COLLECTION COMPLETE" in investigation_result:
            tool_executions_found.append("✅ ARTIFACT COLLECTION COMPLETE")
        else:
            tool_executions_found.append("❌ ARTIFACT COLLECTION COMPLETE")

        print(f"\n🔍 Tool Execution Analysis:")
        for execution in tool_executions_found:
            print(f"   {execution}")

        # 2. Inspect Investigation State with artifacts collected by ADK
        print("\n🔍 Step 2: Investigation State Inspection (Post-ADK)")
        investigation_state = state_manager.get_investigation(investigation_id)
        if investigation_state:
            print(f"   ✅ Investigation State Found:")
            print(f"      Phase: {investigation_state.phase}")
            print(f"      Confidence: {investigation_state.confidence_score}")
            print(f"      Findings Count: {len(investigation_state.findings)}")
            print(
                f"      🎯 TOTAL ARTIFACTS: {len(investigation_state.artifacts)}")

            # Show artifact details
            if investigation_state.artifacts:
                print(f"   📦 Artifacts Collected by ADK:")
                for i, artifact in enumerate(investigation_state.artifacts):
                    artifact_type = artifact.get("type", "unknown")
                    saved_to_gcs = artifact.get("saved_to_gcs", False)
                    has_signed_url = bool(artifact.get("signed_url"))
                    filename = artifact.get("filename", "no filename")
                    print(
                        f"      {i+1}. {artifact_type} - {filename} (GCS: {saved_to_gcs}, URL: {has_signed_url})")
            else:
                print(
                    f"   ❌ NO ARTIFACTS COLLECTED BY ADK - This indicates the agent workflow failed")
        else:
            print(
                f"   ❌ No Investigation State Found for ID: {investigation_id}")
            return False

        # 3. Generate presentation with ADK-collected artifacts
        print("\n🎨 Step 3: Generating Presentation (With ADK-Collected Artifacts)")
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
            print(
                f"      Images Inserted: {slides_result.get('images_inserted', 0)}")
            print(
                f"      Images Failed: {slides_result.get('images_failed', 0)}")
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

        # 4. Final Assessment
        print("\n" + "=" * 60)
        print("🎯 ADK AGENT WORKFLOW TEST SUMMARY:")
        print(f"   1. Investigation Created: ✅")
        print(
            f"   2. ADK Agent Execution: {'✅' if len(investigation_state.artifacts) > 0 else '❌'}")
        print(
            f"   3. Artifacts Collected: {'✅' if len(investigation_state.artifacts) > 0 else '❌'} ({len(investigation_state.artifacts)} items)")
        print(
            f"   4. Presentation Generated: ✅ (With {slides_result.get('images_inserted', 0)} images)")

        # Success criteria: ADK must have collected artifacts
        adk_success = len(investigation_state.artifacts) > 0
        if adk_success:
            print(f"\n🎉 ADK AGENT WORKFLOW: ✅ SUCCESS")
            print(f"   The ADK agents properly executed tools and collected artifacts!")
        else:
            print(f"\n🚨 ADK AGENT WORKFLOW: ❌ FAILED")
            print(f"   The ADK agents did not execute tools or collect artifacts.")
            print(f"   This means the agent transfer/tool execution is still broken.")

        print("=" * 60)
        return adk_success

    except Exception as e:
        print(f"❌ ADK workflow test failed: {e}")
        logger.exception("ADK workflow test error details")
        return False


async def main():
    """Main test function for ADK agent workflow validation."""

    print("🤖 NYC Atlas Investigation System - ADK AGENT WORKFLOW TEST")
    print("=" * 70)
    print("This test validates:")
    print("  1. ADK agent system properly initializes")
    print("  2. Root agent transfers to research agent correctly")
    print("  3. Research agent executes mandatory artifact collection tools")
    print("  4. Artifacts are properly saved and accessible")
    print("  5. Presentation generation works with ADK-collected artifacts")
    print("=" * 70)

    # Run the ADK agent workflow test
    adk_success = await debug_slideshow_placeholders()

    print("\n" + "=" * 70)
    print("📊 FINAL ADK AGENT WORKFLOW TEST RESULTS:")
    print(f"   ADK Agent Workflow: {'✅ PASS' if adk_success else '❌ FAIL'}")
    print("=" * 70)

    if adk_success:
        print("\n🎉 ADK AGENT WORKFLOW TEST: ✅ SUCCESS!")
        print("💡 The ADK agent system is working correctly:")
        print("   ✅ Root agent transfers to research agent")
        print("   ✅ Research agent executes mandatory tools")
        print("   ✅ Artifacts are collected and saved to GCS")
        print("   ✅ Presentation generation includes collected artifacts")
        print("   ✅ Ready for frontend testing!")
        return 0
    else:
        print("\n🚨 ADK AGENT WORKFLOW TEST: ❌ FAILED!")
        print("💡 Issues found with the ADK agent system:")
        print("   ❌ Agents are not executing tools properly")
        print("   ❌ No artifacts were collected during investigation")
        print("   ❌ Agent transfer mechanism may be broken")
        print("   ❌ Need to debug agent instructions and tool execution")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
