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
from .artifact_manager import artifact_manager
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# Google Custom Search Configuration (Fallback)
# Load these at runtime instead of import time to ensure .env is loaded first
GOOGLE_CUSTOM_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


def _get_google_search_config():
    """Get Google Custom Search configuration from environment variables.

    Returns:
        dict: Configuration with api_key and engine_id
    """
    # Try to get from environment variables first (production)
    api_key = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
    engine_id = os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID")

    # If not available and .env file exists, try loading it (local development only)
    if (not api_key or not engine_id):
        try:
            from dotenv import load_dotenv
            # Load from project root only if .env file exists
            env_file_path = os.path.join(os.path.dirname(
                __file__), "..", "..", "..", ".env")
            if os.path.exists(env_file_path):
                load_dotenv(env_file_path)
                api_key = api_key or os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
                engine_id = engine_id or os.getenv(
                    "GOOGLE_CUSTOM_SEARCH_ENGINE_ID")
        except (ImportError, Exception):
            # dotenv not available or loading failed, continue with environment variables
            pass

    return {
        'api_key': api_key,
        'engine_id': engine_id
    }


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
    source_types: str = "news,official,academic",
    max_results: int = 10,
    collect_evidence: bool = True,
    investigation_id: str = "unknown"
) -> dict:
    """
    Search the web for recent information related to the query.
    Optionally collect evidence (screenshots and media) from results.

    Args:
        query: Search query string
        source_types: Comma-separated types of sources to prioritize (news,official,academic)
        max_results: Maximum number of results to return (default: 10)
        collect_evidence: Whether to automatically collect screenshots and media (default: True)
        investigation_id: Investigation ID for artifact naming

    Returns:
        dict: Search results with evidence collection info
    """
    try:
        # Initialize DuckDuckGo search
        ddgs = DDGS()

        # Parse source types
        sources = [s.strip().lower() for s in source_types.split(",")]

        # Perform the search
        search_results = []
        evidence_collected = []

        # Try regular web search first with fallback
        try:
            # Use the new fallback search function
            search_results = _search_web_with_fallback(
                query, max_results, search_type="text")

            for i, result in enumerate(search_results):
                # Collect evidence from top results if enabled
                if collect_evidence and i < 3:  # Only collect from top 3 results
                    url = result.get("url", "")
                    if url and url.startswith("http"):
                        # Collect screenshot
                        screenshot_info = save_investigation_screenshot_simple_func(
                            url=url,
                            description=f"Screenshot of search result: {result.get('title', 'Unknown')}",
                            investigation_id=investigation_id
                        )

                        # IMPORTANT: Actually save the artifact to investigation state
                        investigation_state = state_manager.get_investigation(
                            investigation_id)
                        if investigation_state and screenshot_info.get("success"):
                            investigation_state.artifacts.append(
                                screenshot_info)

                        evidence_collected.append({
                            "type": "screenshot",
                            "url": url,
                            "artifact_info": screenshot_info
                        })

        except Exception as e:
            logger.error(f"Web search with fallback failed: {e}")

        # If we want news specifically, try news search with fallback
        if "news" in sources and len(search_results) < max_results:
            try:
                # Use the new fallback search function for news
                remaining_results = max_results - len(search_results)
                news_results = _search_web_with_fallback(
                    query, remaining_results, search_type="news")

                for i, result in enumerate(news_results):
                    search_results.append(result)

                    # Collect evidence from news results if enabled
                    if collect_evidence and i < 2:  # Only collect from top 2 news results
                        url = result.get("url", "")
                        if url and url.startswith("http"):
                            screenshot_info = save_investigation_screenshot_simple_func(
                                url=url,
                                description=f"Screenshot of news article: {result.get('title', 'Unknown')}",
                                investigation_id=investigation_id
                            )

                            # IMPORTANT: Actually save the artifact to investigation state
                            investigation_state = state_manager.get_investigation(
                                investigation_id)
                            if investigation_state and screenshot_info.get("success"):
                                investigation_state.artifacts.append(
                                    screenshot_info)

                            evidence_collected.append({
                                "type": "screenshot",
                                "url": url,
                                "artifact_info": screenshot_info
                            })

            except Exception as e:
                logger.error(f"News search with fallback failed: {e}")

        # Auto-collect related media content if enabled
        if collect_evidence:
            media_info = collect_media_content_simple_func(
                search_terms=query,
                content_types="images",
                investigation_id=investigation_id
            )

            # IMPORTANT: Actually save media artifacts to investigation state
            investigation_state = state_manager.get_investigation(
                investigation_id)
            if investigation_state and media_info.get("success"):
                # Save each collected media item as an artifact
                for media_item in media_info.get("collected_media", []):
                    investigation_state.artifacts.append(media_item)

            evidence_collected.append({
                "type": "media_collection",
                "artifact_info": media_info
            })

        # Limit to max_results
        search_results = search_results[:max_results]

        # Create summary
        summary = f"Found {len(search_results)} results for query: {query}"
        if search_results:
            summary += f". Top result: {search_results[0]['title']}"
        if evidence_collected:
            summary += f". Collected {len(evidence_collected)} evidence artifacts."

        return {
            "success": True,
            "query": query,
            "total_results": len(search_results),
            "results": search_results,
            "evidence_collected": evidence_collected,
            "evidence_count": len(evidence_collected),
            "summary": summary
        }

    except ImportError:
        return {
            "success": False,
            "error": "duckduckgo-search library not installed. Please install it with: pip install duckduckgo-search",
            "query": query,
            "results": [],
            "evidence_collected": [],
            "summary": "Web search unavailable - missing dependency"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Web search failed: {str(e)}",
            "query": query,
            "results": [],
            "evidence_collected": [],
            "summary": f"Web search failed for query: {query}"
        }


