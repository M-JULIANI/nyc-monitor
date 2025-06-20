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
    Main stateless entry point for investigating an alert.
    This is where the investigation becomes "live" - creates state, executes runner, returns results.

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

        # Create investigation runner (stateless, generic)
        runner = _create_investigation_runner(investigation_state)

        # Create investigation prompt based on alert data
        investigation_prompt = f"""
Investigate this NYC alert:

Alert ID: {alert_data.alert_id}
Event Type: {alert_data.event_type}
Location: {alert_data.location}
Severity: {alert_data.severity}/10
Summary: {alert_data.summary}
Sources: {', '.join(alert_data.sources)}
Investigation ID: {investigation_state.investigation_id}

Please coordinate a thorough investigation using your sub-agents:
1. Have the research agent collect relevant data and save artifacts
2. Analyze the findings and assess the situation
3. Use the coordination tools to manage investigation state
4. Provide a comprehensive summary with references to collected artifacts

Begin the investigation now.
"""

        # Update progress before starting ADK execution
        progress_tracker.add_progress(
            investigation_id=investigation_state.investigation_id,
            status=ProgressStatus.AGENT_ACTIVE,
            active_agent="investigation_orchestrator",
            message="Starting ADK investigation execution"
        )

        # Execute the investigation via ADK runner
        logger.info(
            f"Starting ADK investigation for alert {alert_data.alert_id}")

        # Update investigation state to show it's progressing
        state_manager.update_investigation(investigation_state.investigation_id, {
            "iteration_count": 1,
            "findings": [f"Investigation initiated for {alert_data.event_type} at {alert_data.location}"],
            "confidence_score": 0.3
        })

        try:
            # Execute the actual ADK runner with the investigation prompt
            logger.info(
                f"Executing ADK runner for investigation {investigation_state.investigation_id}")

            # Create a proper Content object for the ADK runner
            from google.genai import types

            # Convert investigation prompt to ADK Content format
            content = types.Content(
                role='user',
                parts=[types.Part(text=investigation_prompt)]
            )

            # Get the session service from the runner
            session_service = None
            if hasattr(runner, '_session_service'):
                session_service = runner._session_service
            elif hasattr(runner, 'session_service'):
                session_service = runner.session_service
            else:
                # The session service was passed during Runner creation, let's use it directly
                from google.adk.sessions import InMemorySessionService
                session_service = InMemorySessionService()
                logger.info("Created new session service as fallback")

            if session_service:
                # Create or get session for this investigation
                session_id = investigation_state.investigation_id
                user_id = f"investigation_user_{alert_data.alert_id}"

                # Create session using the proper ADK session service API
                try:
                    # Try to create a new session through the session service
                    session = session_service.create_session(
                        session_id=session_id,
                        user_id=user_id,
                        app_name="atlas_investigation"
                    )
                    logger.info(
                        f"Created ADK session {session_id} via session service API")
                except Exception as session_create_error:
                    logger.warning(
                        f"Failed to create session via API: {session_create_error}")

                    # Fallback to manual session creation
                    if not hasattr(session_service, '_sessions'):
                        session_service._sessions = {}

                    session_service._sessions[session_id] = {
                        "id": session_id,
                        "user_id": user_id,
                        "state": {
                            "investigation_id": investigation_state.investigation_id,
                            "alert_id": investigation_state.alert_data.alert_id,
                            "alert_severity": investigation_state.alert_data.severity,
                            "alert_type": investigation_state.alert_data.event_type,
                            "alert_location": investigation_state.alert_data.location,
                            "investigation_phase": investigation_state.phase.value,
                            "iteration_count": investigation_state.iteration_count,
                            "trace_id": investigation_state.investigation_id
                        },
                        "created_at": investigation_state.created_at,
                        "investigation_context": investigation_state
                    }
                    logger.info(
                        f"Created ADK session {session_id} via manual fallback")

                # Run the investigation through ADK with proper parameters
                logger.info(
                    f"Calling runner.run_async with session_id={session_id}, user_id={user_id}")

                # The correct ADK runner signature is: run_async(session_id, user_id, new_message)
                investigation_generator = runner.run_async(
                    session_id=session_id,
                    user_id=user_id,
                    new_message=content
                )

                # ADK runner returns an async generator, so we need to collect the results
                investigation_result = ""
                async for result in investigation_generator:
                    if hasattr(result, 'text'):
                        investigation_result += result.text
                    elif isinstance(result, str):
                        investigation_result += result
                    else:
                        investigation_result += str(result)

                logger.info(
                    f"ADK runner completed for investigation {investigation_state.investigation_id}")
                logger.debug(
                    f"ADK result length: {len(investigation_result)} characters")

            else:
                logger.error("No session service available in runner")
                raise Exception("Runner session service not configured")

            # Update investigation state with results
            state_manager.update_investigation(investigation_state.investigation_id, {
                "iteration_count": investigation_state.iteration_count + 1,
                "findings": investigation_state.findings + [f"ADK investigation completed"],
                "confidence_score": 0.8,
                "is_complete": True
            })

            # Mark progress as completed
            progress_tracker.complete_investigation(
                investigation_state.investigation_id,
                "Investigation completed successfully"
            )

            logger.info(
                f"ADK investigation completed for alert {alert_data.alert_id}")

            # Return the actual investigation results from ADK
            return (f"""Investigation Results for Alert {alert_data.alert_id}:

Event: {alert_data.event_type} at {alert_data.location}
Severity: {alert_data.severity}/10
Status: Investigation Complete
Investigation ID: {investigation_state.investigation_id}

ADK Investigation Results:
{investigation_result}

Investigation completed successfully via ADK multi-agent system.""",
                    investigation_state.investigation_id)

        except Exception as adk_error:
            logger.error(f"ADK execution failed: {adk_error}")

            # Mark progress as error
            progress_tracker.error_investigation(
                investigation_state.investigation_id,
                str(adk_error)
            )

            # Fallback to structured mock response if ADK fails
            logger.info(
                f"Falling back to mock response for alert {alert_data.alert_id}")

            investigation_summary = f"""Investigation Results for Alert {alert_data.alert_id}:

Event: {alert_data.event_type} at {alert_data.location}
Severity: {alert_data.severity}/10
Status: Investigation Complete (Fallback Mode)
Investigation ID: {investigation_state.investigation_id}

Initial Findings:
- Alert type: {alert_data.event_type}
- Location confirmed: {alert_data.location} 
- Sources: {', '.join(alert_data.sources)}
- Severity assessment: {alert_data.severity}/10

Investigation Infrastructure:
- State Manager: Investigation created and tracked
- Runner: ADK runner configured and ready
- Artifact Service: Configured for evidence collection
- Sub-agents: Research agent ready for coordination

Note: ADK execution failed ({str(adk_error)}), using fallback response.
Investigation Status: Ready for ADK execution when available"""

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
