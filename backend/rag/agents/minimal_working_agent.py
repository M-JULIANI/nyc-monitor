#!/usr/bin/env python3
"""
Minimal Working Agent for NYC Atlas Investigations.
This agent follows the proven workflow pattern that successfully collects 8+ artifacts
AND performs web searches to gather relevant findings.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.genai import types

logger = logging.getLogger(__name__)


class MinimalWorkingAgent:
    """
    Minimal working agent that follows the proven artifact collection workflow
    with web search capabilities for gathering relevant findings.

    This agent is designed to:
    1. Perform web searches to gather relevant findings
    2. Create investigation state
    3. Generate 2 satellite maps (close + wide zoom)  
    4. Collect images from multiple search queries
    5. Create presentation with all artifacts and findings
    """

    def __init__(self):
        """Initialize the minimal working agent."""
        self.agent = None
        self._setup_agent()

    def _setup_agent(self):
        """Set up the ADK agent with the proven workflow tools including web search."""
        try:
            # Import the working tools from our proven workflow
            from ..tools.map_tools import generate_location_map
            from ..tools.research_tools import collect_media_content, web_search
            from ..tools.report_tools import create_slides_presentation

            # Create the agent with enhanced instructions including web search
            self.agent = Agent(
                model="gemini-2.0-flash-exp",
                name="minimal_working_agent",
                instruction=self._get_system_instructions(),
                tools=[
                    web_search,  # Added web search tool
                    generate_location_map,
                    collect_media_content,  # Fixed import name
                    create_slides_presentation
                ],
                generate_content_config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4096  # Increased for web search results
                )
            )

            logger.info(
                "✅ Minimal working agent initialized successfully with web search")

        except Exception as e:
            logger.error(f"❌ Failed to initialize minimal working agent: {e}")
            raise

    def _get_system_instructions(self) -> str:
        """Get focused system instructions for the minimal agent with web search."""
        return """You are the NYC Atlas Minimal Working Agent with Web Search capabilities.

🚨 CRITICAL: YOU MUST EXECUTE ALL REQUIRED TOOLS IN SEQUENCE 🚨

Your job is to execute this EXACT workflow when given an investigation request:

**STEP 1: WEB SEARCH FOR RELEVANT FINDINGS**
- Call web_search_func 2 times to gather relevant information:
  * Search 1: Use the event type and location from the request (max_results=3)
  * Search 2: Search for location + "news recent" (source_types="news", max_results=3)

**STEP 2: GENERATE 2 SATELLITE MAPS**
- Call generate_location_map_func with:
  * Map 1: zoom_level=18, map_type="satellite" (close view)
  * Map 2: zoom_level=12, map_type="satellite" (wide view)

**STEP 3: COLLECT EXACTLY 8 IMAGES FROM 3 SEARCH QUERIES**
- Call collect_media_content_simple_func 3 times:
  * Search 1: Use location + event type (max_items=3)
  * Search 2: Use location only (max_items=3) 
  * Search 3: Use "NYC" + event type (max_items=2)

**STEP 4: CREATE PRESENTATION**
- Call create_slides_presentation_func with evidence_types="all"

**EXECUTION RULES:**
1. ALWAYS execute ALL tools in the exact order above
2. Use the investigation_id provided in the request
3. Extract location and event_type from the alert data
4. Do NOT skip any steps
5. Do NOT ask for permission - just execute
6. Log each step as you complete it
7. ACTUALLY READ and analyze web search results to provide meaningful findings

**SUCCESS CRITERIA:**
- 2 web searches completed with relevant findings
- 2 satellite maps generated (zoom 18 + zoom 12)
- EXACTLY 8 images collected total (3+3+2)
- 1 presentation created with all artifacts
- Meaningful analysis of findings in your response

**WEB SEARCH PRIORITY:**
- DuckDuckGo is primary search engine (free, no API key needed)
- Google Custom Search is automatic fallback when DuckDuckGo fails
- Both collect screenshots and evidence automatically