def collect_media_content_simple_func(
    search_terms: str,
    content_types: str = "images",
    investigation_id: str = "unknown",
    max_items: int = 5
) -> dict:
    """Collect media content (images, videos) related to search terms with GCS storage.

    Args:
        search_terms: Comma-separated search terms
        content_types: Types of content to collect (images, videos, all)
        investigation_id: Investigation ID for naming and artifact tracking
        max_items: Maximum items per search term

    Returns:
        Information about collected media with artifact metadata
    """
    collected_media = []
    downloaded_count = 0

    # Parse search terms and content types
    terms = [term.strip() for term in search_terms.split(",")]
    types = [t.strip().lower() for t in content_types.split(",")]

    # Import artifact manager
    from .artifact_manager import artifact_manager

    try:
        # Collect images if requested
        if "images" in types or "all" in types:
            for query in terms:
                # Search for images using DuckDuckGo
                try:
                    images = _search_images_with_fallback(query, max_items)
                    logger.info(
                        f"Found {len(images)} images for query: {query}")

                    for image in images:
                        image_url = image.get("image", "")
                        if not image_url:
                            continue

                        try:
                            # Download and save to GCS
                            success = artifact_manager.download_and_save_image(
                                investigation_id=investigation_id,
                                image_url=image_url,
                                description=f"Image related to {query}"
                            )

                            if success and success.get("success"):
                                downloaded_count += 1
                                logger.info(
                                    f"✅ Downloaded and saved image: {success}")

                                # CRITICAL FIX: Add to investigation artifacts using correct investigation_id
                                investigation_state = state_manager.get_investigation(
                                    investigation_id)
                                if investigation_state:
                                    artifact_info = {
                                        "type": "image",
                                        "filename": success["filename"],
                                        "gcs_path": success["gcs_path"],
                                        "gcs_url": success["gcs_url"],
                                        "public_url": success["public_url"],
                                        "signed_url": success["signed_url"],
                                        "description": f"Image related to {query}",
                                        "source": "image_search",
                                        "search_query": query,
                                        "source_url": image_url,
                                        "content_type": success["content_type"],
                                        "size_bytes": success["size_bytes"],
                                        "ticker": state_manager.get_next_artifact_ticker(investigation_id),
                                        "timestamp": success["created_at"],
                                        "relevance_score": 0.8,  # High relevance for search results
                                        "metadata": success.get("metadata", {}),
                                        "saved_to_gcs": True  # Mark as saved to GCS
                                    }

                                    investigation_state.artifacts.append(
                                        artifact_info)
                                    logger.info(
                                        f"✅ Added image artifact to investigation {investigation_id}: {success['filename']}")
                                else:
                                    logger.warning(
                                        f"❌ Investigation state not found for {investigation_id}")

                            # Limit total downloads to prevent overwhelming
                            if downloaded_count >= 12:
                                break

                        except Exception as e:
                            logger.warning(
                                f"Failed to download image {image_url}: {e}")
                            continue

                    if downloaded_count >= 12:
                        break
                except Exception as e:
                    logger.warning(f"No images found for query: {query} - {e}")

    except Exception as e:
        logger.error(f"Image search failed: {e}")
        # Continue with fallback mock images

    # If no real images were downloaded, create mock entries for compatibility
    if downloaded_count == 0:
        logger.info(
            "No real images downloaded, creating mock entries for testing")
        for i, term in enumerate(terms):
            if "images" in types:
                for j in range(min(max_items, 2)):
                    ticker = state_manager.get_next_artifact_ticker(
                        investigation_id)
                    filename = f"evidence_{investigation_id}_{ticker:03d}_image_{term.replace(' ', '_')}.jpg"

                    collected_media.append({
                        "type": "image",
                        "search_term": term,
                        "title": f"Mock image for {term}",
                        "description": f"Simulated image related to {term}",
                        "source": "mock_search",
                        "original_url": f"https://example.com/mock_image_{term}_{j}.jpg",
                        "thumbnail_url": f"https://example.com/mock_thumb_{term}_{j}.jpg",
                        "source_url": "https://example.com/mock",
                        "width": 800,
                        "height": 600,
                        "artifact_filename": filename,
                        "planned_artifact": True,
                        "mime_type": "image/jpeg",
                        "relevance_score": 0.6,
                        "ticker": ticker,
                        "timestamp": datetime.utcnow().isoformat()
                    })

    return {
        "success": True,
        "collected_media": collected_media,
        "search_terms": terms,
        "content_types": types,
        "total_items": len(collected_media),
        "downloaded_count": downloaded_count,
        "summary": f"Collected {len(collected_media)} media items for search terms: {', '.join(terms)} ({downloaded_count} real downloads)"
    }


