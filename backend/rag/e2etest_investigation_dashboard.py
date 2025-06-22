#!/usr/bin/env python3
"""
Test Investigation System with Real-time Dashboard
This provides the best tracing experience for iterating on the multi-agent system.
"""

import asyncio
from datetime import datetime
from rag.investigation.state_manager import AlertData
from rag.investigation_dashboard import run_investigation_with_dashboard, dashboard


async def test_with_dashboard():
    """Test the investigation system with full dashboard monitoring"""

    print("🎯 NYC Atlas Investigation - DASHBOARD MODE")
    print("=" * 60)
    print("🔍 This mode gives you complete visibility into:")
    print("   • Each agent's startup and tool assignment")
    print("   • Every tool call with parameters and results")
    print("   • State transitions and progress updates")
    print("   • Error handling and fallback mechanisms")
    print("   • Agent coordination and handoffs")
    print("=" * 60)

    # Create test alert
    test_alert = AlertData(
        alert_id="DASHBOARD-TEST-001",
        event_type="Community Gathering",
        location="Washington Square Park, Manhattan",
        severity=6,
        summary="Community meeting regarding proposed housing development. Reports of organized groups gathering with signs and speakers. Some concerns about potential for larger demonstration.",
        sources=["Reddit posts", "Twitter mentions",
                 "311 noise complaints", "Community board reports"],
        timestamp=datetime.utcnow()
    )

    print(f"\n📋 TEST ALERT:")
    print(f"   ID: {test_alert.alert_id}")
    print(f"   Type: {test_alert.event_type}")
    print(f"   Location: {test_alert.location}")
    print(f"   Severity: {test_alert.severity}/10")
    print(f"   Sources: {', '.join(test_alert.sources)}")
    print()

    try:
        # Run investigation with dashboard
        result, investigation_id = await run_investigation_with_dashboard(test_alert)

        print(f"\n🎉 INVESTIGATION COMPLETE!")
        print(f"📋 Investigation ID: {investigation_id}")
        print(f"📄 Report Length: {len(result)} characters")
        print()

        # Show final result
        print("📊 FINAL INVESTIGATION REPORT:")
        print("=" * 50)
        print(result)
        print("=" * 50)

        return True

    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        return False


async def test_individual_agent_tracing():
    """Test individual agents with detailed tracing"""

    print("\n🤖 INDIVIDUAL AGENT TRACING")
    print("=" * 40)

    try:
        # Test each agent individually with dashboard monitoring
        from rag.agents.research_agent import create_research_agent
        from rag.agents.data_agent import create_data_agent
        from rag.agents.analysis_agent import create_analysis_agent
        from rag.agents.report_agent import create_report_agent

        dashboard.log_event('agent_start', 'Test System',
                            message="Testing individual agent creation")

        # Create agents and show their configuration
        print("\n🔬 Creating and Inspecting Agents:")

        research_agent = create_research_agent()
        dashboard.log_event('completion', 'Research Agent',
                            message=f"Agent created with {len(research_agent.tools)} tools")
        print(
            f"   ✅ Research Agent: {len(research_agent.tools)} tools configured")

        data_agent = create_data_agent()
        dashboard.log_event('completion', 'Data Agent',
                            message=f"Agent created with {len(data_agent.tools)} tools")
        print(f"   ✅ Data Agent: {len(data_agent.tools)} tools configured")

        analysis_agent = create_analysis_agent()
        dashboard.log_event('completion', 'Analysis Agent',
                            message=f"Agent created with {len(analysis_agent.tools)} tools")
        print(
            f"   ✅ Analysis Agent: {len(analysis_agent.tools)} tools configured")

        report_agent = create_report_agent()
        dashboard.log_event('completion', 'Report Agent',
                            message=f"Agent created with {len(report_agent.tools)} tools")
        print(f"   ✅ Report Agent: {len(report_agent.tools)} tools configured")

        # Test a simple tool call
        from rag.tools.research_tools import web_search_func
        dashboard.log_event('tool_call', 'Research Agent', 'web_search',
                            message="Testing web search tool")
        result = web_search_func("NYC community meeting", ["news"])
        dashboard.log_event('completion', 'Research Agent', 'web_search',
                            message=f"Web search returned {len(result)} results")

        return True

    except Exception as e:
        dashboard.log_event('error', 'Test System',
                            message=f"Agent testing failed: {e}")
        print(f"❌ Agent testing failed: {e}")
        return False


async def main():
    """Main function for dashboard testing"""

    # Run individual agent tracing first
    agent_test = await test_individual_agent_tracing()

    # Then run full system test
    system_test = await test_with_dashboard()

    print(f"\n📊 DASHBOARD TEST SUMMARY:")
    print(f"   Agent Testing: {'✅ PASS' if agent_test else '❌ FAIL'}")
    print(f"   System Testing: {'✅ PASS' if system_test else '❌ FAIL'}")

    if agent_test and system_test:
        print(f"\n🎉 ALL DASHBOARD TESTS PASSED!")
        print(f"💡 You now have complete visibility into the multi-agent system.")
        print(f"   Use this script to monitor changes as you replace stubs with real implementations.")
        return 0
    else:
        print(f"\n🚨 SOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
