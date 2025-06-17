#!/usr/bin/env python3
"""
Simple test to isolate the 400 INVALID_ARGUMENT error.
This test uses minimal tools to determine if the issue is with complex function schemas.
"""

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools import FunctionTool
from google.adk.agents import Agent
from google.genai import types
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables first
env_file_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(env_file_path):
    load_dotenv(env_file_path)
    print(f"✅ Loaded environment variables from {env_file_path}")
else:
    print(f"❌ .env file not found at {env_file_path}")

# Configure simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def simple_test_tool(message: str) -> str:
    """A very simple tool to test basic functionality."""
    return f"✅ Simple tool executed with message: {message}"


def simple_search_tool(query: str, max_results: int = 5) -> dict:
    """A simple search tool with basic parameters."""
    return {
        "success": True,
        "query": query,
        "results": [
            {"title": f"Mock result {i+1} for {query}",
                "url": f"https://example.com/{i+1}"}
            for i in range(max_results)
        ]
    }


async def test_simple_agent():
    """Test a simple agent with basic tools to isolate the 400 error."""

    print("\n🔧 Testing Simple Agent Configuration")
    print("=" * 50)

    try:
        # Initialize Vertex AI
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if not project:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT environment variable not set")

        import vertexai
        vertexai.init(project=project, location=location)
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

        print(
            f"✅ Initialized Vertex AI: project={project}, location={location}")

        # Create simple tools
        tools = [
            FunctionTool(simple_test_tool),
            FunctionTool(simple_search_tool)
        ]

        print(f"✅ Created {len(tools)} simple tools")

        # Create a simple agent
        agent = Agent(
            model='gemini-2.0-flash-001',
            name='simple_test_agent',
            instruction="You are a simple test agent. Use the available tools to respond to user queries.",
            tools=tools,
            generate_content_config=types.GenerateContentConfig(
                temperature=0.1)
        )

        print("✅ Created simple agent")

        # Create runner
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="simple_test",
            session_service=session_service
        )

        print("✅ Created runner")

        # Test the agent with a simple prompt
        session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        user_id = "test_user"

        # Create session
        session = session_service.create_session(
            session_id=session_id,
            user_id=user_id,
            app_name="simple_test"
        )

        print(f"✅ Created session: {session_id}")

        # Simple test message
        content = types.Content(
            role='user',
            parts=[types.Part(
                text="Please use the simple_test_tool with message 'Hello World' and then search for 'test query' using the search tool.")]
        )

        print("🚀 Executing simple agent test...")

        # Run the agent
        result_text = ""
        async for result in runner.run_async(session_id=session_id, user_id=user_id, new_message=content):
            if hasattr(result, 'text'):
                result_text += result.text
            elif isinstance(result, str):
                result_text += result
            else:
                result_text += str(result)

        print("✅ Simple agent test completed successfully!")
        print(f"📤 Result: {result_text}")
        return True

    except Exception as e:
        print(f"❌ Simple agent test failed: {e}")
        logger.exception("Simple agent test failed")
        return False


async def main():
    """Main test function."""
    print("🧪 Simple Agent Test - Isolating 400 Error")
    print("=" * 60)

    success = await test_simple_agent()

    print("\n" + "=" * 60)
    if success:
        print("✅ Simple agent test PASSED - The issue is likely with complex tool schemas")
        print("💡 Next steps: Simplify the complex tools in the main investigation system")
    else:
        print("❌ Simple agent test FAILED - The issue is more fundamental")
        print("💡 Check Vertex AI configuration, ADK version, or API permissions")
    print("=" * 60)

    return 0 if success else 1

if __name__ == "__main__":
    asyncio.run(main())