def save_investigation_screenshot_simple_func(
    url: str,
    description: str,
    investigation_id: str = "unknown",
    capture_type: str = "full_page"
) -> dict:
    """Take and save a screenshot of a webpage with enhanced metadata.

    Args:
        url: URL to screenshot
        description: Description of what the screenshot shows
        investigation_id: Investigation ID for naming convention
        capture_type: Type of capture (full_page, viewport, element)

    Returns:
        Information about the planned screenshot with artifact metadata
    """
    # Get next ticker from state manager
    ticker = state_manager.get_next_artifact_ticker(investigation_id)
    filename = f"evidence_{investigation_id}_{ticker:03d}_screenshot.png"

    # Extract domain for better categorization
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        source_type = "news" if any(news_domain in domain for news_domain in [
                                    "cnn", "nytimes", "abc", "pix11", "ny1"]) else "web"
    except:
        domain = "unknown"
        source_type = "web"

    return {
        "success": True,
        "type": "screenshot",
        "filename": filename,
        "url": url,
        "domain": domain,
        "source_type": source_type,
        "description": description,
        "capture_type": capture_type,
        "planned_artifact": True,
        "mime_type": "image/png",
        "ticker": ticker,
        "timestamp": datetime.utcnow().isoformat(),
        "file_size_estimate": "~500KB",
        "relevance_score": 0.8,  # High relevance for screenshots
        "summary": f"Screenshot planned for {domain}: {description}"
    }


