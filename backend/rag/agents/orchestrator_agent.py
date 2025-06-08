"""Orchestrator agent with progress tracking callbacks and distributed tracing."""

import os
import logging
from typing import Optional
from datetime import date

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from ..prompts.orchestrator import return_orchestrator_instructions
from ..tools.coordination_tools import update_alert_status, manage_investigation_state
from ..tools.research_tools import create_rag_retrieval_tool
from ..investigation.progress_tracker import progress_tracker, ProgressStatus
from ..investigation.tracing import get_distributed_tracer, TraceEventType

logger = logging.getLogger(__name__)
date_today = date.today()

# Get the global tracer
tracer = get_distributed_tracer()


def _get_trace_context(callback_context: CallbackContext) -> tuple[str, str]:
    """Extract trace ID and investigation ID from callback context."""
    investigation_id = None
    trace_id = None

    # Try to get from callback context state first
    investigation_id = callback_context.state.get("investigation_id")
    trace_id = callback_context.state.get("trace_id")

    # If not found, try to get from session service
    if not investigation_id and hasattr(callback_context, '_invocation_context'):
        runner = getattr(callback_context._invocation_context, 'runner', None)
        if runner and hasattr(runner, '_session_service') and hasattr(runner, '_session_id'):
            session_data = runner._session_service._sessions.get(
                runner._session_id, {})
            session_state = session_data.get("state", {})
            investigation_id = session_state.get("investigation_id")
            trace_id = session_state.get("trace_id")

    # Final fallbacks
    if not investigation_id:
        investigation_id = callback_context.state.get(
            "current_investigation", "unknown")

    if not trace_id:
        trace_id = investigation_id  # Use investigation_id as trace_id

    return trace_id, investigation_id


def before_agent_callback(callback_context: CallbackContext):
    """Called before agent execution - track agent activation with distributed tracing."""
    agent_name = callback_context._invocation_context.agent.name
    trace_id, investigation_id = _get_trace_context(callback_context)

    # Get the input message for tracing
    input_data = getattr(callback_context, 'input', None)
    input_preview = str(input_data)[:200] if input_data else "No input data"

    # Start distributed tracing span
    with tracer.trace_agent_execution(
        trace_id=trace_id,
        agent_name=agent_name,
        operation="execute",
        metadata={
            "investigation_id": investigation_id,
            "input_preview": input_preview,
            "agent_type": "orchestrator" if "orchestrator" in agent_name.lower() else "sub_agent"
        }
    ) as span:
        # Store span in callback context for tool callbacks
        callback_context.state["current_trace_span"] = span.span_id

    # Track progress (existing functionality)
    progress_tracker.add_progress(
        investigation_id=investigation_id,
        status=ProgressStatus.AGENT_ACTIVE,
        active_agent=agent_name,
        message=f"Agent {agent_name} is now active"
    )

    # Trace message flow
    tracer.trace_message(
        trace_id=trace_id,
        from_agent="system",
        to_agent=agent_name,
        message_type="agent_invocation",
        content=input_preview,
        metadata={
            "investigation_id": investigation_id,
            "span_id": span.span_id
        }
    )

    logger.info(
        f"🤖 Agent {agent_name} starting execution for investigation {investigation_id} (trace: {trace_id})")


def after_agent_callback(callback_context: CallbackContext):
    """Called after agent execution - track completion with distributed tracing."""
    agent_name = callback_context._invocation_context.agent.name
    trace_id, investigation_id = _get_trace_context(callback_context)

    # Get the output for tracing
    output_data = getattr(callback_context, 'output', None)
    output_preview = str(output_data)[
        :200] if output_data else "No output data"

    # Track progress (existing functionality)
    progress_tracker.add_progress(
        investigation_id=investigation_id,
        status=ProgressStatus.THINKING,
        active_agent=agent_name,
        message=f"Agent {agent_name} completed execution"
    )

    # Trace message flow for output
    tracer.trace_message(
        trace_id=trace_id,
        from_agent=agent_name,
        to_agent="system",
        message_type="agent_response",
        content=output_preview,
        metadata={
            "investigation_id": investigation_id,
            "execution_completed": True
        }
    )

    logger.info(
        f"✅ Agent {agent_name} completed execution for investigation {investigation_id} (trace: {trace_id})")


