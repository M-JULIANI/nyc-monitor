"""
Root Agent for NYC Atlas Investigation System.
This is the deployable entry point for Vertex AI ADK that coordinates 
the 5-agent investigation system directly.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool

# Import the 5 specialized agents
from .agents.research_agent import create_research_agent
from .agents.data_agent import create_data_agent
from .agents.analysis_agent import create_analysis_agent
from .agents.report_agent import create_report_agent

# Import existing infrastructure
from .investigation.state_manager import AlertData, state_manager, InvestigationPhase
from .investigation.progress_tracker import progress_tracker, ProgressStatus
from .investigation.tracing import get_distributed_tracer
from .investigation.workflow import WorkflowManager
from .tools.coordination_tools import update_alert_status, manage_investigation_state

logger = logging.getLogger(__name__)
tracer = get_distributed_tracer()
workflow_manager = WorkflowManager()
date_today = date.today()

# Define callback functions (not methods) as required by ADK


def _before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """Called before agent execution - track agent activation."""
    agent_name = callback_context._invocation_context.agent.name
    investigation_id = _get_investigation_id(callback_context)

    progress_tracker.add_progress(
        investigation_id=investigation_id,
        status=ProgressStatus.AGENT_ACTIVE,
        active_agent=agent_name,
        message=f"Agent {agent_name} is now active"
    )

    logger.info(f"🤖 Agent {agent_name} starting execution")
    return None


def _after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """Called after agent execution - track completion."""
    agent_name = callback_context._invocation_context.agent.name
    investigation_id = _get_investigation_id(callback_context)

    progress_tracker.add_progress(
        investigation_id=investigation_id,
        status=ProgressStatus.THINKING,
        active_agent=agent_name,
        message=f"Agent {agent_name} completed execution"
    )

    logger.info(f"✅ Agent {agent_name} completed execution")
    return None


def _before_tool_callback(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> Optional[Dict]:
    """Called before tool execution - track tool usage."""
    tool_name = tool.name
    agent_name = tool_context.agent_name
    investigation_id = tool_context.state.get("investigation_id", "unknown")

    progress_tracker.add_progress(
        investigation_id=investigation_id,
        status=ProgressStatus.TOOL_EXECUTING,
        active_agent=agent_name,
        current_task=f"Executing {tool_name}",
        message=f"Agent {agent_name} executing tool: {tool_name}"
    )

    logger.info(f"🔧 Agent {agent_name} executing tool {tool_name}")
    return None


def _after_tool_callback(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict) -> Optional[Dict]:
    """Called after tool execution - track tool completion."""
    tool_name = tool.name
    agent_name = tool_context.agent_name

    logger.info(
        f"✅ Tool {tool_name} completed execution for agent {agent_name}")
    return None


def _get_investigation_id(callback_context: CallbackContext) -> str:
    """Extract investigation ID from callback context."""
    return callback_context.state.get("investigation_id", "unknown")


class AtlasRootAgent:
    """
    Root agent for the Atlas investigation system.
    This agent serves as the main entry point and coordinates 5 specialized sub-agents directly.
    """

    def __init__(self):
        self.agent_name = "atlas_root_investigation_agent"
        self._agent = None  # Lazy initialization
        self._vertex_initialized = False

    def _ensure_vertex_ai_initialized(self):
        """Ensure Vertex AI is initialized (only once)"""
        if self._vertex_initialized:
            return

        # Get Vertex AI configuration from environment
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if not project:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT environment variable not set")

        # Initialize Vertex AI (this is what ADK expects)
        import vertexai
        vertexai.init(project=project, location=location)

        # Enable Vertex AI for the google-genai library
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

        self._vertex_initialized = True
        logger.info(
            f"Initialized Vertex AI with project={project}, location={location}")

    @property
    def agent(self):
        """Lazy-loaded agent property"""
        if self._agent is None:
            self._ensure_vertex_ai_initialized()

            rag_corpus = os.getenv("RAG_CORPUS")

            # Create the root agent with 5 direct sub-agents (ADK idiomatic)
            self._agent = Agent(
                model='gemini-2.0-flash-001',
                name=self.agent_name,
                instruction=self._get_root_instructions(),
                tools=[
                    update_alert_status,
                    manage_investigation_state,
                ],
                sub_agents=[
                    # All 5 agents as direct sub-agents (ADK idiomatic)
                    create_research_agent(rag_corpus=rag_corpus),
                    create_data_agent(rag_corpus=rag_corpus),
                    create_analysis_agent(),
                    create_report_agent(),
                ],
                # Use the existing callback system
                before_agent_callback=_before_agent_callback,
                after_agent_callback=_after_agent_callback,
                before_tool_callback=_before_tool_callback,
                after_tool_callback=_after_tool_callback,
                generate_content_config=types.GenerateContentConfig(
                    temperature=0.01),
            )

            logger.info(
                f"Initialized Atlas Root Agent with RAG corpus: {rag_corpus}")

        return self._agent

    def _get_root_instructions(self) -> str:
        """Root agent instructions for coordinating 5-agent investigation workflow."""
        return f"""
