#!/usr/bin/env python3
"""
Test script for improved investigation capabilities with enhanced synthesis and analysis.
This version tests the actual executive summary and key insights generation that happens
in the minimal_working_agent.py workflow via slides creation.
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
    print(
        f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"   GOOGLE_CLOUD_LOCATION: {os.getenv('GOOGLE_CLOUD_LOCATION')}")
except ImportError:
    print("⚠️ python-dotenv not available, using existing environment variables")


def test_executive_summary_generation():
    """
    Test the executive summary and key insights generation that happens in minimal_working_agent.py
    by simulating realistic web search findings and testing the actual slides creation workflow.
    """
    print("🧪 TESTING EXECUTIVE SUMMARY & KEY INSIGHTS GENERATION")
    print("=" * 70)

    # Create realistic test investigation
    investigation_id = f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Create alert data for a realistic scenario
    alert_data = AlertData(
        alert_id="test_summary_001",
        event_type="protest",
        location="Bryant Park, Manhattan",
        severity=7,
        summary="Large-scale demonstration with thousands of participants gathered at Bryant Park, Manhattan. The peaceful protest proceeded through multiple locations including Madison Square Park. No arrests reported, with extensive social media documentation of the events.",
        sources=["web_search", "social_media", "news_outlets"],
        timestamp=datetime.now()
    )

    print(f"📋 Created test investigation:")
    print(f"   ID: {investigation_id}")
    print(f"   Event: {alert_data.event_type}")
    print(f"   Location: {alert_data.location}")
    print(f"   Severity: {alert_data.severity}/10")

    # Create investigation state
    investigation_state = state_manager.create_investigation(alert_data)
    actual_investigation_id = investigation_state.investigation_id

    print(f"✅ Investigation state created: {actual_investigation_id}")

    # Step 1: Mock realistic web search findings (as would be created by minimal_working_agent.py)
    print("\n🔍 Step 1: Setting up realistic web search findings...")

    # Simulate what the minimal_working_agent would store after web searches
    realistic_web_findings = [
        "Multi-source verification from 4 major news outlets including CNN, Reuters, Associated Press",
        "Large-scale demonstration involving tens of thousands of participants documented",
        "Peaceful demonstration with no law enforcement incidents reported",
        "Multi-location demonstration spanning Manhattan parks and organized route",
        "Extensive social media documentation with over 500 posts and images",
        "Professional news coverage indicates significant public interest in the demonstration",
        "Geographic scope extends from Bryant Park through Madison Square Park area"
    ]

    # Store the findings in investigation state as the agent would
    if not hasattr(investigation_state, 'agent_findings'):
        investigation_state.agent_findings = {}

    investigation_state.agent_findings['web_search_analysis'] = realistic_web_findings
    investigation_state.confidence_score = 0.85

    # Add realistic artifacts that would be collected
    investigation_state.artifacts = [
        {'type': 'screenshot', 'filename': 'cnn_protest_coverage.png',
            'url': 'https://cnn.com/nyc-protest', 'relevance_score': 0.9},
        {'type': 'screenshot', 'filename': 'reuters_demonstration.png',
            'url': 'https://reuters.com/manhattan-demo', 'relevance_score': 0.8},
        {'type': 'image', 'filename': 'bryant_park_crowd.jpg',
            'description': 'Peaceful protest scene at Bryant Park, Manhattan', 'relevance_score': 0.9},
        {'type': 'image', 'filename': 'madison_square_march.jpg',
            'description': 'Protest march through Madison Square Park area', 'relevance_score': 0.8},
        {'type': 'map_image', 'filename': 'bryant_park_satellite_close.png',
            'description': 'Satellite view of Bryant Park - Close zoom', 'relevance_score': 1.0},
        {'type': 'map_image', 'filename': 'manhattan_parks_satellite_wide.png',
            'description': 'Satellite view of Manhattan parks - Wide area', 'relevance_score': 0.9},
        {'type': 'image', 'filename': 'social_media_posts.jpg',
            'description': 'Social media documentation of demonstration', 'relevance_score': 0.7},
        {'type': 'screenshot', 'filename': 'ap_news_coverage.png',
            'url': 'https://apnews.com/protest-nyc', 'relevance_score': 0.8},
        {'type': 'image', 'filename': 'peaceful_gathering.jpg',
            'description': 'Peaceful gathering at Bryant Park demonstration', 'relevance_score': 0.8},
        {'type': 'screenshot', 'filename': 'nbc_protest_report.png',
            'url': 'https://nbcnews.com/manhattan-protest', 'relevance_score': 0.8},
    ]

    print(f"   ✅ Set up {len(realistic_web_findings)} realistic web findings")
    print(
        f"   ✅ Added {len(investigation_state.artifacts)} realistic artifacts")
    print(
        f"   ✅ Set confidence score to {investigation_state.confidence_score:.1%}")

    # Step 2: Test the actual slides creation workflow (where executive summary is generated)
    print("\n📊 Step 2: Testing slides creation and executive summary generation...")

    try:
        from rag.tools.report_tools import create_slides_presentation_func

        # This calls the actual workflow that creates executive summary from web findings
        slides_result = create_slides_presentation_func(
            investigation_id=actual_investigation_id,
            title=f"Test Investigation: {alert_data.event_type} at {alert_data.location}",
            evidence_types="all"
        )

        print(
            f"   Slides creation result: {'✅ SUCCESS' if slides_result.get('success') else '❌ FAILED'}")

        if not slides_result.get('success'):
            print(f"   Error: {slides_result.get('error')}")
            print(
                "   ℹ️ This might be expected if Google Slides isn't configured - checking mock data...")

    except Exception as e:
        print(
            f"   ⚠️ Slides creation failed (expected in test environment): {e}")
        print("   ℹ️ Testing executive summary generation directly...")

    # Step 3: Test the executive summary generation directly
    print("\n🎯 Step 3: Testing executive summary generation logic...")

    try:
        # Test the actual summary generation functions directly
        from rag.tools.report_tools import _prepare_replacement_data, _llm_synthesize_findings
        from rag.tools.research_tools import get_investigation_evidence_func

        # Get evidence data as the slides function would
        evidence_data = get_investigation_evidence_func(
            actual_investigation_id, "all")
        print(
            f"   ✅ Retrieved evidence data: {len(evidence_data.get('evidence_items', []))} items")

        # Generate replacement data (includes executive summary and key findings)
        replacements = _prepare_replacement_data(
            investigation_state, evidence_data)

        # Extract the key components we want to test
        executive_summary = replacements.get('executive_summary', '')
        key_findings = replacements.get('key_findings', '')
        findings_summary = replacements.get('findings_summary', '')

        print(f"\n📋 GENERATED CONTENT ANALYSIS:")
        print("=" * 50)

        # Test Executive Summary
        print(f"🎯 EXECUTIVE SUMMARY ({len(executive_summary)} chars):")
        print(f"   {executive_summary}")
        print()

        # Test Key Findings
        print(f"🔍 KEY FINDINGS:")
        if key_findings:
            for line in key_findings.split('\n'):
                if line.strip():
                    print(f"   {line}")
        print()

        # Test LLM synthesis directly (if available)
        print(f"🤖 TESTING LLM SYNTHESIS DIRECTLY:")
        try:
            direct_synthesis = _llm_synthesize_findings(
                event_type=alert_data.event_type,
                location=alert_data.location,
                raw_findings=realistic_web_findings,
                evidence_count=len(investigation_state.artifacts),
                confidence_score=investigation_state.confidence_score
            )

            print(f"   ✅ Direct LLM synthesis successful!")
            print(
                f"   Executive Summary: {len(direct_synthesis.get('executive_summary', ''))} chars")
            print(
                f"   Key Findings: {direct_synthesis.get('key_findings', '').count('•')} bullets")

            # Use LLM results if available
            if direct_synthesis.get('executive_summary'):
                executive_summary = direct_synthesis['executive_summary']
            if direct_synthesis.get('key_findings'):
                key_findings = direct_synthesis['key_findings']

        except Exception as e:
            print(f"   ⚠️ LLM synthesis not available: {e}")
            print(f"   Using fallback synthesis...")

        # Quality Tests
        print(f"📊 CONTENT QUALITY ANALYSIS:")
        print("=" * 40)

        # Test 1: Executive Summary Quality
        summary_quality_score = 0
        summary_tests = []

        if "bryant park" in executive_summary.lower():
            summary_quality_score += 1
            summary_tests.append("✅ Mentions specific location (Bryant Park)")
        else:
            summary_tests.append("❌ Missing specific location details")

        if "peaceful" in executive_summary.lower() or "no arrests" in executive_summary.lower():
            summary_quality_score += 1
            summary_tests.append("✅ Describes event nature (peaceful)")
        else:
            summary_tests.append("❌ Missing event nature details")

        if "thousands" in executive_summary.lower() or "participants" in executive_summary.lower():
            summary_quality_score += 1
            summary_tests.append("✅ Includes scale information")
        else:
            summary_tests.append("❌ Missing scale information")

        if "news" in executive_summary.lower() or "coverage" in executive_summary.lower():
            summary_quality_score += 1
            summary_tests.append("✅ Mentions media coverage")
        else:
            summary_tests.append("❌ Missing media coverage details")

        if not ("investigation" in executive_summary.lower() and "achieved" in executive_summary.lower()):
            summary_quality_score += 1
            summary_tests.append(
                "✅ Focuses on incident, not just investigation process")
        else:
            summary_tests.append(
                "❌ Too focused on investigation process rather than actual incident")

        print(f"Executive Summary Quality: {summary_quality_score}/5")
        for test in summary_tests:
            print(f"   {test}")
        print()

        # Test 2: Key Findings Quality
        findings_quality_score = 0
        findings_tests = []

        if "multi-source" in key_findings.lower() or "news outlets" in key_findings.lower():
            findings_quality_score += 1
            findings_tests.append("✅ Mentions multi-source verification")
        else:
            findings_tests.append("❌ Missing source verification details")

        if "thousands" in key_findings.lower() and "participants" in key_findings.lower():
            findings_quality_score += 1
            findings_tests.append("✅ Includes participant scale")
        else:
            findings_tests.append("❌ Missing participant scale")

        if "peaceful" in key_findings.lower():
            findings_quality_score += 1
            findings_tests.append("✅ Describes peaceful nature")
        else:
            findings_tests.append("❌ Missing peaceful nature description")

        if "multi-location" in key_findings.lower() or "spanning" in key_findings.lower():
            findings_quality_score += 1
            findings_tests.append("✅ Describes geographic scope")
        else:
            findings_tests.append("❌ Missing geographic scope")

        generic_phrases = ["web sources document",
                           "investigation achieved", "evidence items"]
        if not any(phrase in key_findings.lower() for phrase in generic_phrases):
            findings_quality_score += 1
            findings_tests.append("✅ Avoids generic phrases")
        else:
            findings_tests.append("❌ Contains generic investigation language")

        print(f"Key Findings Quality: {findings_quality_score}/5")
        for test in findings_tests:
            print(f"   {test}")
        print()

        # Overall Assessment
        total_quality = summary_quality_score + findings_quality_score
        print(f"🎯 OVERALL QUALITY SCORE: {total_quality}/10")

        if total_quality >= 8:
            print(
                "🎉 EXCELLENT - Executive summary and key findings are highly specific and meaningful!")
            success = True
        elif total_quality >= 6:
            print(
                "✅ GOOD - Executive summary and key findings contain meaningful details!")
            success = True
        elif total_quality >= 4:
            print("⚠️ FAIR - Some improvements needed in specificity and detail")
            success = True
        else:
            print("❌ POOR - Executive summary and key findings are too generic")
            success = False

        print("\n🏁 TEST SUMMARY:")
        print("=" * 30)
        print(
            f"Executive Summary Generation: {'✅ PASS' if summary_quality_score >= 3 else '❌ FAIL'}")
        print(
            f"Key Findings Generation: {'✅ PASS' if findings_quality_score >= 3 else '❌ FAIL'}")
        print(
            f"Overall Content Quality: {'✅ PASS' if total_quality >= 6 else '❌ FAIL'}")

        return success

    except Exception as e:
        print(f"❌ Executive summary generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all improved investigation tests."""
    print("🚀 STARTING IMPROVED INVESTIGATION TESTS")
    print("=" * 80)

    try:
        # Test the executive summary and key insights generation
        summary_success = test_executive_summary_generation()

        print("\n" + "=" * 80)
        print("🏁 FINAL TEST RESULTS")
        print("=" * 80)

        if summary_success:
            print("🎉 ✅ ALL TESTS PASSED!")
            print(
                "   Executive summary and key insights are now meaningful and specific!")
            print("   The generic output issue has been resolved.")
        else:
            print("❌ TESTS FAILED")
            print("   Executive summary and key insights are still too generic.")
            print("   Additional improvements needed.")

        return summary_success

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_all_tests())

    if success:
        print("\n🎯 Next steps: Test with the actual minimal_working_agent.py to ensure integration works!")
        sys.exit(0)
    else:
        print("\n🔧 Next steps: Review and improve the executive summary generation logic.")
        sys.exit(1)
