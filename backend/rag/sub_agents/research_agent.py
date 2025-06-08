"""Research agent for external data collection with artifact support."""

import os
from typing import Optional
from google.adk.agents import Agent
from ..prompts.research import return_research_instructions
from ..tools.research_tools import (
    web_search,
    collect_media_content,
    save_investigation_screenshot,
    list_investigation_artifacts
)
from ..tools.research_tools import create_rag_retrieval_tool


def create_research_agent(rag_corpus: Optional[str] = None) -> Agent:
    """Create the research agent with artifact-capable tools and RAG access."""
    tools = [
        web_search,
        collect_media_content,
        save_investigation_screenshot,
        list_investigation_artifacts,
        # TODO: Add more tools as implemented
        # search_social_media,
        # query_live_apis,
    ]

    # Add RAG tool for accessing existing corpus data
    rag_tool = create_rag_retrieval_tool(rag_corpus)
    if rag_corpus and rag_tool:
        tools.append(rag_tool)

    return Agent(
        model=os.getenv("RESEARCH_AGENT_MODEL", "gemini-2.0-flash-001"),
        name="research_agent",
        instruction=return_research_instructions() + """

When collecting data, save any images, screenshots, or documents as artifacts.
Use descriptive filenames like "social_media_image_1.jpg" or "news_article_screenshot.png".
Always specify the correct MIME type when saving artifacts.

Available tools:
- RAG retrieval: Search existing corpus data for relevant background information
- Web search: Find current information online
- Artifact tools: Save images, screenshots, and documents as evidence
- collect_media_content: Save images and media files as artifacts
- save_investigation_screenshot: Take screenshots of webpages for evidence
- list_investigation_artifacts: List all artifacts collected so far

Investigation strategy:
1. First check the existing corpus for relevant background information using RAG
2. Search for current/live information using web search
3. Collect and save relevant media and screenshots as artifacts
4. Synthesize findings from both corpus data and live searches
""",
        tools=tools
    )
