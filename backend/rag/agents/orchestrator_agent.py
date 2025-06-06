
import os
import logging
from typing import Optional, List
from datetime import datetime, date

from google.genai import types
from google.adk.agents import Agent

from dotenv import load_dotenv
from .prompts.orchestrator import return_orchestrator_instructions
from .tools.coordination_tools import update_alert_status, manage_investigation_state
from .sub_agents.research_agent import create_research_agent

logger = logging.getLogger(__name__)

date_today = date.today()


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
            # Pass RAG corpus to research agent
            create_research_agent(rag_corpus),
            # TODO: Add other sub-agents as they are implemented
            # data_agent,
            # analysis_agent,
            # report_agent,
        ],
        tools=tools,
        generate_content_config=types.GenerateContentConfig(temperature=0.01),
    )
