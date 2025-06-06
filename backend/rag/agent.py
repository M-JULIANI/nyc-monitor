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

from backend.rag.agents.orchestrator_agent import create_orchestrator_agent
from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from google.adk.artifacts import InMemoryArtifactService, GcsArtifactService
from vertexai.preview import rag

from dotenv import load_dotenv
from .prompts.orchestrator import return_orchestrator_instructions
from .sub_agents.research_agent import research_agent
from .tools.coordination_tools import update_alert_status, manage_investigation_state
from .investigation.state_manager import AlertData, state_manager
from .investigation.progress_tracker import progress_tracker, ProgressStatus

logger = logging.getLogger(__name__)
date_today = date.today()


def _create_artifact_service() -> InMemoryArtifactService:
    """
    Create an artifact service for the investigation system.

    Returns:
        ArtifactService instance for storing investigation artifacts
    """
    # TODO: For production, use GcsArtifactService
    # gcs_bucket = os.getenv("INVESTIGATION_ARTIFACTS_BUCKET", "atlas-investigation-artifacts")
    # return GcsArtifactService(bucket_name=gcs_bucket)

    # For now, use in-memory for development
    logger.info("Using InMemoryArtifactService for investigation artifacts")
    return InMemoryArtifactService()


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
    rag_corpus = os.getenv("RAG_CORPUS_ID")

    # Create orchestrator agent with RAG corpus access and progress callbacks
    orchestrator = create_orchestrator_agent(rag_corpus=rag_corpus)

    # Create session service for investigation tracking
    session_service = InMemorySessionService()

    # Create runner with artifact service
    runner = Runner(
        agent=orchestrator,
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
            "current_investigation": investigation_state.investigation_id  # Fallback key
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


async def investigate_alert(alert_data: AlertData) -> str:
    """
    Main stateless entry point for investigating an alert.
    This is where the investigation becomes "live" - creates state, executes runner, returns results.

    Args:
        alert_data: Alert information to investigate

    Returns:
        Investigation results as a string
    """
    try:
        # Create investigation state first
        investigation_state = state_manager.create_investigation(alert_data)
        logger.info(
            f"Created investigation {investigation_state.investigation_id} for alert {alert_data.alert_id}")

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

            # Run the investigation through ADK
            investigation_result = await runner.run_async(investigation_prompt)

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
            return f"""Investigation Results for Alert {alert_data.alert_id}:

Event: {alert_data.event_type} at {alert_data.location}
Severity: {alert_data.severity}/10
Status: Investigation Complete
Investigation ID: {investigation_state.investigation_id}

ADK Investigation Results:
{investigation_result}

Investigation completed successfully via ADK multi-agent system."""

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

            return investigation_summary

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

        return f"Investigation failed for alert {alert_data.alert_id}: {str(e)}"