def get_investigation_evidence_func(
    investigation_id: str,
    evidence_types: str = "all",
    max_items: int = 50
) -> dict:
    """Retrieve collected evidence artifacts for report generation.

    This function is designed for the Report Agent to gather all evidence
    collected during the investigation for inclusion in reports and presentations.

    Args:
        investigation_id: Investigation ID to retrieve evidence for
        evidence_types: Comma-separated evidence types (screenshots,images,documents,all)
        max_items: Maximum number of evidence items to return

    Returns:
        Comprehensive evidence collection for report generation
    """
    try:
        # Parse evidence types
        types = [t.strip().lower() for t in evidence_types.split(",")]
        include_all = "all" in types

        # Get investigation state
        investigation_state = state_manager.get_investigation(investigation_id)
        if not investigation_state:
            return {
                "success": False,
                "error": f"Investigation {investigation_id} not found",
                "evidence_items": [],
                "summary": "No evidence found - investigation not found"
            }

        # Collect evidence from investigation artifacts
        evidence_items = []

        # Process investigation artifacts
        for artifact in investigation_state.artifacts:
            artifact_type = artifact.get("type", "unknown")

            # Filter by evidence types if not "all"
            if not include_all:
                if artifact_type == "screenshot" and "screenshots" not in types:
                    continue
                elif artifact_type == "image" and "images" not in types:
                    continue
                elif artifact_type == "document" and "documents" not in types:
                    continue

            evidence_items.append({
                "type": artifact_type,
                "filename": artifact.get("filename", "unknown"),
                "description": artifact.get("description", "No description"),
                "url": artifact.get("url", ""),
                # Add GCS URLs and signed URLs for Google Slides integration
                "gcs_url": artifact.get("gcs_url", ""),
                "signed_url": artifact.get("signed_url", ""),
                "public_url": artifact.get("public_url", ""),
                "original_url": artifact.get("original_url", ""),
                "saved_to_gcs": artifact.get("saved_to_gcs", False),
                # Also check alternative keys that might be used
                "image_url": artifact.get("image_url", ""),
                "source": artifact.get("source", "unknown"),
                "timestamp": artifact.get("timestamp", ""),
                "ticker": artifact.get("ticker", 0),
                "relevance_score": artifact.get("relevance_score", 0.5),
                "mime_type": artifact.get("mime_type", "unknown"),
                "title": artifact.get("title", ""),
                "metadata": {
                    "domain": artifact.get("domain", ""),
                    "source_type": artifact.get("source_type", ""),
                    "width": artifact.get("width", 0),
                    "height": artifact.get("height", 0),
                    "file_size": artifact.get("file_size_estimate", "unknown"),
                    "content_type": artifact.get("content_type", ""),
                    "size_bytes": artifact.get("size_bytes", 0)
                }
            })

        # Sort by relevance score and timestamp
        evidence_items.sort(key=lambda x: (
            x["relevance_score"], x["timestamp"]), reverse=True)

        # Limit results
        evidence_items = evidence_items[:max_items]

        # Create evidence summary for report agent
        evidence_summary = {
            "total_items": len(evidence_items),
            "types_found": list(set(item["type"] for item in evidence_items)),
            "sources": list(set(item["source"] for item in evidence_items)),
            "time_range": {
                "earliest": min((item["timestamp"] for item in evidence_items), default=""),
                "latest": max((item["timestamp"] for item in evidence_items), default="")
            },
            "high_relevance_count": len([item for item in evidence_items if item["relevance_score"] > 0.7])
        }

        return {
            "success": True,
            "investigation_id": investigation_id,
            "evidence_items": evidence_items,
            "evidence_summary": evidence_summary,
            "requested_types": types,
            "summary": f"Retrieved {len(evidence_items)} evidence items of types: {', '.join(evidence_summary['types_found'])}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve evidence: {str(e)}",
            "evidence_items": [],
            "summary": f"Evidence retrieval failed for investigation {investigation_id}"
        }


