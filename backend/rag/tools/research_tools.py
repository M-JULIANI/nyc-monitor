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
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from google.genai import types
from google.adk.tools import FunctionTool, ToolContext
from ..investigation.state_manager import state_manager
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag

logger = logging.getLogger(__name__)

# Import redditwarp for real Reddit API calls
try:
    from redditwarp.ASYNC import Client as RedditClient
    from redditwarp.models.submission_ASYNC import LinkPost, TextPost, GalleryPost
    REDDIT_AVAILABLE = True
    logger.info("✅ redditwarp library available for real Reddit API calls")
except ImportError:
    logger.warning(
        "❌ redditwarp not available, Reddit search will use mock data")
    logger.info("💡 Install with: pip install redditwarp")
    REDDIT_AVAILABLE = False


def create_rag_retrieval_tool(
    rag_corpus: Optional[str] = None,
    name: str = 'retrieve_rag_documentation',
    description: str = 'Use this tool to retrieve documentation and reference materials for the question from the RAG corpus',
    similarity_top_k: int = 10,
    vector_distance_threshold: float = 0.6,
) -> Optional[VertexAiRagRetrieval]:
    """
    Create a RAG retrieval tool if a corpus is provided.
    Returns None if no corpus is provided, allowing the agent to work without RAG.
    """
    if not rag_corpus:
        logger.info(
            "No RAG corpus provided, agent will run without RAG capabilities")
        return None

    try:
        return VertexAiRagRetrieval(
            name=name,
            description=description,
            rag_resources=[
                rag.RagResource(
                    rag_corpus=rag_corpus
                )
            ],
            similarity_top_k=similarity_top_k,
            vector_distance_threshold=vector_distance_threshold,
        )
    except Exception as e:
        logger.error(f"Failed to create RAG retrieval tool: {e}")
        return None


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
    content_types: List[str] = ["images"],
    alert_id: str = "unknown"
) -> List[Dict]:
    """Gather images, videos, and multimedia content and save as artifacts.

    Args:
        context: Tool context for artifact operations
        search_terms: Terms to search for in media content
        content_types: Types of media to collect (images, videos, etc.)
        alert_id: Alert ID for naming convention

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

                    # Get next ticker from state manager
                    ticker = state_manager.get_next_artifact_ticker(alert_id)
                    filename = f"evidence_{alert_id}_{ticker:03d}_media_{search_term}.png"
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
                        "relevance_score": 0.8,
                        "ticker": ticker
                    })

                except Exception as e:
                    print(f"Error saving media artifact: {e}")
                    # Continue with next item even if one fails
                    continue

    return collected_media


async def save_investigation_screenshot_func(
    context: ToolContext,
    url: str,
    description: str,
    alert_id: str = "unknown"
) -> Dict:
    """Take and save a screenshot of a webpage for investigation evidence.

    Args:
        context: Tool context for artifact operations
        url: URL to screenshot
        description: Description of what the screenshot shows
        alert_id: Alert ID for naming convention

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

        # Get next ticker from state manager
        ticker = state_manager.get_next_artifact_ticker(alert_id)
        filename = f"evidence_{alert_id}_{ticker:03d}_screenshot.png"
        version = await context.save_artifact(filename, screenshot_artifact)

        return {
            "type": "screenshot",
            "url": url,
            "description": description,
            "artifact_filename": filename,
            "artifact_version": version,
            "mime_type": "image/png",
            "ticker": ticker,
            "alert_id": alert_id
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
    query: str,
    location: Optional[str] = None,
    time_range: str = "24h",
    limit: int = 10
) -> List[Dict]:
    """Search Reddit for relevant posts and discussions.

    Args:
        query: Search query terms
        location: Geographic location filter (optional)
        time_range: Time range for search (24h, 7d, 30d)
        limit: Maximum number of posts to return

    Returns:
        List of relevant Reddit posts with metadata
    """

    if not REDDIT_AVAILABLE:
        logger.warning("Reddit API not available, returning mock data")
        return _mock_reddit_search(query, location, time_range, limit)

    try:
        import asyncio
        return asyncio.run(_real_reddit_search(query, location, time_range, limit))
    except Exception as e:
        logger.error(f"Reddit search failed: {e}, falling back to mock data")
        return _mock_reddit_search(query, location, time_range, limit)