def before_tool_callback(callback_context: CallbackContext):
    """Called before tool execution - track tool usage with distributed tracing."""
    # Get current tool being executed
    if hasattr(callback_context, '_tool_call'):
        tool_name = getattr(callback_context._tool_call,
                            'name', 'unknown_tool')
        tool_args = getattr(callback_context._tool_call, 'args', {})
    else:
        tool_name = "unknown_tool"
        tool_args = {}

    agent_name = callback_context._invocation_context.agent.name
    trace_id, investigation_id = _get_trace_context(callback_context)

    # Start tool tracing span
    with tracer.trace_tool_execution(
        trace_id=trace_id,
        tool_name=tool_name,
        agent_name=agent_name,
        metadata={
            "investigation_id": investigation_id,
            "tool_args": str(tool_args)[:500],  # Truncate large args
            "parent_agent": agent_name
        }
    ) as span:
        # Store span for after_tool_callback
        callback_context.state["current_tool_span"] = span.span_id

    # Track progress (existing functionality)
    progress_tracker.add_progress(
        investigation_id=investigation_id,
        status=ProgressStatus.TOOL_EXECUTING,
        active_agent=agent_name,
        current_task=f"Executing {tool_name}",
        message=f"Agent {agent_name} executing tool: {tool_name}"
    )

    # Trace tool invocation message
    tracer.trace_message(
        trace_id=trace_id,
        from_agent=agent_name,
        to_agent=f"tool:{tool_name}",
        message_type="tool_invocation",
        content=f"Invoking {tool_name} with args: {str(tool_args)[:200]}",
        metadata={
            "investigation_id": investigation_id,
            "tool_name": tool_name,
            "span_id": span.span_id
        }
    )

    logger.info(
        f"🔧 Agent {agent_name} executing tool {tool_name} for investigation {investigation_id} (trace: {trace_id})")


def after_tool_callback(callback_context: CallbackContext):
    """Called after tool execution - track tool completion with distributed tracing."""
    # Get tool info
    if hasattr(callback_context, '_tool_call'):
        tool_name = getattr(callback_context._tool_call,
                            'name', 'unknown_tool')
    else:
        tool_name = "unknown_tool"

    agent_name = callback_context._invocation_context.agent.name
    trace_id, investigation_id = _get_trace_context(callback_context)

    # Get tool result
    tool_result = getattr(callback_context, 'result', None)
    result_preview = str(tool_result)[:200] if tool_result else "No result"

    # Trace tool response message
    tracer.trace_message(
        trace_id=trace_id,
        from_agent=f"tool:{tool_name}",
        to_agent=agent_name,
        message_type="tool_response",
        content=f"Tool {tool_name} result: {result_preview}",
        metadata={
            "investigation_id": investigation_id,
            "tool_name": tool_name,
            "execution_completed": True
        }
    )

    logger.info(
        f"✅ Tool {tool_name} completed execution for agent {agent_name} (trace: {trace_id})")


def on_error_callback(callback_context: CallbackContext, error: Exception):
    """Called when an error occurs - trace the error."""
    agent_name = getattr(
        callback_context._invocation_context.agent, 'name', 'unknown')
    trace_id, investigation_id = _get_trace_context(callback_context)

    # Trace the error
    tracer.trace_error(
        trace_id=trace_id,
        error=error,
        agent_name=agent_name,
        context=f"agent_execution:{agent_name}"
    )

    # Update progress tracker
    progress_tracker.add_progress(
        investigation_id=investigation_id,
        status=ProgressStatus.ERROR,
        active_agent=agent_name,
        message=f"Error in agent {agent_name}: {str(error)}"
    )

    logger.error(
        f"🚨 Error in agent {agent_name} for investigation {investigation_id}: {error}")


def create_orchestrator_agent(
    model: str = 'gemini-2.0-flash-001',
    name: str = 'investigation_orchestrator',
    rag_corpus: Optional[str] = None,
) -> Agent:
    """
    Create the orchestrator agent with sub-agents, tools, progress tracking, and distributed tracing.
    """
    tools = [
        update_alert_status,
        manage_investigation_state,
    ]

    # Import here to avoid circular imports
    from ..sub_agents.research_agent import create_research_agent

    return Agent(
        model=model,
        name=name,
        instruction=return_orchestrator_instructions(),
        global_instruction=(
            f"""
            You are the Investigation Orchestrator for the Atlas NYC Monitor system.
            Today's date: {date_today}
            
            Your role is to coordinate multi-agent investigations of NYC alerts and incidents.
            You have access to specialized sub-agents for different aspects of investigation.
            
            The investigation system can store artifacts (images, documents, reports) that agents collect.
            Coordinate artifact collection and reference them in your final investigation summary.
            
            Progress tracking and distributed tracing are active - your actions are being monitored 
            and streamed to users. Provide clear, actionable steps and communicate your reasoning.
            
            IMPORTANT: When delegating to sub-agents, provide clear context about what you need them to do.
            Reference the investigation ID and trace ID when available for proper correlation.
            """
        ),
        sub_agents=[
            # Pass RAG corpus to research agent
            create_research_agent(rag_corpus),
            # TODO: Add other sub-agents as they are implemented
            # data_agent,
            # analysis_agent,
            # report_agent,
        ],
        tools=tools,
        before_agent_callback=before_agent_callback,
        after_agent_callback=after_agent_callback,
        before_tool_callback=before_tool_callback,
        after_tool_callback=after_tool_callback,
        generate_content_config=types.GenerateContentConfig(temperature=0.01),
    )
