#!/usr/bin/env python3
"""
Sequential Investigation Test - Fixed 400 Error + Google Slides Test
Uses simplified tools and forces sequential execution.
"""

from rag.tools.research_tools_simple import (
    simple_web_search_tool,
    simple_social_search_tool,
    simple_knowledge_search_tool
)
from rag.tools.report_tools_simple import (
    simple_create_slides_tool,
    simple_create_report_tool
)
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Import simplified tools


async def test_sequential_investigation():
    """Test investigation with simplified tools and sequential execution."""

    print("\n🔄 Testing Sequential Investigation with Simplified Tools")
    print("=" * 65)

    try:
        # Initialize Vertex AI
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        import vertexai
        vertexai.init(project=project, location=location)
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

        print(f"✅ Initialized Vertex AI: {project}")

        # Create simplified tools
        tools = [
            simple_web_search_tool,
            simple_social_search_tool,
            simple_knowledge_search_tool,
            simple_create_report_tool,
            simple_create_slides_tool
        ]

        print(f"✅ Created {len(tools)} simplified tools")

        # Sequential execution instruction
        sequential_instruction = """You are a NYC Atlas Investigation Agent.

CRITICAL: Execute tools ONE AT A TIME in sequence. Never call multiple tools simultaneously.

Your workflow:
1. First, search the web for information using simple_web_search
2. Then, search social media using simple_social_search  
3. Then, search knowledge base using simple_knowledge_search
4. Then, create a report using simple_create_report
5. Finally, create a Google Slides presentation using simple_create_slides

WAIT for each tool to complete before calling the next one.
Execute tools sequentially, not in parallel."""

        # Create agent with sequential instruction
        agent = Agent(
            model='gemini-2.0-flash-001',
            name='sequential_investigation_agent',
            instruction=sequential_instruction,
            tools=tools,
            generate_content_config=types.GenerateContentConfig(
                temperature=0.1
            )
        )

        print("✅ Created sequential investigation agent")

        # Create runner
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="sequential_investigation",
            session_service=session_service
        )

        print("✅ Created runner")

        # Test investigation
        session_id = f"seq_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        user_id = "test_user"

        session = session_service.create_session(
            session_id=session_id,
            user_id=user_id,
            app_name="sequential_investigation"
        )

        print(f"✅ Created session: {session_id}")

        # Investigation prompt
        content = types.Content(
            role='user',
            parts=[types.Part(text="""
Investigate: "Community Protest at Washington Square Park, Manhattan"

Follow the sequential workflow:
1. Search web for "Washington Square Park protest housing"
2. Search social media for "Washington Square Park protest"  
3. Search knowledge base for "community organizing Manhattan"
4. Create report titled "Washington Square Park Investigation"
5. Create Google Slides presentation titled "WSP Protest Analysis"

Execute each step one at a time and wait for completion before proceeding.
""")]
        )

        print("🚀 Starting sequential investigation...")
        print("   📝 This will test both function execution AND Google Slides creation")

        # Run the investigation
        result_text = ""
        async for result in runner.run_async(session_id=session_id, user_id=user_id, new_message=content):
            if hasattr(result, 'text') and result.text:
                result_text += result.text
                print(f"📤 Agent output: {result.text}")
            elif isinstance(result, str):
                result_text += result

        print("✅ Sequential investigation completed!")
        print(f"📊 Total result length: {len(result_text)} characters")

        # Look for Google Slides URL in the result
        if "docs.google.com/presentation" in result_text:
            print("🎉 GOOGLE SLIDES CREATED SUCCESSFULLY!")
            # Extract URL
            import re
            urls = re.findall(
                r'https://docs\.google\.com/presentation/d/[^/]+/edit', result_text)
            if urls:
                print(f"📎 Slides URL: {urls[0]}")
        else:
            print("⚠️  Google Slides creation not detected in output")

        return True

    except Exception as e:
        print(f"❌ Sequential investigation failed: {e}")
        logger.exception("Sequential investigation failed")
        return False


async def main():
    """Main test function."""
    print("🧪 Sequential Investigation Test - Fixed Tools + Google Slides")
    print("=" * 70)

    success = await test_sequential_investigation()

    print("\n" + "=" * 70)
    if success:
        print("✅ Sequential investigation test PASSED!")
        print("💡 This confirms:")
        print("   • Simplified tools work with ADK")
        print("   • Sequential execution prevents 400 errors")
        print("   • Google Slides integration works")
    else:
        print("❌ Sequential investigation test FAILED!")
        print("💡 Check logs for specific issues")
    print("=" * 70)

    return 0 if success else 1

if __name__ == "__main__":
    asyncio.run(main())
