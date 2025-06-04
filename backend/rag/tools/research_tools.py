# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Research tools for external data collection with artifact support."""

import requests
from typing import List, Dict, Optional
from google.genai import types
from google.adk.tools import FunctionTool, ToolContext


def web_search_func(
    query: str,
    source_types: List[str] = ["news", "official", "academic"]
) -> List[Dict]:
    """Comprehensive web search across multiple source types.

    Args:
        query: Search query terms
        source_types: Types of sources to include (news, official, academic)

    Returns:
        List of web search results with URLs, snippets, source credibility
    """
    # Simple mock implementation for now
    return [
        {
            "title": f"Search results for: {query}",
            "snippet": f"Mock search results about {query} from {', '.join(source_types)} sources",
            "url": "https://example.com/search",
            "source_type": source_types[0] if source_types else "news",
            "credibility_score": 0.8,
            "timestamp": "2025-01-03T12:00:00Z"
        }
    ]


async def collect_media_content_func(
    context: ToolContext,
    search_terms: List[str],
    content_types: List[str] = ["images"]
) -> List[Dict]:
    """Gather images, videos, and multimedia content and save as artifacts.

    Args:
        context: Tool context for artifact operations
        search_terms: Terms to search for in media content
        content_types: Types of media to collect (images, videos, etc.)

    Returns:
        List of media content with artifact references, descriptions, relevance scores
    """
    collected_media = []

    # Mock implementation - simulate collecting images based on search terms
    for i, search_term in enumerate(search_terms):
        if "images" in content_types:
            # Simulate finding relevant images
            mock_images = [
                {
                    "url": f"https://example.com/image_{search_term}_{j}.jpg",
                    "description": f"Image related to {search_term}",
                    "source": "social_media"
                }
                for j in range(2)  # Simulate finding 2 images per search term
            ]

            for j, image_info in enumerate(mock_images):
                try:
                    # In a real implementation, download the image
                    # image_response = requests.get(image_info["url"])
                    # image_bytes = image_response.content

                    # For now, create mock image data
                    mock_image_bytes = b'\x89PNG\r\n\x1a\n' + b'mock_image_data' * 100

                    # Create artifact from image data
                    image_artifact = types.Part.from_bytes(
                        data=mock_image_bytes,
                        mime_type="image/png"
                    )

                    # Save as artifact with descriptive filename
                    filename = f"media_{search_term}_{i}_{j}.png"
                    version = await context.save_artifact(filename, image_artifact)

                    collected_media.append({
                        "type": "image",
                        "search_term": search_term,
                        "description": image_info["description"],
                        "source": image_info["source"],
                        "original_url": image_info["url"],
                        "artifact_filename": filename,
                        "artifact_version": version,
                        "mime_type": "image/png",
                        "relevance_score": 0.8
                    })

                except Exception as e:
                    print(f"Error saving media artifact: {e}")
                    # Continue with next item even if one fails
                    continue

    return collected_media


async def save_investigation_screenshot_func(
    context: ToolContext,
    url: str,
    description: str
) -> Dict:
    """Take and save a screenshot of a webpage for investigation evidence.

    Args:
        context: Tool context for artifact operations
        url: URL to screenshot
        description: Description of what the screenshot shows

    Returns:
        Information about the saved screenshot artifact
    """
    try:
        # In a real implementation, use a service like Playwright or Selenium
        # For now, create mock screenshot data
        mock_screenshot_bytes = b'\x89PNG\r\n\x1a\n' + b'mock_screenshot_data' * 200

        # Create artifact from screenshot
        screenshot_artifact = types.Part.from_bytes(
            data=mock_screenshot_bytes,
            mime_type="image/png"
        )

        # Generate filename based on URL and timestamp
        import datetime
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"

        version = await context.save_artifact(filename, screenshot_artifact)

        return {
            "type": "screenshot",
            "url": url,
            "description": description,
            "artifact_filename": filename,
            "artifact_version": version,
            "mime_type": "image/png",
            "timestamp": timestamp
        }

    except Exception as e:
        return {
            "error": f"Failed to save screenshot: {e}",
            "url": url
        }


async def list_investigation_artifacts_func(
    context: ToolContext
) -> List[str]:
    """List all artifacts collected during the investigation.

    Args:
        context: Tool context for artifact operations

    Returns:
        List of artifact filenames available in the investigation
    """
    try:
        artifacts = await context.list_artifacts()
        return artifacts
    except Exception as e:
        print(f"Error listing artifacts: {e}")
        return []


# Create FunctionTool instances
web_search = FunctionTool(web_search_func)
collect_media_content = FunctionTool(collect_media_content_func)
save_investigation_screenshot = FunctionTool(
    save_investigation_screenshot_func)
list_investigation_artifacts = FunctionTool(list_investigation_artifacts_func)


# TODO: Implement remaining research tools

def search_social_media_func(
    platform: str,
    query: str,
    location: Optional[str] = None,
    time_range: str = "24h"
) -> List[Dict]:
    """Search Reddit, HackerNews, Twitter for recent posts and discussions.

    Args:
        platform: Social media platform to search (reddit, twitter, hackernews)
        query: Search query terms
        location: Geographic location filter (optional)
        time_range: Time range for search (e.g., "24h", "7d")

    Returns:
        List of social media posts with content, sentiment, engagement metrics
    """
    # TODO: Implement social media search
    return []


def query_live_apis_func(
    api_name: str,
    location: str,
    parameters: Dict
) -> Dict:
    """Query live data APIs (311, traffic, weather, transit).

    Args:
        api_name: Name of the API to query (311, traffic, weather, transit)
        location: Geographic location for the query
        parameters: Additional parameters for the API call

    Returns:
        Live data from the specified API
    """
    # TODO: Implement live API queries
    return {}


# Create additional tools when implemented
# search_social_media = FunctionTool(search_social_media_func)
# query_live_apis = FunctionTool(query_live_apis_func)