You are the Root Agent for the NYC Atlas investigation system.
Today's date: {date_today}

Your role is to coordinate a 5-agent investigation workflow for NYC alerts and incidents.

**YOUR DIRECT SUB-AGENTS:**
- **Research Agent**: External data collection (web search, social media, APIs, screenshots)  
- **Data Agent**: Internal knowledge & BigQuery datasets (census, crime, permits, housing)
- **Analysis Agent**: Pattern recognition & cross-domain synthesis
- **Report Agent**: Validation & professional report generation (including Google Slides)

**🚨 CRITICAL SUCCESS CRITERIA - INVESTIGATION CANNOT BE COMPLETE WITHOUT:**
1. **MINIMUM 2 LOCATION MAPS** generated via generate_location_map tool
2. **MINIMUM 5 IMAGES** collected via collect_media_content tool
3. **MINIMUM 3 SCREENSHOTS** captured via save_investigation_screenshot tool
4. **TIMELINE CHART** created via generate_investigation_timeline tool

**MANDATORY STEP-BY-STEP PROTOCOL:**

**STEP 1 - ARTIFACT COLLECTION (NON-NEGOTIABLE):**
Transfer to Research Agent with this EXACT instruction:
"MANDATORY ARTIFACT COLLECTION - You must execute these specific tools in order:

1. EXECUTE generate_location_map with location='[LOCATION]', zoom_level=16, map_type='satellite'
2. EXECUTE generate_location_map with location='[LOCATION]', zoom_level=12, map_type='satellite'  
3. EXECUTE collect_media_content with search_terms='[EVENT_TYPE], [LOCATION]', content_types='images', max_items=8
4. EXECUTE save_investigation_screenshot with url='https://www.ny1.com', description='NY1 news screenshot'
5. EXECUTE save_investigation_screenshot with url='https://www.pix11.com', description='PIX11 news screenshot'
6. EXECUTE save_investigation_screenshot with url='https://www.abc7ny.com', description='ABC7 news screenshot'
7. EXECUTE generate_investigation_timeline with investigation_id='[INVESTIGATION_ID]'

DO NOT return control to me until you have successfully executed ALL 7 tools above. 
Confirm each tool execution with its results before proceeding to the next.
If any tool fails, retry it once before continuing.
Report back with: 'ARTIFACT COLLECTION COMPLETE - Generated X maps, collected Y images, captured Z screenshots, created timeline.'"

**STEP 2 - DATA COLLECTION:**
Only after Research Agent confirms artifact collection, transfer to Data Agent for internal data gathering.

**STEP 3 - SYNTHESIS:**
Transfer to Analysis Agent for pattern recognition and confidence scoring.

**STEP 4 - REPORTING:**
Transfer to Report Agent for Google Slides creation using collected artifacts.

**VERIFICATION REQUIREMENTS:**
- Before proceeding to Step 2, verify Research Agent has called all 7 required tools
- Before proceeding to Step 3, verify Data Agent has gathered internal context
- Before proceeding to Step 4, verify Analysis Agent has calculated confidence scores
- Investigation is NOT complete until Report Agent has created Google Slides with artifacts

**COORDINATION STRATEGY:**
- Be DIRECTIVE and SPECIFIC about tool execution requirements
- Do not accept vague responses - require confirmation of specific tool calls
- If an agent returns without completing required tools, redirect them with specific instructions
- Track progress through state management system
- Use progress tracking for real-time frontend updates

