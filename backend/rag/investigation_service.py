# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging
from typing import Optional, List
from datetime import datetime, date

from .root_agent import root_agent_instance
from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from google.adk.artifacts import InMemoryArtifactService, GcsArtifactService
from vertexai.preview import rag

from .prompts.orchestrator import return_orchestrator_instructions
# Note: This is not used since we switched to root_agent, but keeping import for potential reference
# from .agents.research_agent import create_research_agent
from .tools.coordination_tools import update_alert_status, manage_investigation_state
from .investigation.state_manager import AlertData, state_manager, InvestigationPhase
from .investigation.progress_tracker import progress_tracker, ProgressStatus
from .investigation.tracing import get_distributed_tracer

logger = logging.getLogger(__name__)
date_today = date.today()

# Get the global tracer
tracer = get_distributed_tracer()


def _create_artifact_service() -> GcsArtifactService:
    """
    Create an artifact service for the investigation system.

    Returns:
        GcsArtifactService instance for storing investigation artifacts in GCS
    """
    # Use existing staging bucket for Vertex AI native integration
    staging_bucket = os.getenv(
        "STAGING_BUCKET", "gs://atlas-460522-vertex-deploy")
    bucket_name = staging_bucket.replace("gs://", "").split("/")[0]

    logger.info(f"Using GcsArtifactService with bucket: {bucket_name}")
    return GcsArtifactService(bucket_name=bucket_name)


def _create_investigation_runner(investigation_state):
    """
    Create a runner for investigation with artifact service and investigation context.

    Args:
        investigation_state: InvestigationState object containing alert data and investigation context

    Returns:
        Configured Runner instance ready for investigation execution with proper context
    """
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    # Create artifact service for this investigation
    artifact_service = _create_artifact_service()

    # Get RAG corpus from environment
    rag_corpus = os.getenv("RAG_CORPUS")

    # Use the root agent instance (already configured)
    root_agent = root_agent_instance.agent

    # Create session service for investigation tracking
    session_service = InMemorySessionService()

    # Create runner with artifact service
    runner = Runner(
        agent=root_agent,
        app_name="atlas_investigation",
        session_service=session_service,
        artifact_service=artifact_service
    )

    # Set investigation context in runner's session state (the ADK way)
    # This ensures callbacks have access to investigation_id and other context
    if hasattr(runner, '_session_service') and runner._session_service:
        # Create a session for this investigation
        session_id = investigation_state.investigation_id

        # Initialize session state with investigation context
        session_state = {
            "investigation_id": investigation_state.investigation_id,
            "alert_id": investigation_state.alert_data.alert_id,
            "alert_severity": investigation_state.alert_data.severity,
            "alert_type": investigation_state.alert_data.event_type,
            "alert_location": investigation_state.alert_data.location,
            "investigation_phase": investigation_state.phase.value,
            "iteration_count": investigation_state.iteration_count,
            "current_investigation": investigation_state.investigation_id,  # Fallback key
            # Use investigation_id as trace_id
            "trace_id": investigation_state.investigation_id
        }

        # Store session state in the session service
        if hasattr(session_service, '_sessions'):
            session_service._sessions[session_id] = {
                "state": session_state,
                "created_at": investigation_state.created_at,
                "investigation_context": investigation_state
            }

        # Also set the session ID on the runner if possible
        if hasattr(runner, '_session_id'):
            runner._session_id = session_id

        logger.info(
            f"Set investigation context in runner session: {investigation_state.investigation_id}")

    return runner


