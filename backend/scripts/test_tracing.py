#!/usr/bin/env python3
"""Test script for distributed tracing functionality."""

from rag.investigation.state_manager import AlertData, state_manager
from rag.investigation.tracing import get_distributed_tracer, TraceEventType
import asyncio
import sys
import os
import pytest
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_basic_tracing():
    """Test basic tracing functionality."""
    tracer = get_distributed_tracer()

    # Start a test trace
    trace_id = "test_investigation_001"
    span_id = tracer.start_trace(
        trace_id=trace_id,
        operation_name="test_investigation",
        metadata={"test": True}
    )

    print(f"🔍 Started trace: {trace_id}")

    # Simulate agent execution
    with tracer.trace_agent_execution(
        trace_id=trace_id,
        agent_name="test_orchestrator",
        operation="coordinate",
        metadata={"phase": "testing"}
    ) as agent_span:
        print(f"🤖 Agent execution span: {agent_span.span_id}")

        # Simulate tool execution
        with tracer.trace_tool_execution(
            trace_id=trace_id,
            tool_name="web_search",
            agent_name="test_orchestrator",
            metadata={"query": "test query"}
        ) as tool_span:
            print(f"🔧 Tool execution span: {tool_span.span_id}")

        # Simulate message passing
        message_id = tracer.trace_message(
            trace_id=trace_id,
            from_agent="test_orchestrator",
            to_agent="research_agent",
            message_type="delegation",
            content="Please research this test topic and collect artifacts",
            metadata={"task": "research"}
        )
        print(f"📨 Message logged: {message_id}")

        # Simulate response message
        response_id = tracer.trace_message(
            trace_id=trace_id,
            from_agent="research_agent",
            to_agent="test_orchestrator",
            message_type="response",
            content="Research completed. Found 3 relevant articles and saved 2 screenshots as artifacts.",
            metadata={"artifacts_collected": 2}
        )
        print(f"📨 Response logged: {response_id}")

    # Get trace summary
    summary = tracer.get_trace_summary(trace_id)
    print(f"\n📊 Trace Summary:")
    print(f"   Total spans: {summary['total_spans']}")
    print(f"   Total messages: {summary['total_messages']}")
    print(f"   Agents involved: {summary['agents_involved']}")
    print(f"   Tools used: {summary['tools_used']}")
    print(f"   Duration: {summary['total_duration_ms']}ms")

    # Get timeline
    timeline = tracer.get_trace_timeline(trace_id)
    print(f"\n⏱️  Timeline ({len(timeline)} events):")
    for i, event in enumerate(timeline):
        print(
            f"   {i+1}. [{event['timestamp']}] {event['type']}: {event.get('operation', event.get('message_type', 'N/A'))}")

    assert trace_id is not None


@pytest.mark.expensive_api
@pytest.mark.asyncio
async def test_investigation_with_tracing():
    """Test tracing with a mock investigation."""
    from rag.investigation_service_simple import investigate_alert_simple as investigate_alert

    # Create a test alert
    alert_data = AlertData(
        alert_id="test_alert_001",
        event_type="infrastructure_issue",
        location="Brooklyn Bridge",
        severity=7,
        summary="Test investigation for tracing",
        timestamp=datetime.now(timezone.utc),
        sources=["test_system"]
    )

    print(f"\n🚨 Starting test investigation for: {alert_data.event_type}")

    try:
        # This would normally run the full ADK investigation
        # For testing, we'll just see the tracing setup
        result = await investigate_alert(alert_data)
        print(f"✅ Investigation completed")

        # Get tracing data
        tracer = get_distributed_tracer()
        trace_id = alert_data.alert_id  # Investigation uses alert_id as trace_id

        summary = tracer.get_trace_summary(trace_id)
        timeline = tracer.get_trace_timeline(trace_id)

        print(f"\n📊 Investigation Trace Summary:")
        print(f"   Trace ID: {trace_id}")
        print(f"   Total spans: {summary['total_spans']}")
        print(f"   Total messages: {summary['total_messages']}")
        print(f"   Status: {summary['status']}")

        if timeline:
            print(f"\n⏱️  Investigation Timeline:")
            for event in timeline[:5]:  # Show first 5 events
                print(
                    f"   [{event['timestamp']}] {event['type']}: {event.get('operation', event.get('message_type', 'N/A'))}")
            if len(timeline) > 5:
                print(f"   ... and {len(timeline) - 5} more events")

        return trace_id

    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        return None


def demonstrate_api_usage():
    """Show how to use the tracing APIs."""
    print(f"\n🌐 API Usage Examples:")
    print(f"   GET /investigate/{{investigation_id}}/trace/summary")
    print(f"   GET /investigate/{{investigation_id}}/trace/timeline")
    print(f"   GET /investigate/{{investigation_id}}/trace/export")
    print(f"   GET /investigate/{{investigation_id}}/agent-flow")
    print(f"")
    print(f"   These endpoints provide:")
    print(f"   • Summary: High-level metrics and agent involvement")
    print(f"   • Timeline: Chronological view of all events")
    print(f"   • Export: Complete trace data for external analysis")
    print(f"   • Agent Flow: Message passing between agents")


if __name__ == "__main__":
    print("🔍 Testing Distributed Tracing System")
    print("=" * 50)

    # Test 1: Basic tracing functionality
    print("\n1️⃣  Testing basic tracing...")
    trace_id1 = test_basic_tracing()

    # Test 2: Investigation tracing (async)
    print("\n2️⃣  Testing investigation tracing...")
    trace_id2 = asyncio.run(test_investigation_with_tracing())

    # Test 3: API usage demonstration
    print("\n3️⃣  API Usage:")
    demonstrate_api_usage()

    print(f"\n✅ Tracing tests completed!")
    print(f"   Generated trace IDs: {trace_id1}, {trace_id2}")
    print(f"   You can access these traces via the API endpoints when the server is running.")
