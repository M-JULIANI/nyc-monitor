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

logger = logging.getLogger(__name__)

date_today = date.today()


def create_rag_retrieval_tool(
    rag_corpus: Optional[str] = None,
    name: str = 'retrieve_rag_documentation',
    description: str = 'Use this tool to retrieve documentation and reference materials for the question from the RAG corpus',
    similarity_top_k: int = 10,
    vector_distance_threshold: float = 0.6,
) -> Optional[VertexAiRagRetrieval]:
    """
    Create a RAG retrieval tool if a corpus is provided.
    Returns None if no corpus is provided, allowing the agent to work without RAG.
    """
    if not rag_corpus:
        logger.info(
            "No RAG corpus provided, agent will run without RAG capabilities")
        return None

    try:
        return VertexAiRagRetrieval(
            name=name,
            description=description,
            rag_resources=[
                rag.RagResource(
                    rag_corpus=rag_corpus
                )
            ],
            similarity_top_k=similarity_top_k,
            vector_distance_threshold=vector_distance_threshold,
        )
    except Exception as e:
        logger.error(f"Failed to create RAG retrieval tool: {e}")
        return None


def create_artifact_service() -> InMemoryArtifactService:
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


def setup_investigation_context(callback_context: CallbackContext):
    """Setup the investigation context and state."""

    # Initialize investigation state if not present
    if "investigation_state" not in callback_context.state:
        # For now, create a simple mock alert for testing
        # TODO: Get this from the actual alert data passed in
        mock_alert = AlertData(
            alert_id="test_alert_001",
            severity=7,
            event_type="traffic_incident",
            location="Brooklyn Bridge, NYC",
            summary="Traffic delays reported on Brooklyn Bridge",
            timestamp=datetime.utcnow(),
            sources=["reddit", "social_media"]
        )

        investigation_state = state_manager.create_investigation(mock_alert)
        callback_context.state["investigation_state"] = investigation_state

    # Update agent instructions with current investigation context
    investigation_state = callback_context.state["investigation_state"]
    alert_data = investigation_state.alert_data

    callback_context._invocation_context.agent.instruction = (
        return_orchestrator_instructions()
        + f"""

Current Investigation Context:
- Alert ID: {alert_data.alert_id}
- Location: {alert_data.location}
- Severity: {alert_data.severity}/10
- Event Type: {alert_data.event_type}
- Summary: {alert_data.summary}
- Investigation Phase: {investigation_state.phase.value}
- Iteration Count: {investigation_state.iteration_count}

Your task is to coordinate the investigation of this alert using your sub-agents.
Start by assigning appropriate tasks to the research agent.

Available artifacts will be stored and can be referenced by filename.
Agents can save images, documents, and reports as artifacts for the investigation.
"""
    )


def create_orchestrator_agent(
    model: str = 'gemini-2.0-flash-001',
    name: str = 'investigation_orchestrator',
    rag_corpus: Optional[str] = None,
) -> Agent:
    """
    Create the orchestrator agent with sub-agents and tools.
    """
    tools = [
        update_alert_status,
        manage_investigation_state,
    ]

    # Add RAG tool if corpus is provided
    rag_tool = create_rag_retrieval_tool(rag_corpus)
    if rag_tool:
        tools.append(rag_tool)

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
            """
        ),
        sub_agents=[
            research_agent,
            # TODO: Add other sub-agents as they are implemented
            # data_agent,
            # analysis_agent,
            # report_agent,
        ],
        tools=tools,
        before_agent_callback=setup_investigation_context,
        generate_content_config=types.GenerateContentConfig(temperature=0.01),
    )


# Create the artifact service for investigations
investigation_artifact_service = create_artifact_service()


def create_investigation_runner(alert_data: Optional[AlertData] = None):
    """
    Create a runner for investigation with artifact service.

    Args:
        alert_data: Optional alert data to investigate

    Returns:
        Tuple of (runner, investigation_id) for managing the investigation
    """
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    # Create orchestrator agent
    orchestrator = create_orchestrator_agent()

    # Create session service for investigation tracking
    session_service = InMemorySessionService()

    # Create runner with artifact service
    runner = Runner(
        agent=orchestrator,
        app_name="atlas_investigation",
        session_service=session_service,
        artifact_service=investigation_artifact_service
    )

    return runner


def investigate_alert(alert_data: AlertData) -> str:
    """
    Main entry point for investigating an alert.

    Args:
        alert_data: Alert information to investigate

    Returns:
        Investigation results as a string
    """
    try:
        # Create investigation runner
        runner = create_investigation_runner(alert_data)

        # Create investigation prompt
        investigation_prompt = f"""
            Investigate this NYC alert:

            Alert ID: {alert_data.alert_id}
            Event Type: {alert_data.event_type}
            Location: {alert_data.location}
            Severity: {alert_data.severity}/10
            Summary: {alert_data.summary}
            Sources: {', '.join(alert_data.sources)}

            Please coordinate a thorough investigation using your sub-agents:
            1. Have the research agent collect relevant data and save artifacts
            2. Analyze the findings and assess the situation
            3. Provide a comprehensive summary with references to collected artifacts

            Begin the investigation now.
            """

        # For now, call the agent directly
        # TODO: Implement proper async runner execution
        response = investigation_artifact_service  # Placeholder

        return f"Investigation initiated for alert {alert_data.alert_id}. Artifact service ready."

    except Exception as e:
        logger.error(f"Error during investigation: {e}")
        return f"Investigation failed: {str(e)}"


# Create the root orchestrator agent (for backward compatibility)
root_agent = create_orchestrator_agent()
