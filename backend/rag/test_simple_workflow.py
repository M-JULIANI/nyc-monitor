#!/usr/bin/env python3
"""
Simple workflow test to isolate and fix the core issues.
This bypasses all the complex ADK machinery to test basic tool execution.
"""

from dotenv import load_dotenv
import os
import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv("../../atlas-bootstrapped/.env")


def test_simple_tool_execution():
    """Test basic tool execution without ADK complexity."""

    print("🔧 SIMPLE TOOL EXECUTION TEST")
    print("=" * 50)

    # Test 1: Generate a map directly
    try:
        from rag.tools.map_tools import generate_location_map_func

        investigation_id = f"SIMPLE-TEST-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        location = "Washington Square Park, Manhattan"

        print(f"📍 Testing map generation:")
        print(f"   Investigation ID: {investigation_id}")
        print(f"   Location: {location}")

        result = generate_location_map_func(
            investigation_id=investigation_id,
            location=location,
            zoom_level=16,
            map_type="satellite"
        )

        print(f"✅ Map result: {result}")

        if result.get("success"):
            print(f"🎯 Map saved successfully!")
            return investigation_id
        else:
            print(f"❌ Map generation failed: {result}")
            return None

    except Exception as e:
        print(f"❌ Tool execution failed: {e}")
        return None


def test_simple_presentation():
    """Test presentation creation with simple data."""

    print("\n🎨 SIMPLE PRESENTATION TEST")
    print("=" * 50)

    try:
        from rag.tools.report_tools import create_slides_presentation_func

        investigation_id = f"SIMPLE-PRES-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"📊 Testing presentation creation:")
        print(f"   Investigation ID: {investigation_id}")

        result = create_slides_presentation_func(
            investigation_id=investigation_id,
            title="Simple Test Presentation"
        )

        print(f"✅ Presentation result: {result}")

        if result.get("success"):
            print(f"🎯 Presentation URL: {result.get('url')}")
            return result.get("url")
        else:
            print(f"❌ Presentation creation failed: {result}")
            return None

    except Exception as e:
        print(f"❌ Presentation creation failed: {e}")
        return None


def test_web_search():
    """Test simple web search functionality."""

    print("\n🔍 SIMPLE WEB SEARCH TEST")
    print("=" * 50)

    try:
        from rag.tools.research_tools import web_search_func

        print(f"🌐 Testing web search:")
        print(f"   Query: Washington Square Park protest")

        result = web_search_func(
            query="Washington Square Park protest",
            source_types="news",
            max_results=3
        )

        print(f"✅ Search result: {result}")

        if result.get("success"):
            print(f"🎯 Found {len(result.get('results', []))} results")
            return True
        else:
            print(f"❌ Web search failed: {result}")
            return False

    except Exception as e:
        print(f"❌ Web search failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 STARTING SIMPLE WORKFLOW TESTS")
    print("=" * 60)

    # Test each component individually
    investigation_id = test_simple_tool_execution()
    presentation_url = test_simple_presentation()
    search_success = test_web_search()

    print("\n" + "=" * 60)
    print("📊 SIMPLE WORKFLOW TEST RESULTS:")
    print(f"   Map Generation: {'✅ PASS' if investigation_id else '❌ FAIL'}")
    print(f"   Presentation: {'✅ PASS' if presentation_url else '❌ FAIL'}")
    print(f"   Web Search: {'✅ PASS' if search_success else '❌ FAIL'}")

    if investigation_id and presentation_url and search_success:
        print("\n🎉 ALL SIMPLE TESTS PASSED!")
        print("Next step: Build minimal agent that uses these working tools")
    else:
        print("\n🚨 SOME TESTS FAILED!")
        print("Fix basic tool execution before proceeding to agents")
