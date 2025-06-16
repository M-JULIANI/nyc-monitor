"""
Research Agent for external data collection with artifact support.
Handles web search, APIs, social media, and stores findings in RAG.
"""

import os
import logging
from typing import Optional, List, Dict
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from ..tools.research_tools import (
    web_search,
    collect_media_content,
    save_investigation_screenshot,
    list_investigation_artifacts,
    create_rag_retrieval_tool,
    search_social_media_func,
    query_live_apis_func
)
from ..prompts.research import return_research_instructions

logger = logging.getLogger(__name__)


def create_research_agent(
    model: str = 'gemini-2.0-flash-001',
    name: str = 'research_agent',
    rag_corpus: Optional[str] = None
) -> Agent:
    """
    Create a specialized Research Agent with external data collection tools.

    This agent focuses on:
    - Web search across news, official, academic sources
    - Social media monitoring (Reddit, Twitter, etc.)
    - Live API queries (311, traffic, weather)
    - Media content collection and screenshot capture
    - Storing findings in RAG for future investigations
    """

    # Use pre-built tool objects from research_tools
    tools = [
        web_search,
        collect_media_content,
        save_investigation_screenshot,
        list_investigation_artifacts,
        # Add the newly implemented tools
        FunctionTool(search_social_media_func),
        FunctionTool(query_live_apis_func),
    ]

    # Add RAG retrieval tool if corpus is provided
    rag_tool = create_rag_retrieval_tool(rag_corpus)
    if rag_corpus and rag_tool:
        tools.append(rag_tool)
        logger.info(
            f"Research agent initialized with RAG corpus: {rag_corpus}")

    # Create the agent with comprehensive instructions
    agent = Agent(
        model=model,
        name=name,
        instruction=return_research_instructions(),
        tools=tools
    )

    logger.info(f"Created Research Agent '{name}' with {len(tools)} tools")
    return agent