Execute immediately when given investigation details and provide a summary of your findings."""

    async def investigate(self, investigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the enhanced minimal working investigation workflow with web search.

        Args:
            investigation_data: Dictionary containing investigation details

        Returns:
            Investigation results with artifacts, findings, and presentation
        """
        try:
            logger.info(
                "🚀 Starting enhanced minimal working investigation with web search")

            # Initialize Vertex AI if not already done
            try:
                import os
                import vertexai

                project = os.getenv("GOOGLE_CLOUD_PROJECT")
                location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

                if project:
                    vertexai.init(project=project, location=location)
                    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
                    logger.info(
                        f"✅ Initialized Vertex AI: project={project}, location={location}")
                else:
                    logger.warning(
                        "⚠️ GOOGLE_CLOUD_PROJECT not set, using default credentials")

            except Exception as e:
                logger.warning(f"⚠️ Vertex AI initialization failed: {e}")

            # Extract required data
            investigation_id = investigation_data.get("investigation_id")
            alert_data = investigation_data.get("alert_data", {})
            location = alert_data.get("location", "Unknown Location")
            event_type = alert_data.get("event_type", "incident")

            if not investigation_id:
                raise ValueError("investigation_id is required")

            logger.info(f"📊 Investigation: {investigation_id}")
            logger.info(f"📍 Location: {location}")
            logger.info(f"🎯 Event Type: {event_type}")

            # Create the enhanced investigation message for the agent
            investigation_message = f"""
🚨 INVESTIGATION REQUEST - EXECUTE ENHANCED WORKFLOW IMMEDIATELY 🚨

Investigation Details:
- Investigation ID: {investigation_id}
- Location: {location}
- Event Type: {event_type}
- Alert Data: {alert_data}

EXECUTE ALL REQUIRED TOOLS NOW IN SEQUENCE:

1. **WEB SEARCH PHASE** - Gather relevant findings:
   - Search for "{event_type} {location}" to find specific information
   - Search for "{location} news recent" to find recent news coverage

2. **MAP GENERATION PHASE** - Create location context:
   - Generate satellite map with zoom level 18 (close view)
   - Generate satellite map with zoom level 12 (wide view)

3. **IMAGE COLLECTION PHASE** - Gather EXACTLY 8 images:
   - Collect images for "{location} {event_type}" (max_items=3)
   - Collect images for "{location}" (max_items=3)
   - Collect images for "NYC {event_type}" (max_items=2)

4. **PRESENTATION PHASE** - Create comprehensive report:
   - Generate presentation with all collected artifacts and findings

🎯 **CRITICAL INSTRUCTIONS:**
- ACTUALLY EXECUTE each tool - do not just describe what you would do
- READ and ANALYZE the web search results to extract key findings
- PROVIDE a meaningful summary of what you discovered
- DO NOT skip any steps
- START IMMEDIATELY - NO CONFIRMATION NEEDED
- Collect EXACTLY 8 images total (3+3+2)

Your goal is to provide both comprehensive artifact collection AND meaningful investigative findings.
"""

            # Execute the agent workflow
            logger.info("🔧 Executing enhanced agent workflow...")

            # Use the ADK Runner to execute the agent
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService

            session_service = InMemorySessionService()
            runner = Runner(
                agent=self.agent,
                app_name="minimal_working_agent",
                session_service=session_service
            )

            # Run the investigation
            results = []
            session_id = f"investigation_{investigation_id}"
            user_id = "minimal_working_agent"

            # Create session before running
            session = session_service.create_session(
                session_id=session_id,
                user_id=user_id,
                app_name="minimal_working_agent"
            )

            logger.info(f"✅ Created session: {session_id}")

            # Create the message as types.Content
            content = types.Content(
                role='user',
                parts=[types.Part(text=investigation_message)]
            )

            async for event in runner.run_async(
                session_id=session_id,
                user_id=user_id,
                new_message=content
            ):
                # Handle different types of events from the ADK runner
                if hasattr(event, 'text') and event.text:
                    results.append(event.text)
                    logger.info(f"📤 Agent response: {event.text[:100]}...")
                elif hasattr(event, 'content'):
                    # Handle Content objects properly
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                results.append(part.text)
                                logger.info(
                                    f"📤 Agent text: {part.text[:100]}...")
                            elif hasattr(part, 'function_call') and part.function_call:
                                logger.info(
                                    f"📤 Agent function call: {part.function_call.name}")
                    else:
                        results.append(str(event.content))
                        logger.info(
                            f"📤 Agent content: {str(event.content)[:100]}...")
                elif isinstance(event, str):
                    results.append(event)
                    logger.info(f"📤 Agent response: {event[:100]}...")
                else:
                    # Log the event type for debugging
                    logger.info(
                        f"📤 Agent event type: {type(event)}, content: {str(event)[:100]}...")
                    results.append(str(event))

            # Combine all results
            full_response = "\n".join(
                results) if results else "No response from agent"

            # Get the final investigation state to check artifacts
            from ..investigation.state_manager import state_manager
            final_state = state_manager.get_investigation(investigation_id)

            if final_state:
                total_artifacts = len(final_state.artifacts)

                # Count artifact types
                artifact_types = {}
                for artifact in final_state.artifacts:
                    artifact_type = artifact.get('type', 'unknown')
                    artifact_types[artifact_type] = artifact_types.get(
                        artifact_type, 0) + 1

                logger.info(f"📊 Final artifact count: {total_artifacts}")
                logger.info(f"📋 Artifact breakdown: {artifact_types}")

                # Enhanced success criteria including web search results
                maps_count = artifact_types.get('map_image', 0)
                images_count = artifact_types.get('image', 0)
                screenshots_count = artifact_types.get('screenshot', 0)

                # Check if web searches were performed (should have screenshots from web search)
                web_search_performed = screenshots_count > 0 or "web_search" in full_response.lower()

                success = (
                    maps_count >= 2 and
                    images_count >= 8 and
                    web_search_performed and
                    total_artifacts >= 8
                )

                return {
                    "success": success,
                    "investigation_id": investigation_id,
                    "total_artifacts": total_artifacts,
                    "artifact_breakdown": artifact_types,
                    "maps_generated": maps_count,
                    "images_collected": images_count,
                    "screenshots_collected": screenshots_count,
                    "web_search_performed": web_search_performed,
                    "agent_response": full_response,
                    "workflow_status": "completed" if success else "partial",
                    "summary": f"Generated {maps_count} maps, collected {images_count} images, {screenshots_count} screenshots, total {total_artifacts} artifacts. Web search: {'✅' if web_search_performed else '❌'}"
                }
            else:
                logger.warning(
                    "⚠️ Could not retrieve final investigation state")
                return {
                    "success": False,
                    "investigation_id": investigation_id,
                    "error": "Could not retrieve investigation state",
                    "agent_response": full_response,
                    "workflow_status": "failed"
                }

        except Exception as e:
            logger.error(
                f"❌ Enhanced minimal working investigation failed: {e}")
            return {
                "success": False,
                "investigation_id": investigation_data.get("investigation_id", "unknown"),
                "error": str(e),
                "workflow_status": "failed",
                "summary": f"Investigation failed: {str(e)}"
            }


# Global instance for use by the endpoint
minimal_working_agent = MinimalWorkingAgent()


async def execute_minimal_investigation(investigation_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an enhanced minimal working investigation using the proven workflow with web search.

    This function is called by the /investigate endpoint.

    Args:
        investigation_data: Investigation details including investigation_id and alert_data

    Returns:
        Investigation results with web search findings, artifacts, and presentation
    """
    return await minimal_working_agent.investigate(investigation_data)
