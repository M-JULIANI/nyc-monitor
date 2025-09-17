#!/usr/bin/env python3
"""
Test script for improved LLM synthesis capabilities.
This version focuses specifically on testing the LLM synthesis that converts 
web search results into meaningful executive summaries and key findings.
"""

from datetime import datetime
from rag.investigation.state_manager import AlertData, state_manager
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
    print(f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"   GOOGLE_CLOUD_LOCATION: {os.getenv('GOOGLE_CLOUD_LOCATION')}")
except ImportError:
    print("⚠️ python-dotenv not available, using existing environment variables")


def create_test_investigation_with_findings(investigation_id: str, event_type: str, location: str, raw_findings: list):
    """Create a test investigation with web search findings for synthesis testing."""
    from rag.investigation.state_manager import AlertData, state_manager
    from datetime import datetime

    # Create alert data
    alert_data = AlertData(
        alert_id=f"test_alert_{investigation_id}",
        severity=7,
        event_type=event_type,
        location=location,
        summary=f"Test {event_type} at {location} for synthesis testing",
        timestamp=datetime.now(),
        sources=["test"]
    )

    # Create investigation using the correct method signature
    investigation_state = state_manager.create_investigation(alert_data)

    # Manually override the investigation_id if needed for testing
    original_id = investigation_state.investigation_id
    investigation_state.investigation_id = investigation_id

    # Update the state manager's registry with the new ID
    state_manager.investigations[investigation_id] = investigation_state
    # Remove the old ID if different
    if original_id != investigation_id and original_id in state_manager.investigations:
        del state_manager.investigations[original_id]

    # Add web search findings to agent_findings
    investigation_state.agent_findings = {
        f"web_search_{event_type.replace(' ', '_')}": raw_findings
    }

    # Add some test artifacts
    investigation_state.artifacts = [
        {
            "type": "image",
            "description": f"Visual evidence of {event_type} at {location}",
            "relevance_score": 0.8
        },
        {
            "type": "screenshot",
            "description": f"News coverage of {event_type}",
            "relevance_score": 0.9
        }
    ]

    investigation_state.confidence_score = 0.85

    return investigation_state


