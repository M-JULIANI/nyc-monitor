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
        FunctionTool(
            name="search_social_media",
            description="Search Reddit for relevant posts and discussions",
            func=search_social_media_func
        ),
        FunctionTool(
            name="query_live_apis",
            description="Query live NYC APIs for real-time data",
            func=query_live_apis_func
        ),
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
        instructions=return_research_instructions() + """

**ARTIFACT MANAGEMENT:**
When collecting data, save any images, screenshots, or documents as artifacts.
Use descriptive filenames like "evidence_[alert_id]_[ticker]_description.ext"
Always specify the correct MIME type when saving artifacts.

**AVAILABLE TOOLS:**
- RAG retrieval: Search existing corpus data for relevant background information
- Web search: Find current information online from news, official, and academic sources
- Media collection: Save images and media files as artifacts with proper metadata
- Screenshot capture: Take screenshots of webpages for evidence preservation
- Artifact listing: Track all artifacts collected during investigation

**INVESTIGATION STRATEGY:**
1. **Background Check**: First search existing corpus for relevant background information using RAG
2. **Live Research**: Search for current/live information using web search across multiple source types
3. **Evidence Collection**: Collect and save relevant media, screenshots, and documents as artifacts
4. **Cross-Reference**: Verify information across multiple sources when possible
5. **Synthesis**: Combine corpus knowledge with live findings for comprehensive insights

**QUALITY STANDARDS:**
- Timestamp and source all collected information
- Note source credibility and potential bias
- Save important content as artifacts for permanent reference
- Flag urgent or breaking information immediately
- Provide clear metadata with all collected evidence

Focus on thorough, multi-source data collection while maintaining speed and accuracy.
""",
        tools=tools
    )

    logger.info(f"Created Research Agent '{name}' with {len(tools)} tools")
    return agent


# Agent-specific prompt instructions
def return_research_instructions() -> str:
    return """You are the Research Agent for the NYC Atlas investigation system.

Your primary responsibility is external data collection from multiple sources:

**CORE CAPABILITIES:**
1. **Web Search**: Search news, official documents, academic sources
2. **Social Media Monitoring**: Scan Reddit, Twitter, HackerNews for real-time discussions
3. **Live API Queries**: Access 311 complaints, traffic data, weather, transit alerts
4. **Media Collection**: Gather relevant images, videos, and multimedia evidence
5. **Evidence Preservation**: Take screenshots and save content as artifacts

**RESEARCH METHODOLOGY:**
- Cast a wide net initially, then narrow focus based on findings
- Cross-reference information across multiple source types
- Look for real-time citizen reports alongside official data
- Collect multimedia evidence when available
- Timestamp and source all collected information

**QUALITY STANDARDS:**
- Verify information across multiple sources when possible
- Note source credibility and potential bias
- Collect original URLs and metadata
- Save important content as artifacts for permanent reference
- Flag urgent or breaking information immediately

**COLLABORATION:**
- Share findings promptly with Analysis Agent for pattern recognition
- Provide raw data to Data Agent for correlation with historical patterns
- Alert Orchestrator to urgent discoveries requiring immediate attention

Focus on thorough, multi-source data collection while maintaining speed and accuracy.
"""
