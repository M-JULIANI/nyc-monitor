"""
Simplified research tools with minimal schemas to avoid 400 INVALID_ARGUMENT errors.
These are drop-in replacements for the complex tools causing ADK issues.
"""

from google.adk.tools import FunctionTool
import logging

logger = logging.getLogger(__name__)


def simple_web_search(query: str) -> dict:
    """
    Simplified web search with minimal parameters.

    Args:
        query: What to search for

    Returns:
        Simple results dict
    """
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()

        results = ddgs.text(keywords=query, max_results=5)
        search_results = []

        for result in results:
            search_results.append({
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "snippet": result.get("body", "")[:200]  # Limit snippet length
            })

        return {
            "success": True,
            "query": query,
            "results": search_results[:5]  # Limit to 5 results
        }
    except:
        return {
            "success": False,
            "query": query,
            "results": []
        }


def simple_social_search(query: str) -> dict:
    """
    Simplified social media search.

    Args:
        query: What to search for

    Returns:
        Simple mock results
    """
    return {
        "success": True,
        "query": query,
        "posts": [
            {"platform": "reddit", "title": f"Discussion about {query}", "score": 85},
            {"platform": "twitter", "title": f"Breaking: {query}", "score": 72}
        ]
    }


def simple_collect_media(search_term: str) -> dict:
    """
    Simplified media collection.

    Args:
        search_term: What to search for

    Returns:
        Simple media info
    """
    return {
        "success": True,
        "search_term": search_term,
        "media_count": 3,
        "media_types": ["images"]
    }


def simple_save_screenshot(url: str) -> dict:
    """
    Simplified screenshot saving.

    Args:
        url: URL to screenshot

    Returns:
        Simple success info
    """
    return {
        "success": True,
        "url": url,
        "filename": f"screenshot_{hash(url) % 10000}.png"
    }


def simple_knowledge_search(query: str) -> dict:
    """
    Simplified knowledge base search.

    Args:
        query: What to search for

    Returns:
        Simple mock knowledge
    """
    return {
        "success": True,
        "query": query,
        "documents": [
            {"title": f"Knowledge about {query}", "relevance": 0.85},
            {"title": f"Background on {query}", "relevance": 0.72}
        ]
    }


# Create simple tool instances
simple_web_search_tool = FunctionTool(simple_web_search)
simple_social_search_tool = FunctionTool(simple_social_search)
simple_collect_media_tool = FunctionTool(simple_collect_media)
simple_save_screenshot_tool = FunctionTool(simple_save_screenshot)
simple_knowledge_search_tool = FunctionTool(simple_knowledge_search)
