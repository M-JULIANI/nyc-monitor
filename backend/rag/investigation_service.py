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

        # Update progress before starting minimal agent execution
        progress_tracker.add_progress(
            investigation_id=investigation_state.investigation_id,
            status=ProgressStatus.AGENT_ACTIVE,
            active_agent="minimal_working_agent",
            message="Starting minimal working agent execution"
        )

        # Execute the investigation via minimal working agent
        logger.info(
            f"Starting minimal working agent for alert {alert_data.alert_id}")

        # Update investigation state to show it's progressing
        state_manager.update_investigation(investigation_state.investigation_id, {
            "iteration_count": 1,
            "findings": [f"Investigation initiated for {alert_data.event_type} at {alert_data.location}"],
            "confidence_score": 0.3
        })

        try:
            # Use the minimal working agent instead of complex ADK runner
            from .agents.minimal_working_agent import execute_minimal_investigation

            logger.info(
                f"Executing minimal working agent for investigation {investigation_state.investigation_id}")

            # Prepare investigation data for the minimal agent
            investigation_data = {
                "investigation_id": investigation_state.investigation_id,
                "alert_data": {
                    "alert_id": alert_data.alert_id,
                    "event_type": alert_data.event_type,
                    "location": alert_data.location,
                    "severity": alert_data.severity,
                    "summary": alert_data.summary,
                    "sources": alert_data.sources,
                    "timestamp": alert_data.timestamp.isoformat()
                }
            }

            # Execute the minimal working agent
            agent_result = await execute_minimal_investigation(investigation_data)

            logger.info(
                f"Minimal working agent completed for investigation {investigation_state.investigation_id}")
            logger.info(f"Agent result: {agent_result}")

            # Update investigation state with results
            if agent_result.get("success"):
                state_manager.update_investigation(investigation_state.investigation_id, {
                    "iteration_count": investigation_state.iteration_count + 1,
                    "findings": investigation_state.findings + [
                        f"Minimal working agent completed successfully",
                        f"Generated {agent_result.get('maps_generated', 0)} maps",
                        f"Collected {agent_result.get('images_collected', 0)} images",
                        f"Total artifacts: {agent_result.get('total_artifacts', 0)}"
                    ],
                    "confidence_score": 0.9,
                    "is_complete": True
                })

                # Mark progress as completed
                progress_tracker.complete_investigation(
                    investigation_state.investigation_id,
                    "Investigation completed successfully via minimal working agent"
                )

                investigation_summary = f"""Investigation Results for Alert {alert_data.alert_id}:

Event: {alert_data.event_type} at {alert_data.location}
Severity: {alert_data.severity}/10
Status: Investigation Complete
Investigation ID: {investigation_state.investigation_id}

🎯 Minimal Working Agent Results:
✅ Workflow Status: {agent_result.get('workflow_status', 'unknown')}
✅ Maps Generated: {agent_result.get('maps_generated', 0)} satellite maps
✅ Images Collected: {agent_result.get('images_collected', 0)} images
✅ Total Artifacts: {agent_result.get('total_artifacts', 0)}

📋 Artifact Breakdown:
{agent_result.get('artifact_breakdown', {})}

📝 Summary: {agent_result.get('summary', 'Investigation completed')}

🔗 Agent Response: {agent_result.get('agent_response', 'No detailed response')[:500]}...

Investigation completed successfully via Minimal Working Agent."""

            else:
                # Agent failed
                state_manager.update_investigation(investigation_state.investigation_id, {
                    "iteration_count": investigation_state.iteration_count + 1,
                    "findings": investigation_state.findings + [
                        f"Minimal working agent failed: {agent_result.get('error', 'Unknown error')}"
                    ],
                    "confidence_score": 0.2,
                    "is_complete": False
                })

                # Mark progress as error
                progress_tracker.error_investigation(
                    investigation_state.investigation_id,
                    agent_result.get('error', 'Agent execution failed')
                )

                investigation_summary = f"""Investigation Results for Alert {alert_data.alert_id}:

Event: {alert_data.event_type} at {alert_data.location}
Severity: {alert_data.severity}/10
Status: Investigation Failed
Investigation ID: {investigation_state.investigation_id}

❌ Minimal Working Agent Error:
Error: {agent_result.get('error', 'Unknown error')}
Workflow Status: {agent_result.get('workflow_status', 'failed')}

Investigation failed. Please check logs for details."""

            logger.info(
                f"Investigation completed for alert {alert_data.alert_id}")

            # Return the investigation results
            return (investigation_summary, investigation_state.investigation_id)

        except Exception as agent_error:
            logger.error(
                f"Minimal working agent execution failed: {agent_error}")

            # Mark progress as error
            progress_tracker.error_investigation(
                investigation_state.investigation_id,
                str(agent_error)
            )

            # Fallback to structured response if agent fails
            logger.info(
                f"Falling back to basic response for alert {alert_data.alert_id}")

            investigation_summary = f"""Investigation Results for Alert {alert_data.alert_id}:

Event: {alert_data.event_type} at {alert_data.location}
Severity: {alert_data.severity}/10
Status: Investigation Error (Fallback Mode)
Investigation ID: {investigation_state.investigation_id}

Initial Analysis:
- Alert type: {alert_data.event_type}
- Location: {alert_data.location} 
- Sources: {', '.join(alert_data.sources)}
- Severity assessment: {alert_data.severity}/10

Infrastructure Status:
- State Manager: ✅ Investigation created and tracked
- Minimal Working Agent: ❌ Execution failed ({str(agent_error)})

Note: Minimal working agent execution failed, using fallback response.
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