def list_investigation_artifacts_simple_func(
    investigation_id: str = "unknown",
    artifact_types: str = "all"
) -> dict:
    """List all artifacts planned/collected during the investigation.

    Args:
        investigation_id: Investigation ID to check
        artifact_types: Comma-separated artifact types to filter (all,screenshots,images,documents)

    Returns:
        Information about artifacts with counts and summaries
    """
    try:
        # Get investigation state
        investigation_state = state_manager.get_investigation(investigation_id)
        if not investigation_state:
            return {
                "success": False,
                "message": f"Investigation {investigation_id} not found",
                "investigation_id": investigation_id,
                "artifact_count": 0,
                "timestamp": datetime.utcnow().isoformat()
            }

        # Parse artifact types
        types = [t.strip().lower() for t in artifact_types.split(",")]
        include_all = "all" in types

        # Count artifacts by type
        artifact_counts = {}
        filtered_artifacts = []

        for artifact in investigation_state.artifacts:
            artifact_type = artifact.get("type", "unknown")

            # Count all types
            artifact_counts[artifact_type] = artifact_counts.get(
                artifact_type, 0) + 1

            # Filter for response if not "all"
            if include_all or artifact_type in types:
                filtered_artifacts.append(artifact)

        return {
            "success": True,
            "message": "Artifact listing retrieved successfully",
            "investigation_id": investigation_id,
            "artifact_count": len(filtered_artifacts),
            "total_artifacts": len(investigation_state.artifacts),
            "artifact_counts": artifact_counts,
            # Limit to first 20 for display
            "artifacts": filtered_artifacts[:20],
            "timestamp": datetime.utcnow().isoformat(),
            "summary": f"Found {len(filtered_artifacts)} artifacts of requested types from total of {len(investigation_state.artifacts)} artifacts"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to list artifacts: {str(e)}",
            "investigation_id": investigation_id,
            "artifact_count": 0,
            "timestamp": datetime.utcnow().isoformat()
        }


# Create FunctionTool instances with the simplified functions
web_search = FunctionTool(web_search_func)
collect_media_content = FunctionTool(collect_media_content_simple_func)
save_investigation_screenshot = FunctionTool(
    save_investigation_screenshot_simple_func)
get_investigation_evidence = FunctionTool(get_investigation_evidence_func)
list_investigation_artifacts = FunctionTool(
    list_investigation_artifacts_simple_func)


# TODO: Implement remaining research tools

def search_social_media_func(
    query: str,
    location: str = "NYC",
    time_range: str = "24h",
    limit: int = 10,
    collect_evidence: bool = True,
    investigation_id: str = "unknown"
) -> dict:
    """Search Reddit for relevant posts and discussions.
    Optionally collect evidence (screenshots and media) from results.

    Args:
        query: Search query terms
        location: Geographic location filter (default: NYC)
        time_range: Time range for search (24h, 7d, 30d)
        limit: Maximum number of posts to return
        collect_evidence: Whether to automatically collect screenshots and media
        investigation_id: Investigation ID for artifact naming

    Returns:
        Social media posts with evidence collection info
    """
    evidence_collected = []

    if not REDDIT_AVAILABLE:
        logger.warning("Reddit API not available, returning mock data")
        posts = _mock_reddit_search(query, location, time_range, limit)
    else:
        try:
            import asyncio
            posts = asyncio.run(_real_reddit_search(
                query, location, time_range, limit))
        except Exception as e:
            logger.error(
                f"Reddit search failed: {e}, falling back to mock data")
            posts = _mock_reddit_search(query, location, time_range, limit)

    # Collect evidence from top social media posts if enabled
    if collect_evidence and posts:
        top_posts = posts[:3]  # Only collect from top 3 posts

        for i, post in enumerate(top_posts):
            # If post has URL, take screenshot
            if post.get("url") and post["url"].startswith("http"):
                screenshot_info = save_investigation_screenshot_simple_func(
                    url=post["url"],
                    description=f"Screenshot of Reddit post: {post.get('title', 'Unknown')}",
                    investigation_id=investigation_id
                )
                evidence_collected.append({
                    "type": "screenshot",
                    "url": post["url"],
                    "platform": "reddit",
                    "artifact_info": screenshot_info
                })

            # If post mentions media or has images, collect related media
            post_text = f"{post.get('title', '')} {post.get('content', '')}"
            if any(keyword in post_text.lower() for keyword in ['image', 'photo', 'video', 'pic']):
                media_terms = f"{query}, reddit post, {post.get('title', '')}"
                media_info = collect_media_content_simple_func(
                    search_terms=media_terms,
                    content_types="images",
                    investigation_id=investigation_id
                )
                evidence_collected.append({
                    "type": "media_collection",
                    "platform": "reddit",
                    "artifact_info": media_info
                })

    return {
        "success": True,
        "posts": posts,
        "query": query,
        "location": location,
        "count": len(posts),
        "evidence_collected": evidence_collected,
        "evidence_count": len(evidence_collected),
        "summary": f"Found {len(posts)} Reddit posts for '{query}' in {location}. Collected {len(evidence_collected)} evidence artifacts."
    }


