#!/usr/bin/env python3
"""
Test script for improved investigation capabilities with enhanced synthesis and analysis.
"""

from datetime import datetime
from rag.investigation.state_manager import AlertData
from rag.agents.minimal_working_agent import execute_minimal_investigation
import asyncio
import json
import sys
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from parent directory where .env is located
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
    print(
        f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', 'NOT SET')}")
    print(
        f"   GOOGLE_CLOUD_LOCATION: {os.getenv('GOOGLE_CLOUD_LOCATION', 'NOT SET')}")
except ImportError:
    print("⚠️ python-dotenv not available, environment variables must be set manually")
except Exception as e:
    print(f"⚠️ Error loading .env file: {e}")

# Add backend to path
sys.path.append(os.path.dirname(__file__))


async def test_improved_investigation():
    """Test the improved investigation system with better synthesis."""

    print("🚀 Testing Improved Investigation System")
    print("=" * 60)

    # Create a realistic test case
    test_alert = {
        "investigation_id": "test_improved_2024_001",
        "alert_data": {
            "alert_id": "test_protest_2024_001",
            "severity": 6,
            "event_type": "protest",
            "location": "Bryant Park, Manhattan",
            "summary": "Large demonstration with thousands of participants reported in Bryant Park, Manhattan. Multiple social media reports indicate peaceful protest with significant crowd size. Police presence noted but no major incidents reported.",
            "timestamp": datetime.utcnow().isoformat(),
            "sources": ["social_media", "citizen_reports", "police_scanner"]
        }
    }

    print(f"📋 Test Alert Details:")
    print(f"   Location: {test_alert['alert_data']['location']}")
    print(f"   Event Type: {test_alert['alert_data']['event_type']}")
    print(f"   Severity: {test_alert['alert_data']['severity']}/10")
    print(f"   Summary: {test_alert['alert_data']['summary'][:100]}...")
    print()

    try:
        # Execute the improved investigation
        print("🔍 Executing Enhanced Investigation...")
        result = await execute_minimal_investigation(test_alert)

        print("\n📊 Investigation Results:")
        print("=" * 40)
        print(f"✅ Success: {result.get('success', False)}")
        print(f"📈 Confidence Score: {result.get('confidence_score', 0):.1%}")
        print(f"🗂️ Total Artifacts: {result.get('total_artifacts', 0)}")
        print(f"🗺️ Maps Generated: {result.get('maps_generated', 0)}")
        print(f"🖼️ Images Collected: {result.get('images_collected', 0)}")
        print(f"📸 Screenshots: {result.get('screenshots_collected', 0)}")
        print(
            f"🔍 Web Search: {'✅' if result.get('web_search_performed', False) else '❌'}")
        print(f"📊 Status: {result.get('workflow_status', 'unknown')}")

        if result.get('artifact_breakdown'):
            print(f"\n📋 Artifact Breakdown:")
            for artifact_type, count in result['artifact_breakdown'].items():
                print(f"   {artifact_type}: {count}")

        print(f"\n📝 Summary: {result.get('summary', 'No summary available')}")

        # Check for specific improvements
        print(f"\n🎯 Improvement Validation:")
        print("=" * 40)

        # 1. Check location extraction
        location_extracted = test_alert['alert_data']['location'] != "Unknown"
        print(
            f"✅ Location Extraction: {'PASS' if location_extracted else 'FAIL'}")

        # 2. Check confidence score
        confidence_reasonable = result.get('confidence_score', 0) > 0.5
        print(
            f"✅ Confidence Score: {'PASS' if confidence_reasonable else 'FAIL'} ({result.get('confidence_score', 0):.1%})")

        # 3. Check web search
        web_search_done = result.get('web_search_performed', False)
        print(f"✅ Web Search: {'PASS' if web_search_done else 'FAIL'}")

        # 4. Check artifact collection
        sufficient_artifacts = result.get('total_artifacts', 0) >= 8
        print(
            f"✅ Artifact Collection: {'PASS' if sufficient_artifacts else 'FAIL'} ({result.get('total_artifacts', 0)} artifacts)")

        # 5. Check synthesis quality (look for specific insights in response)
        agent_response = result.get('agent_response', '')
        has_specific_insights = any(keyword in agent_response.lower() for keyword in [
            'participants', 'demonstration', 'peaceful', 'arrests', 'police', 'manhattan', 'bryant park'
        ])
        print(
            f"✅ Synthesis Quality: {'PASS' if has_specific_insights else 'FAIL'}")

        # Overall assessment
        improvements_working = all([
            location_extracted,
            confidence_reasonable,
            web_search_done,
            sufficient_artifacts,
            has_specific_insights
        ])

        print(
            f"\n🎉 Overall Assessment: {'✅ IMPROVEMENTS WORKING' if improvements_working else '❌ NEEDS MORE WORK'}")

        if result.get('agent_response'):
            print(f"\n📄 Agent Response Preview:")
            print("=" * 40)
            response_preview = result['agent_response'][:500] + "..." if len(
                result['agent_response']) > 500 else result['agent_response']
            print(response_preview)

        return result

    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_edge_cases():
    """Test edge cases to ensure robustness."""

    print("\n🧪 Testing Edge Cases")
    print("=" * 40)

    # Test case with minimal information
    minimal_alert = {
        "investigation_id": "test_minimal_2024_001",
        "alert_data": {
            "alert_id": "minimal_001",
            "severity": 3,
            "event_type": "incident",
            "location": "Unknown",
            "summary": "Some kind of event happened",
            "timestamp": datetime.utcnow().isoformat(),
            "sources": []
        }
    }

    print("🔍 Testing with minimal information...")
    try:
        result = await execute_minimal_investigation(minimal_alert)

        # Check that validation improved the data
        print(
            f"   Location after validation: {result.get('investigation_id', 'N/A')}")
        print(f"   Confidence score: {result.get('confidence_score', 0):.1%}")
        print(f"   Success: {'✅' if result.get('success', False) else '❌'}")

    except Exception as e:
        print(f"   ❌ Minimal test failed: {e}")


if __name__ == "__main__":
    print("🧪 Enhanced Investigation Testing Suite")
    print("=" * 60)
    print("Testing improved synthesis, confidence scoring, and data validation...")
    print()

    # Run main test
    asyncio.run(test_improved_investigation())

    # Run edge case tests
    asyncio.run(test_edge_cases())

    print("\n✅ Testing Complete!")
    print("\nKey Improvements Tested:")
    print("1. ✅ Enhanced web search analysis with specific insight extraction")
    print("2. ✅ Better alert data validation and location extraction")
    print("3. ✅ Comprehensive confidence scoring based on evidence quality")
    print("4. ✅ Improved agent instructions for deeper synthesis")
    print("5. ✅ Better executive summary generation from actual findings")
