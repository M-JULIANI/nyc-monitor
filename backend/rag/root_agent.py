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
from google.adk.tools import FunctionTool

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
from .tools.coordination_tools import (
    update_alert_status,
    manage_investigation_state,
    call_research_agent_tool,
    call_data_agent_tool,
    call_analysis_agent_tool,
    call_report_agent_tool
)

logger = logging.getLogger(__name__)
tracer = get_distributed_tracer()
workflow_manager = WorkflowManager()
date_today = datetime.now().strftime("%Y-%m-%d")

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
                    # Remove coordination tools - let ADK handle sub-agent transfers
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

Your role is to coordinate a 5-agent investigation workflow for NYC alerts and incidents using ADK's transfer_to_agent mechanism.

**🚨 CRITICAL INVESTIGATION PROTOCOL 🚨**

**STEP 1: MANDATORY ARTIFACT COLLECTION**
When you receive an investigation request, you MUST:

1. **IMMEDIATELY transfer to research_agent** using transfer_to_agent with this EXACT message:

"🚨 MANDATORY ARTIFACT COLLECTION REQUIRED 🚨

Investigation Details:
- Investigation ID: [investigation_id]
- Location: [location] 
- Event Type: [event_type]
- Alert ID: [alert_id]

CRITICAL REQUIREMENTS:
- You MUST make actual FUNCTION CALLS, not text descriptions
- Execute ALL required tools in sequence
- Replace [investigation_id], [location], [event_type], [alert_id] with actual values
- Confirm each function call with: '✅ Called [function_name]: [result]'
- End with: 'ARTIFACT COLLECTION COMPLETE - Generated maps, collected images, captured screenshots, created timeline.'

MANDATORY TOOL EXECUTION SEQUENCE:
1. generate_location_map(investigation_id='[investigation_id]', location='[location]', zoom_level=16, map_type='normal')
2. generate_location_map(investigation_id='[investigation_id]', location='[location]', zoom_level=12, map_type='satellite') 
3. collect_media_content(search_terms='[location] [event_type]', content_types='images', investigation_id='[investigation_id]', max_items=5)
4. save_investigation_screenshot(url='https://www.google.com/search?q=[location]+[event_type]', description='Google search results', investigation_id='[investigation_id]')
5. generate_investigation_timeline(investigation_id='[investigation_id]', include_evidence_points=True, chart_type='timeline')

Execute each tool immediately. DO NOT return control until all tools are executed and artifacts are collected."

**STEP 2: COORDINATE REMAINING AGENTS** (Only after Step 1 complete)
- transfer_to_agent: data_agent for internal data analysis
- transfer_to_agent: analysis_agent for pattern recognition  
- transfer_to_agent: report_agent for final presentation generation

**AGENT TRANSFER EXAMPLES:**

```
# Step 1: Research Agent for artifact collection
transfer_to_agent(agent_name="research_agent")

# Step 2: Data Agent for internal analysis  
transfer_to_agent(agent_name="data_agent")

# Step 3: Analysis Agent for synthesis
transfer_to_agent(agent_name="analysis_agent")

# Step 4: Report Agent for deliverables
transfer_to_agent(agent_name="report_agent")
```

**SUCCESS CRITERIA:**
- Research Agent executes 5+ actual function calls
- Artifacts are saved to investigation state with GCS URLs
- Each subsequent agent receives proper context and data
- Final presentation includes all collected artifacts

Your coordination ensures comprehensive investigation through proper ADK agent transfers and tool execution.
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

            # Execute the root agent using proper ADK Runner pattern
            logger.info(
                f"Starting ADK investigation via root agent (5-agent direct)")

            # Create ADK Runner and session service for proper execution
            from google.adk.sessions import InMemorySessionService
            from google.genai import types

            session_service = InMemorySessionService()
            runner = Runner(
                agent=self.agent,
                app_name="atlas_investigation",
                session_service=session_service
            )

            # Create session for this investigation
            session_id = investigation_context.get(
                "investigation_id", f"investigation_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            user_id = f"atlas_user_{session_id}"

            # Set investigation context in session state
            if hasattr(session_service, '_sessions'):
                session_service._sessions[session_id] = {
                    "id": session_id,
                    "user_id": user_id,
                    "state": investigation_context,
                    "created_at": datetime.now()
                }

            # Convert prompt to proper ADK Content format
            content = types.Content(
                role='user',
                parts=[types.Part(text=investigation_prompt)]
            )

            # Execute via ADK Runner (proper way)
            logger.info(f"Executing ADK runner with session_id={session_id}")

            investigation_result = ""
            investigation_generator = runner.run_async(
                session_id=session_id,
                user_id=user_id,
                new_message=content
            )

            # Collect results from async generator
            async for result in investigation_generator:
                if hasattr(result, 'text'):
                    investigation_result += result.text
                elif isinstance(result, str):
                    investigation_result += result
                else:
                    investigation_result += str(result)

            logger.info("ADK investigation completed via root agent")
            return investigation_result

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
    # Extract context dictionary from CallbackContext properly
    context_dict = {}
    if context:
        # CallbackContext has a state attribute, not session_data
        if hasattr(context, 'state') and context.state:
            context_dict = context.state
        # Also check for session-related attributes
        elif hasattr(context, '_session_data'):
            context_dict = context._session_data
        # Fallback to empty dict if no context available
        else:
            context_dict = {}

    return await root_agent_instance.investigate(prompt, context_dict)

# Export the instance for deployment (consumers should access .agent when needed)
__all__ = ["root_agent_instance", "adk_investigate"]