def test_llm_synthesis_direct():
    """
    Test the LLM synthesis function directly with realistic web search findings.
    This tests ONLY the synthesis generation from web search results.
    """
    print("🧪 TESTING LLM SYNTHESIS GENERATION DIRECTLY")
    print("=" * 70)

    # Import the new dedicated synthesis tool
    try:
        from rag.tools.analysis_tools import synthesize_investigation_findings_func
        print("✅ Imported dedicated synthesis tool")
    except ImportError as e:
        print(f"❌ Failed to import synthesis tool: {e}")
        assert False, f"Failed to import synthesis tool: {e}"

    # Test data - realistic web search findings like the agent would collect
    test_scenarios = [
        {
            "name": "Bryant Park Protest",
            "event_type": "protest",
            "location": "Bryant Park, Manhattan",
            "web_findings": [
                "CNN reports large-scale demonstration at Bryant Park with estimated 15,000 participants",
                "Reuters documents peaceful protest march from Bryant Park to Madison Square Park",
                "Associated Press confirms no arrests during 4-hour demonstration",
                "NBC New York shows extensive social media coverage with #BryantParkProtest trending",
                "NYPD statement indicates cooperative event with proper permits",
                "Local witnesses describe orderly crowd with organized route through Manhattan",
                "Multiple news sources verify demonstration focused on housing policy reforms"
            ],
            "expected_keywords": ["15,000", "peaceful", "permits", "housing policy", "bryant park", "madison square"]
        },
        {
            "name": "Manhattan Bridge Infrastructure",
            "event_type": "infrastructure_failure",
            "location": "Manhattan Bridge",
            "web_findings": [
                "DOT reports structural inspection revealing cable wear on Manhattan Bridge south side",
                "Traffic restrictions implemented on lower level during peak hours",
                "Engineering assessment shows 40-year-old cables require immediate attention",
                "NYC Department of Transportation schedules 6-month repair timeline",
                "Bridge remains safe for pedestrian and vehicle traffic with monitoring",
                "Historical maintenance records show last major cable work in 1998",
                "Public works announcement indicates $12 million repair budget allocated"
            ],
            "expected_keywords": ["cable wear", "40-year-old", "6-month repair", "$12 million", "1998", "inspection"]
        }
    ]

    # Test the LLM synthesis function for each scenario
    from rag.tools.report_tools import _llm_synthesize_findings

    all_tests_passed = True

    for i, scenario in enumerate(test_scenarios, 1):
        print(f" TEST SCENARIO {i}: {scenario['name']}")
        print("=" * 50)

        # Create test investigation first
        investigation_id = f"test_synthesis_{scenario['name'].lower().replace(' ', '_')}"
        investigation_state = create_test_investigation_with_findings(
            investigation_id, scenario["event_type"], scenario["location"], scenario["web_findings"]
        )

        # Use the new dedicated synthesis tool
        synthesis_result = synthesize_investigation_findings_func(
            investigation_id=investigation_id,
            event_type=scenario["event_type"],
            location=scenario["location"],
            synthesis_focus="executive_summary,key_findings"
        )

        if synthesis_result.get("success"):
            synthesis_data = synthesis_result.get("synthesis", {})
            executive_summary = synthesis_data.get("executive_summary", "")
            key_findings = synthesis_data.get("key_findings", "")
        else:
            print(
                f"❌ Synthesis failed: {synthesis_result.get('error', 'Unknown error')}")
            executive_summary = ""
            key_findings = ""

        print(f"📋 GENERATED CONTENT:")
        print(f"Executive Summary ({len(executive_summary)} chars):")
        print(f"   {executive_summary}")
        print()
        print(f"Key Findings:")
        for line in key_findings.split('\n'):
            if line.strip():
                print(f"   {line}")
        print()

        # Quality assessment
        quality_score = 0
        quality_tests = []

        # Check for specific details from web findings
        for keyword in scenario["expected_keywords"]:
            content = (executive_summary + " " + key_findings).lower()
            if keyword.lower() in content:
                quality_score += 1
                quality_tests.append(
                    f"✅ Contains specific detail: '{keyword}'")
            else:
                quality_tests.append(
                    f"❌ Missing specific detail: '{keyword}'")

        # Check for non-generic content
        generic_phrases = ["investigation completed",
                           "evidence collected", "analysis shows"]
        generic_found = any(phrase in (
            executive_summary + key_findings).lower() for phrase in generic_phrases)
        if not generic_found:
            quality_score += 2
            quality_tests.append("✅ Avoids generic investigation language")
        else:
            quality_tests.append(
                "❌ Contains generic investigation language")

        # Check content length and substance
        if len(executive_summary) > 100 and len(key_findings) > 150:
            quality_score += 1
            quality_tests.append("✅ Generated substantial content")
        else:
            quality_tests.append("❌ Content too brief")

        # Check for event-specific language
        if scenario["event_type"] in (executive_summary + key_findings).lower():
            quality_score += 1
            quality_tests.append(
                f"✅ Uses event-specific language: '{scenario['event_type']}'")
        else:
            quality_tests.append(
                f"❌ Missing event-specific language: '{scenario['event_type']}'")

        # keywords + generic + length + event-specific
        max_score = len(scenario["expected_keywords"]) + 3
        percentage = (quality_score / max_score) * 100

        print(
            f"📊 QUALITY ASSESSMENT: {quality_score}/{max_score} ({percentage:.1f}%)")
        for test in quality_tests:
            print(f"   {test}")

        # Test passes if it gets more than 60% quality score
        test_passed = percentage >= 60
        print(f"🎯 TEST RESULT: {'✅ PASS' if test_passed else '❌ FAIL'}")

        if not test_passed:
            all_tests_passed = False

    # Final assessment
    print(f"\n🏁 OVERALL TEST RESULTS")
    print("=" * 50)

    if all_tests_passed:
        print("🎉 ✅ ALL LLM SYNTHESIS TESTS PASSED!")
        print("   The synthesis is generating specific, meaningful content from web search results.")
        print("   Generic output issue is resolved.")
    else:
        print("❌ LLM SYNTHESIS TESTS FAILED")
        print("   The synthesis is still producing generic or incomplete content.")
        print("   Additional improvements needed in the LLM synthesis logic.")

    assert all_tests_passed, "LLM synthesis tests failed"