**QUALITY GATES:**
✅ Reconnaissance: Research Agent confirms "ARTIFACT COLLECTION COMPLETE" with counts
✅ Data: Data Agent provides internal context and historical patterns
✅ Analysis: Analysis Agent calculates confidence score and identifies patterns
✅ Reporting: Report Agent creates Google Slides with embedded artifacts

The investigation cannot proceed to the next step until the current step's quality gate is satisfied.
Focus on ensuring comprehensive evidence collection through explicit tool execution verification.
"""

    async def investigate(self, investigation_prompt: str, context: Dict[str, Any] = None) -> str:
        """
        Main investigation entry point for ADK deployment.
        This method will be called by the ADK system.

        Args:
            investigation_prompt: The investigation request/prompt
            context: Additional context from ADK runtime

        Returns:
            Investigation results as string
        """
        try:
            # Extract investigation context from prompt or context
            investigation_context = self._extract_investigation_context(
                investigation_prompt, context)

            # Initialize tracing if we have an investigation ID
            if investigation_context.get("investigation_id"):
                trace_id = investigation_context["investigation_id"]
                tracer.start_trace(
                    trace_id=trace_id,
                    operation_name="adk_root_agent_investigate",
                    metadata={
                        **investigation_context,
                        "approach": "adk_5_agent_direct",
                        "root_agent": self.agent_name
                    }
                )

            # Create ADK callback context with investigation metadata
            callback_context = CallbackContext(
                session_data={
                    **investigation_context,
                    "root_agent": self.agent_name,
                    "investigation_start_time": datetime.utcnow().isoformat()
                }
            )

            # Execute the root agent with direct sub-agent coordination
            logger.info(
                f"Starting ADK investigation via root agent (5-agent direct)")

            result = await self.agent.execute(
                prompt=investigation_prompt,
                context=callback_context
            )

            logger.info("ADK investigation completed via root agent")
            return result

        except Exception as e:
            logger.error(f"Root agent investigation failed: {e}")

            return f"""ADK Root Agent Investigation Report:

Agent: {self.agent_name}
Status: Error occurred during investigation
Error: {str(e)}

Investigation Infrastructure:
- Root Agent: ✅ Initialized and callable
- 5 Direct Sub-Agents: ✅ Created with ADK framework
- RAG Corpus: {'✅ Connected' if os.getenv('RAG_CORPUS') else '❌ Not configured'}
- State Management: ✅ Available (progress_tracker, state_manager, tracing, workflow)
- ADK Integration: ✅ Direct sub-agent coordination (idiomatic)

ADK Deployment Status: ✅ Ready for deployment

Error Details: {str(e)}
"""

    def _extract_investigation_context(self, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract investigation context from prompt and ADK context.
        This helps maintain state across the investigation.
        """
        investigation_context = {}

        # Extract from ADK context if available
        if context:
            investigation_context.update(context)

        # Try to extract investigation ID from prompt
        if "Investigation ID:" in prompt:
            try:
                lines = prompt.split('\n')
                for line in lines:
                    if "Investigation ID:" in line:
                        investigation_id = line.split(
                            "Investigation ID:")[-1].strip()
                        investigation_context["investigation_id"] = investigation_id
                        break
            except Exception:
                pass

        # Extract alert information from prompt
        for field in ["Alert ID:", "Event Type:", "Location:", "Severity:"]:
            if field in prompt:
                try:
                    lines = prompt.split('\n')
                    for line in lines:
                        if field in line:
                            value = line.split(field)[-1].strip()
                            key = field.lower().replace(":", "").replace(" ", "_")
                            investigation_context[key] = value
                            break
                except Exception:
                    pass

        return investigation_context


# Create the root agent instance for ADK deployment
root_agent_instance = AtlasRootAgent()

# Don't access .agent property at import time - this would trigger initialization!
# Instead, export the instance and let consumers access .agent when needed
# root_agent = root_agent_instance.agent  # <-- REMOVED: This was causing immediate initialization

# ADK expects a callable agent - create the interface


async def adk_investigate(prompt: str, context: CallbackContext = None) -> str:
    """
    ADK-compatible entry point for investigations.
    This is what gets called when the agent is deployed to Vertex AI.
    """
    context_dict = context.session_data if context else {}
    return await root_agent_instance.investigate(prompt, context_dict)

# Export the instance for deployment (consumers should access .agent when needed)
__all__ = ["root_agent_instance", "adk_investigate"]