async def _real_reddit_search(query: str, location: Optional[str], time_range: str, limit: int) -> List[Dict]:
    """Perform real Reddit search using redditwarp client."""

    # Get Reddit credentials from environment
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    refresh_token = os.getenv("REDDIT_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        logger.warning("Reddit credentials not found, using mock data")
        return _mock_reddit_search(query, location, time_range, limit)

    try:
        # Initialize Reddit client (similar to reddit_collector.py)
        client = RedditClient(client_id, client_secret, refresh_token)

        # NYC-specific subreddits for investigation (from reddit_collector.py)
        nyc_subreddits = [
            'nyc', 'newyorkcity', 'manhattan', 'brooklyn', 'queens',
            'bronx', 'statenisland', 'asknyc', 'nycapartments', 'nycjobs',
            'nycsubway', 'cycling', 'gentrification', 'urbanplanning',
            'news', 'breakingnews', 'publicfreakout'
        ]

        # Determine time cutoff based on time_range
        if time_range == "24h":
            cutoff_hours = 24
        elif time_range == "7d":
            cutoff_hours = 24 * 7
        elif time_range == "30d":
            cutoff_hours = 24 * 30
        else:
            cutoff_hours = 24  # Default to 24h

        cutoff_time = datetime.utcnow().replace(tzinfo=timezone.utc) - \
            timedelta(hours=cutoff_hours)

        all_posts = []
        query_lower = query.lower()
        location_lower = location.lower() if location else ""

        # Search across relevant subreddits
        search_subreddits = nyc_subreddits if location and 'nyc' in location_lower else [
            'nyc', 'newyorkcity', 'news']

        # Limit to 5 subreddits for speed
        for subreddit in search_subreddits[:5]:
            try:
                logger.info(f"Searching r/{subreddit} for: {query}")

                # Get recent posts from this subreddit
                post_count = 0
                async for submission in client.p.subreddit.pull.hot(subreddit):
                    if post_count >= 20:  # Limit posts per subreddit
                        break

                    try:
                        # Get submission timestamp
                        created_at = getattr(
                            submission, 'created_at', datetime.utcnow())
                        if hasattr(created_at, 'tzinfo') and created_at.tzinfo is None:
                            created_at = created_at.replace(
                                tzinfo=timezone.utc)
                        elif not hasattr(created_at, 'tzinfo'):
                            created_at = datetime.utcnow().replace(tzinfo=timezone.utc)

                        # Skip if too old
                        if created_at < cutoff_time:
                            continue

                        # Get post content
                        title = getattr(submission, 'title', '')
                        content = _get_reddit_content(submission)
                        full_text = f"{title} {content}".lower()

                        # Check if query matches title or content
                        if any(term.lower() in full_text for term in query.split()):
                            # Optional location filtering
                            if location and location_lower not in full_text:
                                # Skip if location specified but not found
                                continue

                            post_data = {
                                "platform": "reddit",
                                "post_id": f"reddit_{getattr(submission, 'id36', '')}",
                                "content": f"r/{subreddit}: {title}\n\n{content}",
                                "title": title,
                                "author": f"u/{getattr(submission, 'author_name', '[deleted]')}",
                                "timestamp": created_at.isoformat(),
                                "engagement": {
                                    "likes": getattr(submission, 'score', 0),
                                    "shares": 0,  # Reddit doesn't track shares
                                    "comments": getattr(submission, 'comment_count', 0)
                                },
                                "sentiment": "neutral",  # Could be enhanced with sentiment analysis
                                "relevance_score": _calculate_relevance(query, title, content),
                                "location_tags": [location] if location else ["NYC"],
                                "verified_account": False,
                                "content_type": _get_reddit_post_type(submission),
                                "url": getattr(submission, 'permalink', ''),
                                "subreddit": subreddit
                            }

                            all_posts.append(post_data)

                    except Exception as e:
                        logger.warning(
                            f"Error processing submission in r/{subreddit}: {e}")
                        continue

                    post_count += 1

            except Exception as e:
                logger.warning(f"Error searching r/{subreddit}: {e}")
                continue

        # Sort by relevance and engagement
        all_posts.sort(key=lambda x: (
            x['relevance_score'], x['engagement']['likes']), reverse=True)

        logger.info(
            f"Found {len(all_posts)} relevant Reddit posts for query: {query}")
        return all_posts[:limit]

    except Exception as e:
        logger.error(f"Reddit search failed completely: {e}")
        return _mock_reddit_search(query, location, time_range, limit)


def _get_reddit_content(submission) -> str:
    """Extract content from Reddit submission based on type."""
    try:
        if isinstance(submission, LinkPost):
            return getattr(submission, 'link', '') or ''
        elif isinstance(submission, TextPost):
            return getattr(submission, 'body', '') or ''
        elif isinstance(submission, GalleryPost):
            gallery_link = getattr(submission, 'gallery_link', None)
            return str(gallery_link) if gallery_link else ''
        else:
            # Fallback for unknown types
            return getattr(submission, 'body', '') or getattr(submission, 'selftext', '') or ''
    except Exception as e:
        logger.warning(f"Error extracting Reddit content: {e}")
        return ''


def _get_reddit_post_type(submission) -> str:
    """Determine Reddit post type."""
    if isinstance(submission, LinkPost):
        return 'link'
    elif isinstance(submission, TextPost):
        return 'text'
    elif isinstance(submission, GalleryPost):
        return 'gallery'
    return 'unknown'


def _calculate_relevance(query: str, title: str, content: str) -> float:
    """Calculate relevance score for a post based on query match."""
    query_terms = [term.lower() for term in query.split()]
    title_lower = title.lower()
    content_lower = content.lower()

    score = 0.0

    # Higher weight for title matches
    for term in query_terms:
        if term in title_lower:
            score += 0.4
        if term in content_lower:
            score += 0.2

    # Boost for exact phrase matches
    if query.lower() in title_lower:
        score += 0.3
    if query.lower() in content_lower:
        score += 0.1

    return min(score, 1.0)  # Cap at 1.0


def _mock_reddit_search(query: str, location: Optional[str], time_range: str, limit: int) -> List[Dict]:
    """Fallback mock Reddit search results."""
    query_hash = hash(query) % 1000
    location_suffix = f" in {location}" if location else ""

    return [
        {
            "platform": "reddit",
            "post_id": f"reddit_{query_hash}_{i:03d}",
            "content": f"Reddit post about {query}{location_suffix}. Community discussion shows mixed reactions and concerns about local impact.",
            "title": f"Discussion about {query}",
            "author": f"u/user{query_hash + i}",
            "timestamp": f"2024-12-0{1 + i}T{10 + (query_hash + i) % 12}:30:00Z",
            "engagement": {
                "likes": 10 + (query_hash * i) % 100,
                "shares": 2 + (query_hash * i) % 20,
                "comments": 5 + (query_hash * i) % 30
            },
            "sentiment": ["negative", "neutral", "positive"][i % 3],
            "relevance_score": 0.7 + (query_hash % 25) / 100,
            "location_tags": [location] if location else ["NYC", "Manhattan"],
            "verified_account": i == 0,  # First result is from verified account
            "content_type": ["text", "link", "gallery"][i % 3],
            "url": f"https://reddit.com/r/nyc/comments/mock_{i}",
            "subreddit": "nyc"
        }
        for i in range(min(limit, 3))  # Return up to 3 mock posts
    ]


def query_live_apis_func(
    api_name: str,
    location: str,
    parameters: Dict
) -> Dict:
    """Query live NYC APIs for real-time data.

    Args:
        api_name: Name of the API to query (311, traffic, weather, etc.)
        location: Geographic location for the query
        parameters: Additional parameters for the API query

    Returns:
        Live data from the specified API
    """
    # Mock live API responses
    location_hash = hash(location) % 100
    api_hash = hash(api_name) % 100

    api_responses = {
        "311": {
            "service": "NYC 311 Service Requests",
            "data": {
                "total_requests_24h": 50 + location_hash % 100,
                "top_complaint_types": [
                    {"type": "Noise - Street/Sidewalk",
                        "count": 15 + location_hash % 20},
                    {"type": "Illegal Parking", "count": 12 + location_hash % 15},
                    {"type": "Street Condition", "count": 8 + location_hash % 12}
                ],
                "recent_requests": [
                    {
                        "complaint_type": "Noise - Street/Sidewalk",
                        "descriptor": "Loud Music/Party",
                        "status": "Open",
                        "created_date": "2024-12-03T14:30:00Z"
                    }
                ]
            }
        },
        "traffic": {
            "service": "NYC DOT Traffic Data",
            "data": {
                "current_conditions": ["normal", "heavy", "severe"][location_hash % 3],
                "speed_average": 25 + location_hash % 20,  # mph
                "incidents": 2 + location_hash % 5,
                "construction_zones": 1 + location_hash % 3,
                "recent_incidents": [
                    {
                        "type": "Vehicle Accident",
                        "severity": "Minor",
                        "reported": "2024-12-03T13:45:00Z",
                        "cleared": None
                    }
                ]
            }
        },
        "weather": {
            "service": "National Weather Service NYC",
            "data": {
                "current_temp": 45 + location_hash % 20,  # Fahrenheit
                "conditions": ["Clear", "Cloudy", "Rainy", "Windy"][location_hash % 4],
                "visibility": "10 miles",
                "wind_speed": 5 + location_hash % 15,  # mph
                "alerts": [] if location_hash % 3 == 0 else ["Winter Weather Advisory"]
            }
        },
        "transit": {
            "service": "MTA Service Status",
            "data": {
                "subway_delays": 3 + location_hash % 8,
                "bus_delays": 2 + location_hash % 6,
                "service_alerts": [
                    {
                        "line": ["4", "5", "6", "L", "N", "Q"][location_hash % 6],
                        "status": ["Good Service", "Delays", "Service Change"][location_hash % 3],
                        "reason": "Signal problems" if location_hash % 2 == 0 else "Train traffic ahead"
                    }
                ]
            }
        }
    }

    base_response = api_responses.get(api_name.lower(), {
        "service": f"{api_name} API",
        "data": {"message": f"Mock data for {api_name} API in {location}"}
    })

    return {
        "api_name": api_name,
        "location": location,
        "query_time": "2024-12-03T15:00:00Z",
        "parameters": parameters,
        "response": base_response,
        "status": "success",
        "response_time_ms": 150 + api_hash % 100
    }


# Create additional tools when implemented
# search_social_media = FunctionTool(search_social_media_func)
# query_live_apis = FunctionTool(query_live_apis_func)