async def _real_reddit_search(query: str, location: Optional[str], time_range: str, limit: int) -> list:
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


def _mock_reddit_search(query: str, location: Optional[str], time_range: str, limit: int) -> list:
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
    parameters: str = ""
) -> dict:
    """Query live NYC APIs for real-time data.

    Args:
        api_name: Name of the API to query (311, traffic, weather, etc.)
        location: Geographic location for the query
        parameters: Additional parameters as JSON string

    Returns:
        Live data from the specified API
    """
    # Parse parameters if provided
    import json
    try:
        params_dict = json.loads(parameters) if parameters else {}
    except:
        params_dict = {}

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
        "parameters": params_dict,
        "response": base_response,
        "status": "success",
        "response_time_ms": 150 + api_hash % 100
    }


# Create additional tools when implemented
search_social_media = FunctionTool(search_social_media_func)
query_live_apis = FunctionTool(query_live_apis_func)


def _search_images_google_custom(query: str, max_results: int = 10) -> List[Dict]:
    """Search for images using Google Custom Search API as fallback."""
    if not _get_google_search_config().get('api_key') or not _get_google_search_config().get('engine_id'):
        logger.warning(
            "Google Custom Search not configured - missing API key or Engine ID")
        return []

    try:
        params = {
            'key': _get_google_search_config().get('api_key'),
            'cx': _get_google_search_config().get('engine_id'),
            'q': query,
            'searchType': 'image',
            # Google Custom Search max 10 per request
            'num': min(max_results, 10),
            'safe': 'medium',
            'imgSize': 'medium',
            'imgType': 'photo'
        }

        logger.info(f"🔍 Google Custom Search fallback for: {query}")
        response = requests.get(GOOGLE_CUSTOM_SEARCH_URL,
                                params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        items = data.get('items', [])

        results = []
        for item in items:
            try:
                result = {
                    'title': item.get('title', ''),
                    'image': item.get('link', ''),
                    'thumbnail': item.get('image', {}).get('thumbnailLink', ''),
                    'source': item.get('displayLink', ''),
                    'width': item.get('image', {}).get('width', 0),
                    'height': item.get('image', {}).get('height', 0)
                }
                results.append(result)
            except Exception as e:
                logger.warning(
                    f"Error parsing Google Custom Search result: {e}")
                continue

        logger.info(
            f"✅ Google Custom Search found {len(results)} images for: {query}")
        return results

    except requests.exceptions.RequestException as e:
        logger.error(f"Google Custom Search API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Google Custom Search error: {e}")
        return []


def _search_images_with_fallback(query: str, max_results: int = 10) -> List[Dict]:
    """Search for images with DuckDuckGo primary and Google Custom Search fallback."""
    # Try DuckDuckGo first (free, no API key needed)
    try:
        ddgs = DDGS()
        results = list(ddgs.images(
            keywords=query,
            region="us-en",
            safesearch="moderate",
            size="Medium",
            max_results=max_results
        ))

        if results:
            logger.info(
                f"✅ DuckDuckGo found {len(results)} images for: {query}")
            return results
        else:
            logger.warning(f"DuckDuckGo returned no results for: {query}")

    except Exception as e:
        error_msg = str(e).lower()
        if "ratelimit" in error_msg or "403" in error_msg or "202" in error_msg:
            logger.warning(f"DuckDuckGo rate limited for '{query}': {e}")
        else:
            logger.error(f"DuckDuckGo error for '{query}': {e}")

    # Fallback to Google Custom Search
    logger.info(f"🔄 Falling back to Google Custom Search for: {query}")
    google_results = _search_images_google_custom(query, max_results)

    if google_results:
        # Convert Google Custom Search format to DuckDuckGo format for compatibility
        converted_results = []
        for item in google_results:
            converted_result = {
                'title': item['title'],
                'image': item['image'],
                'thumbnail': item['thumbnail'],
                'url': item['image'],  # Use image URL as main URL
                'source': item['source']
            }
            converted_results.append(converted_result)

        logger.info(
            f"✅ Google Custom Search fallback found {len(converted_results)} images")
        return converted_results

    # If both fail, return empty list (will trigger mock generation)
    logger.warning(
        f"❌ Both DuckDuckGo and Google Custom Search failed for: {query}")
    return []


def _search_web_google_custom(query: str, max_results: int = 10) -> List[Dict]:
    """Search for web pages using Google Custom Search API as fallback for general web search."""
    if not _get_google_search_config().get('api_key') or not _get_google_search_config().get('engine_id'):
        logger.warning(
            "Google Custom Search not configured - missing API key or Engine ID")
        return []

    try:
        params = {
            'key': _get_google_search_config().get('api_key'),
            'cx': _get_google_search_config().get('engine_id'),
            'q': query,
            # No searchType = general web search (not just images)
            # Google Custom Search max 10 per request
            'num': min(max_results, 10),
            'safe': 'medium'
        }

        logger.info(f"🔍 Google Custom Search web fallback for: {query}")
        response = requests.get(GOOGLE_CUSTOM_SEARCH_URL,
                                params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        items = data.get('items', [])

        results = []
        for item in items:
            try:
                result = {
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'source': item.get('displayLink', ''),
                    'type': 'web'
                }
                results.append(result)
            except Exception as e:
                logger.warning(
                    f"Error parsing Google Custom Search web result: {e}")
                continue

        logger.info(
            f"✅ Google Custom Search found {len(results)} web results for: {query}")
        return results

    except requests.exceptions.RequestException as e:
        logger.error(f"Google Custom Search web API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Google Custom Search web error: {e}")
        return []


def _search_web_with_fallback(query: str, max_results: int = 10, search_type: str = "text") -> List[Dict]:
    """Search for web content with DuckDuckGo primary and Google Custom Search fallback."""
    # Try DuckDuckGo first (free, no API key needed)
    try:
        ddgs = DDGS()

        if search_type == "news":
            results = list(ddgs.news(
                keywords=query,
                region="wt-wt",
                safesearch="moderate",
                timelimit="m",  # Last month
                max_results=max_results
            ))

            # Convert news results to standard format
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'snippet': result.get('body', ''),
                    'type': 'news',
                    'date': result.get('date', ''),
                    'source': result.get('source', '')
                })

        else:  # Default to text search
            results = list(ddgs.text(
                keywords=query,
                region="wt-wt",
                safesearch="moderate",
                timelimit="m",  # Last month
                max_results=max_results
            ))

            # Convert text results to standard format
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'title': result.get('title', ''),
                    'url': result.get('href', ''),
                    'snippet': result.get('body', ''),
                    'type': 'web'
                })

        if formatted_results:
            logger.info(
                f"✅ DuckDuckGo found {len(formatted_results)} {search_type} results for: {query}")
            return formatted_results
        else:
            logger.warning(
                f"DuckDuckGo returned no {search_type} results for: {query}")

    except Exception as e:
        error_msg = str(e).lower()
        if "ratelimit" in error_msg or "403" in error_msg or "202" in error_msg:
            logger.warning(
                f"DuckDuckGo {search_type} search rate limited for '{query}': {e}")
        else:
            logger.error(
                f"DuckDuckGo {search_type} search error for '{query}': {e}")

    # Fallback to Google Custom Search (general web search)
    logger.info(f"🔄 Falling back to Google Custom Search web for: {query}")
    google_results = _search_web_google_custom(query, max_results)

    if google_results:
        logger.info(
            f"✅ Google Custom Search web fallback found {len(google_results)} results")
        return google_results

    # If both fail, return empty list
    logger.warning(
        f"❌ Both DuckDuckGo and Google Custom Search failed for web search: {query}")
    return []
