"""Orchestrator agent with progress tracking callbacks."""

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

logger = logging.getLogger(__name__)
date_today = date.today()


def before_agent_callback(callback_context: CallbackContext):
    """Called before agent execution - track agent activation."""
    agent_name = callback_context._invocation_context.agent.name

    # Get investigation ID from session state (the proper ADK way)
    investigation_id = None

    # Try to get from callback context state first
    investigation_id = callback_context.state.get("investigation_id")

    # If not found, try to get from session service
    if not investigation_id and hasattr(callback_context, '_invocation_context'):
        runner = getattr(callback_context._invocation_context, 'runner', None)
        if runner and hasattr(runner, '_session_service') and hasattr(runner, '_session_id'):
            session_data = runner._session_service._sessions.get(
                runner._session_id, {})
            session_state = session_data.get("state", {})
            investigation_id = session_state.get("investigation_id")

    # Final fallback
    if not investigation_id:
        investigation_id = callback_context.state.get(
            "current_investigation", "unknown")

    # Track agent becoming active
    progress_tracker.add_progress(
        investigation_id=investigation_id,
        status=ProgressStatus.AGENT_ACTIVE,
        active_agent=agent_name,
        message=f"Agent {agent_name} is now active"
    )

    logger.info(
        f"Agent {agent_name} starting execution for investigation {investigation_id}")


def after_agent_callback(callback_context: CallbackContext):
    """Called after agent execution - track completion."""
    agent_name = callback_context._invocation_context.agent.name

    # Get investigation ID from session state (the proper ADK way)
    investigation_id = None

    # Try to get from callback context state first
    investigation_id = callback_context.state.get("investigation_id")

    # If not found, try to get from session service
    if not investigation_id and hasattr(callback_context, '_invocation_context'):
        runner = getattr(callback_context._invocation_context, 'runner', None)
        if runner and hasattr(runner, '_session_service') and hasattr(runner, '_session_id'):
            session_data = runner._session_service._sessions.get(
                runner._session_id, {})
            session_state = session_data.get("state", {})
            investigation_id = session_state.get("investigation_id")

    # Final fallback
    if not investigation_id:
        investigation_id = callback_context.state.get(
            "current_investigation", "unknown")

    # Track agent completion
    progress_tracker.add_progress(
        investigation_id=investigation_id,
        status=ProgressStatus.THINKING,
        active_agent=agent_name,
        message=f"Agent {agent_name} completed execution"
    )

    logger.info(
        f"Agent {agent_name} completed execution for investigation {investigation_id}")


def before_tool_callback(callback_context: CallbackContext):
    """Called before tool execution - track tool usage."""
    # Get current tool being executed
    if hasattr(callback_context, '_tool_call'):
        tool_name = getattr(callback_context._tool_call,
                            'name', 'unknown_tool')
    else:
        tool_name = "unknown_tool"

    agent_name = callback_context._invocation_context.agent.name

    # Get investigation ID from session state (the proper ADK way)
    investigation_id = None

    # Try to get from callback context state first
    investigation_id = callback_context.state.get("investigation_id")

    # If not found, try to get from session service
    if not investigation_id and hasattr(callback_context, '_invocation_context'):
        runner = getattr(callback_context._invocation_context, 'runner', None)
        if runner and hasattr(runner, '_session_service') and hasattr(runner, '_session_id'):
            session_data = runner._session_service._sessions.get(
                runner._session_id, {})
            session_state = session_data.get("state", {})
            investigation_id = session_state.get("investigation_id")

    # Final fallback
    if not investigation_id:
        investigation_id = callback_context.state.get(
            "current_investigation", "unknown")

    # Track tool execution
    progress_tracker.add_progress(
        investigation_id=investigation_id,
        status=ProgressStatus.TOOL_EXECUTING,
        active_agent=agent_name,
        current_task=f"Executing {tool_name}",
        message=f"Agent {agent_name} executing tool: {tool_name}"
    )

    logger.info(
        f"Agent {agent_name} executing tool {tool_name} for investigation {investigation_id}")


def create_orchestrator_agent(
    model: str = 'gemini-2.0-flash-001',
    name: str = 'investigation_orchestrator',
    rag_corpus: Optional[str] = None,
) -> Agent:
    """
    Create the orchestrator agent with sub-agents, tools, and progress tracking.
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
            
            Progress tracking is active - your actions are being monitored and streamed to users.
            Provide clear, actionable steps and communicate your reasoning.
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
        generate_content_config=types.GenerateContentConfig(temperature=0.01),
    )
