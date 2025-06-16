#!/usr/bin/env python3
"""
Test script for the Atlas Investigation System.
This script tests the complete 5-agent workflow end-to-end.
"""

from rag.investigation_service import investigate_alert
from rag.investigation.state_manager import AlertData, state_manager
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the investigation system


async def test_investigation_system():
    """Test the complete investigation system with a mock alert."""

    print("🚀 Starting Atlas Investigation System Test")
    print("=" * 60)

    # Create a test alert
    test_alert = AlertData(
        alert_id="TEST-2024-0003",
        event_type="Community Protest",
        location="Washington Square Park, Manhattan",
        severity=7,
        summary="Large gathering reported in Washington Square Park with residents expressing concerns about recent development projects. Social media indicates growing community organization around housing issues.",
        sources=["Reddit", "Twitter", "311 Complaints", "Community Board"],
        timestamp=datetime.utcnow()
    )

    print(f"📋 Test Alert Details:")
    print(f"   Alert ID: {test_alert.alert_id}")
    print(f"   Event: {test_alert.event_type}")
    print(f"   Location: {test_alert.location}")
    print(f"   Severity: {test_alert.severity}/10")
    print(f"   Summary: {test_alert.summary[:100]}...")
    print()

    try:
        # Run the investigation
        print("🔍 Starting Investigation...")
        investigation_result, investigation_id = await investigate_alert(test_alert)

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

        # Check investigation state
        print("🔍 Investigation State Check:")
        investigation_state = state_manager.get_investigation(investigation_id)
        if investigation_state:
            print(f"   Phase: {investigation_state.phase}")
            print(f"   Confidence: {investigation_state.confidence_score}")
            print(f"   Artifacts: {len(investigation_state.artifacts)}")
            print(f"   Iteration: {investigation_state.iteration_count}")

            # List artifacts if any
            if investigation_state.artifacts:
                print(f"   📎 Artifacts Created:")
                for artifact in investigation_state.artifacts:
                    print(f"      - {artifact}")
        print()

        return True

    except Exception as e:
        print(f"❌ Investigation Failed: {e}")
        logger.exception("Investigation failed with exception")
        return False


async def test_individual_agents():
    """Test individual agents to ensure tools are working."""

    print("🧪 Testing Individual Agents")
    print("=" * 40)

    try:
        # Test imports
        from rag.agents.research_agent import create_research_agent
        from rag.agents.data_agent import create_data_agent
        from rag.agents.analysis_agent import create_analysis_agent
        from rag.agents.report_agent import create_report_agent

        print("✅ All agent imports successful")

        # Test agent creation
        research_agent = create_research_agent()
        data_agent = create_data_agent()
        analysis_agent = create_analysis_agent()
        report_agent = create_report_agent()

        print("✅ All agents created successfully")
        print(f"   Research Agent: {len(research_agent.tools)} tools")
        print(f"   Data Agent: {len(data_agent.tools)} tools")
        print(f"   Analysis Agent: {len(analysis_agent.tools)} tools")
        print(f"   Report Agent: {len(report_agent.tools)} tools")
        print()

        return True

    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        logger.exception("Agent test failed")
        return False


async def test_tools_individually():
    """Test tools individually to ensure they work."""

    print("🔧 Testing Individual Tools")
    print("=" * 30)

    try:
        # Test research tools
        from rag.tools.research_tools import web_search_func, search_social_media_func, query_live_apis_func

        print("Testing Research Tools:")
        web_result = web_search_func(
            "NYC housing protest", ["news", "official"])
        print(f"   ✅ Web search: {len(web_result)} results")

        social_result = search_social_media_func(
            "Washington Square Park protest", "Manhattan")
        print(f"   ✅ Social media: {len(social_result)} posts")

        api_result = query_live_apis_func(
            "311", "Manhattan", {"category": "noise"})
        print(f"   ✅ Live API: {api_result['status']}")

        # Test data tools
        from rag.tools.data_tools import (
            search_knowledge_base, query_census_demographics,
            get_crime_statistics, find_similar_incidents
        )

        print("Testing Data Tools:")
        kb_result = search_knowledge_base("housing protest")
        print(f"   ✅ Knowledge base: {len(kb_result)} documents")

        census_result = query_census_demographics(
            "Manhattan", ["income", "housing"])
        print(f"   ✅ Census data: {census_result['confidence']}")

        crime_result = get_crime_statistics("Washington Square", "30d")
        print(f"   ✅ Crime stats: {crime_result['confidence']}")

        similar_result = find_similar_incidents(
            "community protest", "Manhattan")
        print(f"   ✅ Similar incidents: {len(similar_result)} found")

        # Test analysis tools
        from rag.tools.analysis_tools import (
            analyze_temporal_patterns, correlate_data_sources,
            identify_risk_factors, generate_hypotheses
        )

        print("Testing Analysis Tools:")
        temporal_result = analyze_temporal_patterns(
            [{"timestamp": "2024-12-03T14:00:00Z"}], "24h")
        print(f"   ✅ Temporal analysis: {temporal_result['confidence']}")

        correlation_result = correlate_data_sources(
            {"web": "data"}, {"census": "data"})
        print(
            f"   ✅ Correlation: {len(correlation_result['strong_correlations'])} correlations")

        risk_result = identify_risk_factors(
            {"severity": 7}, {"location": "Manhattan"})
        print(f"   ✅ Risk analysis: {risk_result['overall_risk_score']:.2f}")

        hypothesis_result = generate_hypotheses(
            {"research": "data", "demographics": "data"})
        print(f"   ✅ Hypotheses: {len(hypothesis_result)} generated")

        # Test report tools
        from rag.tools.report_tools import (
            fact_check_claims_func, assess_source_reliability_func,
            generate_confidence_scores_func
        )

        print("Testing Report Tools:")
        fact_result = fact_check_claims_func(
            ["Test claim"], [{"name": "source1"}])
        print(f"   ✅ Fact check: {fact_result['overall_confidence']:.2f}")

        reliability_result = assess_source_reliability_func(
            [{"name": "Reddit", "type": "social"}])
        print(
            f"   ✅ Source reliability: {reliability_result['average_credibility']:.2f}")

        confidence_result = generate_confidence_scores_func(
            {"analysis": "complete"})
        print(
            f"   ✅ Confidence scores: {confidence_result['overall_confidence']:.2f}")

        print()
        return True

    except Exception as e:
        print(f"❌ Tool test failed: {e}")
        logger.exception("Tool test failed")
        return False


async def main():
    """Main test function."""

    print("🏗️  NYC Atlas Investigation System - End-to-End Test")
    print("=" * 60)
    print()

    # Test individual tools
    tools_ok = await test_tools_individually()

    # Test individual agents
    agents_ok = await test_individual_agents()

    # Test full system
    system_ok = await test_investigation_system()

    print("📊 Test Summary:")
    print(f"   Tools: {'✅ PASS' if tools_ok else '❌ FAIL'}")
    print(f"   Agents: {'✅ PASS' if agents_ok else '❌ FAIL'}")
    print(f"   System: {'✅ PASS' if system_ok else '❌ FAIL'}")
    print()

    if tools_ok and agents_ok and system_ok:
        print("🎉 ALL TESTS PASSED! System ready for deployment.")
        return 0
    else:
        print("🚨 SOME TESTS FAILED! Check logs for details.")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