async def investigate_alert(alert_data: AlertData) -> tuple[str, str]:
    """
    Main stateless entry point for investigating an alert using the ADK multi-agent approach.
    This is the full deployment approach with specialized agents.

    Args:
        alert_data: Alert information to investigate

    Returns:
        Tuple of (investigation_results_string, investigation_id)
    """
    try:
        # Create investigation state first
        investigation_state = state_manager.create_investigation(alert_data)
        logger.info(
            f"Created investigation {investigation_state.investigation_id} for alert {alert_data.alert_id}")

        # Initialize distributed tracing for this investigation
        trace_id = investigation_state.investigation_id
        tracer.start_trace(
            trace_id=trace_id,
            operation_name=f"investigate_alert:{alert_data.event_type}",
            metadata={
                "alert_id": alert_data.alert_id,
                "event_type": alert_data.event_type,
                "location": alert_data.location,
                "severity": alert_data.severity,
                "investigation_id": investigation_state.investigation_id
            }
        )

        # Start progress tracking
        progress_tracker.start_investigation(
            investigation_state.investigation_id)

        # Update progress before starting ADK execution
        progress_tracker.add_progress(
            investigation_id=investigation_state.investigation_id,
            status=ProgressStatus.AGENT_ACTIVE,
            active_agent="adk_investigation",
            message="Starting ADK investigation execution"
        )

        # Execute the investigation via ADK runner
        logger.info(
            f"Starting ADK investigation for alert {alert_data.alert_id}")

        # Update investigation state to show it's progressing
        state_manager.update_investigation(investigation_state.investigation_id, {
            "iteration_count": 1,
            "findings": [f"ADK Investigation initiated for {alert_data.event_type} at {alert_data.location}"],
            "confidence_score": 0.3
        })

        try:
            # Create investigation runner for this specific investigation
            runner = _create_investigation_runner(investigation_state)

            logger.info(
                f"Executing ADK runner for investigation {investigation_state.investigation_id}")

            # Prepare the investigation message for the ADK agent
            investigation_message = f"""
🚨 ALERT INVESTIGATION REQUEST 🚨

**Alert Details:**
- Alert ID: {alert_data.alert_id}
- Event Type: {alert_data.event_type}
- Location: {alert_data.location}
- Severity: {alert_data.severity}/10
- Summary: {alert_data.summary}
- Sources: {', '.join(alert_data.sources)}
- Investigation ID: {investigation_state.investigation_id}

**Investigation Requirements:**
1. Analyze the severity and nature of this alert
2. Research relevant background information
3. Collect evidence and artifacts
4. Coordinate investigation activities
5. Provide comprehensive findings and recommendations

**Context:**
This is a NYC Atlas system investigation for monitoring civic incidents and events.
Use all available tools to thoroughly investigate this alert and provide actionable insights.

Please begin the investigation immediately.
"""

            # Execute the ADK runner
            results = []
            session_id = investigation_state.investigation_id
            user_id = f"investigation_user_{alert_data.alert_id}"

            # Create session via the session service
            session = runner._session_service.create_session(
                session_id=session_id,
                user_id=user_id,
                app_name="atlas_investigation"
            )

            logger.info(
                f"Created ADK session {session_id} via session service API")

            # Create the message as types.Content
            from google.genai import types
            content = types.Content(
                role='user',
                parts=[types.Part(text=investigation_message)]
            )

            logger.info(
                f"Calling runner.run_async with session_id={session_id}, user_id={user_id}")

            async for event in runner.run_async(
                session_id=session_id,
                user_id=user_id,
                new_message=content
            ):
                # Handle different types of events from the ADK runner
                if hasattr(event, 'text') and event.text:
                    results.append(event.text)
                    logger.info(f"ADK response: {event.text[:100]}...")
                elif hasattr(event, 'content'):
                    # Handle Content objects properly
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                results.append(part.text)
                            elif hasattr(part, 'function_call') and part.function_call:
                                logger.info(
                                    f"ADK function call: {part.function_call.name}")
                    else:
                        results.append(str(event.content))
                elif isinstance(event, str):
                    results.append(event)
                else:
                    results.append(str(event))

            logger.info(
                f"ADK runner completed for investigation {investigation_state.investigation_id}")

            # Combine all results
            full_response = "\n".join(
                results) if results else "No response from ADK agents"

            # Update investigation state with results
            state_manager.update_investigation(investigation_state.investigation_id, {
                "iteration_count": investigation_state.iteration_count + 1,
                "findings": investigation_state.findings + [
                    f"ADK multi-agent investigation completed",
                    f"Response length: {len(full_response)} characters"
                ],
                "confidence_score": 0.8,
                "is_complete": True
            })

            # Mark progress as completed
            progress_tracker.complete_investigation(
                investigation_state.investigation_id,
                "Investigation completed successfully via ADK multi-agent system"
            )

            investigation_summary = f"""Investigation Results for Alert {alert_data.alert_id}:

Event: {alert_data.event_type} at {alert_data.location}
Severity: {alert_data.severity}/10
Status: Investigation Complete (ADK Multi-Agent)
Investigation ID: {investigation_state.investigation_id}

🎯 ADK Multi-Agent System Results:
✅ Investigation Status: Completed
✅ Agent Coordination: Multi-agent workflow executed
✅ Response Length: {len(full_response)} characters

📝 Agent Response:
{full_response[:1000]}{"..." if len(full_response) > 1000 else ""}

Investigation completed successfully via ADK Multi-Agent System."""

            logger.info(
                f"ADK investigation completed for alert {alert_data.alert_id}")

            # Return the investigation results
            return (investigation_summary, investigation_state.investigation_id)

        except Exception as adk_error:
            logger.error(f"ADK investigation execution failed: {adk_error}")

            # Mark progress as error
            progress_tracker.error_investigation(
                investigation_state.investigation_id,
                str(adk_error)
            )

            # Fallback to structured response if ADK fails
            logger.info(
                f"Falling back to basic response for alert {alert_data.alert_id}")

            investigation_summary = f"""Investigation Results for Alert {alert_data.alert_id}:

Event: {alert_data.event_type} at {alert_data.location}
Severity: {alert_data.severity}/10
Status: Investigation Error (ADK Fallback Mode)
Investigation ID: {investigation_state.investigation_id}

Initial Analysis:
- Alert type: {alert_data.event_type}
- Location: {alert_data.location} 
- Sources: {', '.join(alert_data.sources)}
- Severity assessment: {alert_data.severity}/10

Infrastructure Status:
- State Manager: ✅ Investigation created and tracked
- ADK Multi-Agent System: ❌ Execution failed ({str(adk_error)})

Note: ADK multi-agent execution failed, using fallback response.
Investigation Status: Requires manual intervention"""

            return (investigation_summary, investigation_state.investigation_id)

    except Exception as e:
        logger.error(f"Error during investigation: {e}")

        # Try to mark progress as error if we have an investigation state
        try:
            if 'investigation_state' in locals():
                progress_tracker.error_investigation(
                    investigation_state.investigation_id,
                    str(e)
                )
        except:
            pass

        return (f"Investigation failed for alert {alert_data.alert_id}: {str(e)}", "")