def test_web_search_to_synthesis_integration():
    """
    Test the full integration from web search collection to final synthesis.
    This simulates the complete flow that minimal_working_agent.py uses.
    """
    print("\n🔗 TESTING WEB SEARCH TO SYNTHESIS INTEGRATION")
    print("=" * 70)

    # Import the dedicated synthesis tool
    from rag.tools.analysis_tools import synthesize_investigation_findings_func

    # Create a test investigation
    investigation_id = f"test_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    alert_data = AlertData(
        alert_id="test_integration_001",
        event_type="protest",
        location="Union Square, Manhattan",
        severity=6,
        summary="Large demonstration at Union Square with thousands of participants and significant media coverage.",
        sources=["test_framework"],
        timestamp=datetime.now()
    )

    print(f"📋 Created test investigation: {investigation_id}")
    print(f"   Event: {alert_data.event_type} at {alert_data.location}")

    # Create investigation state
    investigation_state = state_manager.create_investigation(alert_data)
    actual_investigation_id = investigation_state.investigation_id

    # Simulate web search findings being stored (as minimal_working_agent would do)
    if not hasattr(investigation_state, 'agent_findings'):
        investigation_state.agent_findings = {}

    # Realistic web search findings
    web_findings = [
        "ABC News reports 8,000 participants at Union Square demonstration for labor rights",
        "New York Times coverage shows peaceful march from Union Square to Washington Square Park",
        "Twitter trending with #UnionSquareRally hashtag gaining 50K mentions in 2 hours",
        "NYPD confirms advance coordination with organizers and no incidents reported",
        "Local business owners report normal operations with minor traffic delays",
        "Event organizers from Labor Coalition announce successful turnout exceeding expectations"
    ]

    investigation_state.agent_findings['web_search_analysis'] = web_findings
    investigation_state.confidence_score = 0.80

    # Add some realistic artifacts
    investigation_state.artifacts = [
        {'type': 'screenshot', 'filename': 'abc_news_coverage.png',
            'relevance_score': 0.9},
        {'type': 'screenshot', 'filename': 'nytimes_article.png', 'relevance_score': 0.8},
        {'type': 'image', 'filename': 'union_square_crowd.jpg', 'relevance_score': 0.9},
        {'type': 'map_image', 'filename': 'union_square_satellite.png',
            'relevance_score': 1.0},
    ]

    print(
        f"✅ Set up investigation with {len(web_findings)} web findings and {len(investigation_state.artifacts)} artifacts")

    # Test synthesis of web search findings using new tool
    try:
        synthesis_result = synthesize_investigation_findings_func(
            investigation_id=investigation_id,
            event_type="protest",
            location="Union Square, Manhattan",
            synthesis_focus="executive_summary,key_findings"
        )

        if synthesis_result.get("success"):
            synthesis_data = synthesis_result.get("synthesis", {})
            executive_summary = synthesis_data.get("executive_summary", "")
            key_findings = synthesis_data.get("key_findings", "")
            synthesis_method = synthesis_result.get(
                "synthesis_method", "unknown")

            print(f"\n📊 INTEGRATION RESULTS:")
            print(f"Executive Summary ({len(executive_summary)} chars):")
            print(f"   {executive_summary}")
            print(f"\nKey Findings:")
            print(f"   {key_findings}")
            print(f"\nSynthesis Method: {synthesis_method}")

            # Test integration quality
            integration_score = 0
            integration_tests = []

            # Should contain specific details from web findings
            specific_details = ["8,000", "labor rights",
                                "union square", "washington square", "nypd", "peaceful"]
            for detail in specific_details:
                content = (executive_summary + " " + key_findings).lower()
                if detail.lower() in content:
                    integration_score += 1
                    integration_tests.append(
                        f"✅ Integrated specific detail: '{detail}'")
                else:
                    integration_tests.append(
                        f"❌ Missing integration of: '{detail}'")

            # Should reference the investigation findings appropriately
            if "demonstration" in (executive_summary + key_findings).lower():
                integration_score += 1
                integration_tests.append(
                    "✅ Uses appropriate event terminology")
            else:
                integration_tests.append(
                    "❌ Missing appropriate event terminology")

            # Should not be purely generic
            if not ("investigation completed" in (executive_summary + key_findings).lower() and
                    "evidence collected" in (executive_summary + key_findings).lower()):
                integration_score += 1
                integration_tests.append("✅ Avoids purely generic content")
            else:
                integration_tests.append(
                    "❌ Contains generic investigation language")

            max_integration_score = len(specific_details) + 2
            integration_percentage = (
                integration_score / max_integration_score) * 100

            print(
                f"\n📊 INTEGRATION QUALITY: {integration_score}/{max_integration_score} ({integration_percentage:.1f}%)")
            for test in integration_tests:
                print(f"   {test}")

            integration_success = integration_percentage >= 70
            print(
                f"🎯 INTEGRATION TEST: {'✅ PASS' if integration_success else '❌ FAIL'}")

            assert integration_success, "Integration test failed"

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        assert False, f"Integration test failed: {e}"


async def run_all_tests():
    """Run all synthesis improvement tests."""
    print("🚀 STARTING LLM SYNTHESIS IMPROVEMENT TESTS")
    print("=" * 80)

    try:
        # Test LLM synthesis directly
        direct_synthesis_success = test_llm_synthesis_direct()

        # Test web search to synthesis integration
        integration_success = test_web_search_to_synthesis_integration()

        print("\n" + "=" * 80)
        print("🏁 FINAL TEST RESULTS")
        print("=" * 80)

        overall_success = direct_synthesis_success and integration_success

        if overall_success:
            print("🎉 ✅ ALL TESTS PASSED!")
            print("   LLM synthesis is generating meaningful, specific content!")
            print("   The generic output issue has been resolved.")
        else:
            print("❌ TESTS FAILED")
            if not direct_synthesis_success:
                print("   Direct LLM synthesis needs improvement")
            if not integration_success:
                print("   Web search to synthesis integration needs improvement")

        return overall_success

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_all_tests())

    if success:
        print("\n🎯 Next steps: The synthesis generation is working correctly!")
        print("   You can now test with minimal_working_agent.py for full integration.")
        sys.exit(0)
    else:
        print("\n🔧 Next steps: Review and improve the LLM synthesis logic.")
        print("   Focus on _llm_synthesize_findings() and _fallback_synthesis() functions.")
        sys.exit(1)
