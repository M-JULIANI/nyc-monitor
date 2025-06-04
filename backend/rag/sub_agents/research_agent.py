"""Research agent for external data collection with artifact support."""

import os
from google.adk.agents import Agent
from ..prompts.research import return_research_instructions
from ..tools.research_tools import (
    web_search,
    collect_media_content,
    save_investigation_screenshot,
    list_investigation_artifacts
)


def create_research_agent() -> Agent:
    """Create the research agent with artifact-capable tools."""
    return Agent(
        model=os.getenv("RESEARCH_AGENT_MODEL", "gemini-2.0-flash-001"),
        name="research_agent",
        instruction=return_research_instructions() + """

When collecting data, save any images, screenshots, or documents as artifacts.
Use descriptive filenames like "social_media_image_1.jpg" or "news_article_screenshot.png".
Always specify the correct MIME type when saving artifacts.

Available artifact tools:
- collect_media_content: Save images and media files as artifacts
- save_investigation_screenshot: Take screenshots of webpages for evidence
- list_investigation_artifacts: List all artifacts collected so far
""",
        tools=[
            web_search,
            collect_media_content,
            save_investigation_screenshot,
            list_investigation_artifacts,
            # TODO: Add more tools as implemented
            # search_social_media,
            # query_live_apis,
        ]
    )


# Create the research agent instance
research_agent = create_research_agent()
