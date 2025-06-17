#!/usr/bin/env python3
"""
Quick Trace Script - Test individual components with minimal overhead
Perfect for rapid iteration while replacing stubs with real implementations.
"""

import asyncio
import logging
import sys
from datetime import datetime

# Simple logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(name)-15s | %(levelname)-5s | %(message)s',
    datefmt='%H:%M:%S'
)


def trace_tool(tool_name: str, tool_func, *args, **kwargs):
    """Trace a single tool call with detailed output"""
    print(f"\n🔧 TRACING TOOL: {tool_name}")
    print("-" * 50)
    print(f"📥 Input: args={args}, kwargs={kwargs}")

    try:
        start_time = datetime.utcnow()
        result = tool_func(*args, **kwargs)
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        print(f"⏱️  Duration: {duration:.3f}s")
        print(f"📤 Output Type: {type(result)}")

        if isinstance(result, dict):
            print(f"📊 Dict Keys: {list(result.keys())}")
            for key, value in result.items():
                value_preview = str(
                    value)[:100] + "..." if len(str(value)) > 100 else str(value)
                print(f"    {key}: {value_preview}")
        elif isinstance(result, list):
            print(f"📋 List Length: {len(result)}")
            if result:
                print(f"    First Item: {str(result[0])[:100]}...")
        else:
            result_preview = str(
                result)[:200] + "..." if len(str(result)) > 200 else str(result)
            print(f"📄 Result: {result_preview}")

        print(f"✅ Tool completed successfully")
        return result

    except Exception as e:
        print(f"❌ Tool failed: {e}")
        print(f"🔍 Exception Type: {type(e)}")
        raise


async def trace_agent(agent_name: str, agent_creator, sample_input: str = "test input"):
    """Trace agent creation and basic functionality"""
    print(f"\n🤖 TRACING AGENT: {agent_name}")
    print("-" * 50)

    try:
        # Create agent
        print("🏗️  Creating agent...")
        agent = agent_creator()
        print(f"✅ Agent created successfully")
        print(f"🔧 Tools available: {len(agent.tools)}")

        # List tools
        if hasattr(agent, 'tools') and agent.tools:
            print("📋 Tool list:")
            for i, tool in enumerate(agent.tools, 1):
                tool_name = getattr(tool, 'name', getattr(
                    tool, '__name__', f'Tool_{i}'))
                print(f"    {i}. {tool_name}")

        return agent

    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        raise


def quick_test_research_tools():
    """Quick test of research tools"""
    print("\n🌐 QUICK TEST: Research Tools")
    print("=" * 40)

    try:
        from rag.tools.research_tools import web_search_func, search_social_media_func

        # Test web search
        result = trace_tool("web_search", web_search_func,
                            "NYC protest Washington Square", ["news"])

        # Test social media search
        result = trace_tool("social_media_search", search_social_media_func,
                            "Washington Square Park gathering", "Manhattan")

        return True
    except Exception as e:
        print(f"❌ Research tools test failed: {e}")
        return False


def quick_test_data_tools():
    """Quick test of data tools"""
    print("\n📊 QUICK TEST: Data Tools")
    print("=" * 40)

    try:
        from rag.tools.data_tools import (
            search_knowledge_base, query_census_demographics,
            get_crime_statistics, find_similar_incidents
        )

        # Test each tool
        trace_tool("knowledge_base", search_knowledge_base,
                   "community protest")
        trace_tool("census_data", query_census_demographics,
                   "Manhattan", ["income"])
        trace_tool("crime_stats", get_crime_statistics,
                   "Washington Square", "30d")
        trace_tool("similar_incidents", find_similar_incidents,
                   "protest", "Manhattan")

        return True
    except Exception as e:
        print(f"❌ Data tools test failed: {e}")
        return False


def quick_test_analysis_tools():
    """Quick test of analysis tools"""
    print("\n📈 QUICK TEST: Analysis Tools")
    print("=" * 40)

    try:
        from rag.tools.analysis_tools import (
            analyze_temporal_patterns, correlate_data_sources,
            identify_risk_factors, generate_hypotheses
        )

        # Test with sample data
        sample_events = [
            {"timestamp": "2024-12-03T14:00:00Z", "type": "social_post"},
            {"timestamp": "2024-12-03T15:00:00Z", "type": "311_call"}
        ]

        trace_tool("temporal_analysis", analyze_temporal_patterns,
                   sample_events, "24h")
        trace_tool("correlation", correlate_data_sources,
                   {"web": "data1"}, {"census": "data2"})
        trace_tool("risk_factors", identify_risk_factors, {
                   "severity": 6}, {"location": "Manhattan"})
        trace_tool("hypotheses", generate_hypotheses, {
                   "research": "findings", "data": "analysis"})

        return True
    except Exception as e:
        print(f"❌ Analysis tools test failed: {e}")
        return False


async def quick_test_agents():
    """Quick test of all agents"""
    print("\n🤖 QUICK TEST: All Agents")
    print("=" * 40)

    try:
        from rag.agents.research_agent import create_research_agent
        from rag.agents.data_agent import create_data_agent
        from rag.agents.analysis_agent import create_analysis_agent
        from rag.agents.report_agent import create_report_agent

        # Test each agent
        await trace_agent("Research Agent", create_research_agent)
        await trace_agent("Data Agent", create_data_agent)
        await trace_agent("Analysis Agent", create_analysis_agent)
        await trace_agent("Report Agent", create_report_agent)

        return True
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        return False


async def main():
    """Quick trace main function"""
    print("⚡ QUICK TRACE MODE - Rapid Component Testing")
    print("=" * 60)
    print("Perfect for testing individual components as you iterate!")
    print()

    # Quick tests
    research_ok = quick_test_research_tools()
    data_ok = quick_test_data_tools()
    analysis_ok = quick_test_analysis_tools()
    agents_ok = await quick_test_agents()

    print(f"\n📊 QUICK TRACE SUMMARY:")
    print("-" * 30)
    print(f"   Research Tools: {'✅' if research_ok else '❌'}")
    print(f"   Data Tools: {'✅' if data_ok else '❌'}")
    print(f"   Analysis Tools: {'✅' if analysis_ok else '❌'}")
    print(f"   Agents: {'✅' if agents_ok else '❌'}")

    total_passed = sum([research_ok, data_ok, analysis_ok, agents_ok])
    print(f"\n🎯 {total_passed}/4 components working correctly")

    if total_passed == 4:
        print("🎉 All components ready! You can run the full investigation.")
    else:
        print("🔧 Some components need attention. Check the traces above.")


if __name__ == "__main__":
    asyncio.run(main())
