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


async def test_investigation_system_with_tracing():
    """Test the complete investigation system with detailed tracing."""

    print("\n🚀 Starting Atlas Investigation System Test WITH DETAILED TRACING")
    print("=" * 80)

    # Create a test alert
    test_alert = AlertData(
        alert_id="TRACE-TEST-2024-001",
        event_type="Community Protest",
        location="Washington Square Park, Manhattan",
        severity=7,
        summary="Large gathering reported in Washington Square Park with residents expressing concerns about recent development projects. Social media indicates growing community organization around housing issues.",
        sources=["Reddit", "Twitter", "311 Complaints", "Community Board"],
        timestamp=datetime.utcnow()
    )

    print(f"\n📋 Test Alert Details:")
    print(f"   Alert ID: {test_alert.alert_id}")
    print(f"   Event: {test_alert.event_type}")
    print(f"   Location: {test_alert.location}")
    print(f"   Severity: {test_alert.severity}/10")
    print(f"   Summary: {test_alert.summary[:100]}...")
    print()

    try:
        print("🔍 Starting Investigation with Enhanced Tracing...")
        print("=" * 60)

        # Run the investigation
        investigation_result, investigation_id = await investigate_alert(test_alert)

        print("=" * 60)
        print(f"✅ Investigation Complete!")
        print(f"   Investigation ID: {investigation_id}")
        print(f"   Result Length: {len(investigation_result)} characters")
        print()

        # Print the results
        print("📊 Investigation Results:")
        print("-" * 40)
        print(investigation_result)
        print("-" * 40)
        print()

        # Detailed investigation state inspection
        print("🔍 Detailed Investigation State:")
        investigation_state = state_manager.get_investigation(investigation_id)
        if investigation_state:
            print(
                f"   📋 Investigation ID: {investigation_state.investigation_id}")
            print(f"   🎯 Phase: {investigation_state.phase}")
            print(f"   📊 Confidence: {investigation_state.confidence_score}")
            print(f"   🔄 Iteration: {investigation_state.iteration_count}")
            print(f"   📁 Artifacts: {len(investigation_state.artifacts)}")
            print(f"   ⏱️  Started: {investigation_state.start_time}")
            print(f"   📝 Findings: {len(investigation_state.findings)} items")

            # Show artifacts if any
            if investigation_state.artifacts:
                print(f"\n   📎 Artifacts Created:")
                for i, artifact in enumerate(investigation_state.artifacts, 1):
                    print(f"      {i}. {artifact}")

            # Show findings summary
            if investigation_state.findings:
                print(f"\n   📄 Recent Findings:")
                # Show last 3
                for i, finding in enumerate(investigation_state.findings[-3:], 1):
                    print(f"      {i}. {finding}")

        else:
            print("   ❌ No investigation state found")

        print()
        return True

    except Exception as e:
        print(f"❌ Investigation Failed: {e}")
        logger.exception("Investigation failed with exception")
        return False


async def trace_individual_tool_calls():
    """Test individual tools with detailed tracing to see what each one does."""

    print("\n🔧 Tracing Individual Tool Calls")
    print("=" * 50)

    try:
        # Test a research tool with tracing
        from rag.tools.research_tools import web_search_func

        print("\n🌐 Tracing Web Search Tool:")
        print("-" * 30)
        result = web_search_func(
            "NYC housing protest Washington Square Park", "news,official")
        print(f"📤 Tool Result: {json.dumps(result, indent=2)}")

        # Test a data tool
        from rag.tools.data_tools import search_knowledge_base

        print("\n📚 Tracing Knowledge Base Search:")
        print("-" * 35)
        result = search_knowledge_base("community organizing Manhattan")
        print(f"📤 Tool Result: {json.dumps(result, indent=2)}")

        # Test an analysis tool
        from rag.tools.analysis_tools import analyze_temporal_patterns

        print("\n📊 Tracing Temporal Analysis:")
        print("-" * 30)
        test_events = [
            {"timestamp": "2024-12-03T14:00:00Z", "type": "social_media_post"},
            {"timestamp": "2024-12-03T15:30:00Z", "type": "311_complaint"},
            {"timestamp": "2024-12-03T16:00:00Z", "type": "news_article"}
        ]
        result = analyze_temporal_patterns(test_events, "24h")
        print(f"📤 Tool Result: {json.dumps(result, indent=2)}")

        return True

    except Exception as e:
        print(f"❌ Tool tracing failed: {e}")
        logger.exception("Tool tracing failed")
        return False


async def main():
    """Main test function with enhanced tracing."""

    print("🏗️  NYC Atlas Investigation System - DETAILED TRACING MODE")
    print("=" * 70)
    print("This mode provides detailed logs of:")
    print("  • Agent creation and tool assignments")
    print("  • Tool function calls and results")
    print("  • Investigation state transitions")
    print("  • Multi-agent coordination")
    print("  • Error handling and fallbacks")
    print("=" * 70)

    # Trace individual tool calls first
    tools_trace = await trace_individual_tool_calls()

    # Test full system with tracing
    system_trace = await test_investigation_system_with_tracing()

    print("\n" + "=" * 70)
    print("📊 TRACING SUMMARY:")
    print(f"   Tool Tracing: {'✅ PASS' if tools_trace else '❌ FAIL'}")
    print(f"   System Tracing: {'✅ PASS' if system_trace else '❌ FAIL'}")
    print("=" * 70)

    if tools_trace and system_trace:
        print("\n🎉 TRACING COMPLETE! Check the detailed logs above.")
        print("💡 As you replace stubs with real implementations, run this script")
        print("   to see exactly how each tool and agent behaves.")
        return 0
    else:
        print("\n🚨 TRACING FAILED! Check logs for details.")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
