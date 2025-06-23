"""
HackerNews collector for NYC monitor system.
Collects recent stories from HackerNews API and filters for NYC-related content.
"""
import os
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging
import re

from .base_collector import BaseCollector
from monitor.utils.location_extractor import NYCLocationExtractor
from monitor.utils.geocode import geocode_nyc_location

logger = logging.getLogger(__name__)


class HackerNewsCollector(BaseCollector):
    """HackerNews collector for NYC signals"""

    def __init__(self):
        super().__init__("hackernews")

        # HackerNews API endpoints
        self.api_base = "https://hacker-news.firebaseio.com/v0"
        self.new_stories_url = f"{self.api_base}/newstories.json"
        self.top_stories_url = f"{self.api_base}/topstories.json"
        self.item_url = f"{self.api_base}/item/{{}}.json"

        # Limit for stories to fetch (HN can return 500+ IDs)
        self.max_stories_to_check = 50  # Check most recent 50 stories
        self.max_signals_to_return = 20  # Return up to 20 NYC-relevant signals

        # Time window for considering "recent" stories (last 4 hours)
        self.time_window_hours = 4

        # Priority keywords now inherited from BaseCollector.PRIORITY_KEYWORDS
        # No need to redefine here - available as self.priority_keywords

        # Initialize location extractor
        self.location_extractor = NYCLocationExtractor()
        logger.info(
            f"🗺️ HackerNews Location extractor initialized with {self.location_extractor.get_location_count()} NYC locations")

        # NYC-relevant search terms for HackerNews (expanded for better coverage)
        self.nyc_search_terms = [
            # Direct NYC mentions
            'NYC', 'New York', 'Manhattan', 'Brooklyn', 'Queens', 'Bronx',

            # Tech companies and areas
            'Silicon Alley', 'Flatiron', 'DUMBO', 'Cornell Tech', 'Hudson Yards',
            'Goldman Sachs', 'JPMorgan', 'Bloomberg', 'Two Sigma', 'Palantir',

            # Infrastructure and services
            'MTA', 'subway', 'Citi Bike', '311', 'LinkNYC', 'mesh network',
            'broadband NYC', 'internet outage', 'power grid', 'ConEd',

            # Events and conferences
            'hackathon NYC', 'tech meetup', 'startup week', 'TechCrunch',
            'NYC startup', 'venture capital', 'tech conference NYC',

            # General infrastructure/tech topics that often affect NYC
            'transportation app', 'delivery app', 'rideshare', 'food delivery',
            'smart city', 'urban planning', 'traffic management', 'public wifi',
            'electric grid', 'renewable energy', 'data center outage',

            # Major NYC universities and research
            'Columbia University', 'NYU', 'New York University', 'Rockefeller',
            'Memorial Sloan Kettering', 'Mount Sinai', 'research NYC',

            # Economic and regulatory
            'Wall Street', 'financial district', 'SEC', 'CFTC', 'fintech NYC',
            'cryptocurrency exchange', 'trading system', 'market outage'
        ]

    async def collect_signals(self) -> List[Dict]:
        """
        Collect recent signals from HackerNews filtered for NYC relevance

        Returns:
            List of NYC-relevant HackerNews signals for triage analysis
        """
        logger.info("🔍 STARTING HACKERNEWS SIGNAL COLLECTION")
        try:
            all_signals = []
            monitoring_stats = {
                'total_stories_checked': 0,
                'relevant_stories': 0,
                'priority_stories': 0,
                'recent_stories': 0,
                'keywords_found': set(),
                'priority_flags': set()
            }

            # Get recent story IDs from both new and top stories
            async with aiohttp.ClientSession() as session:
                # Fetch new stories
                new_story_ids = await self._fetch_story_ids(session, self.new_stories_url, "new")
                top_story_ids = await self._fetch_story_ids(session, self.top_stories_url, "top")

                # Combine and deduplicate story IDs, prioritizing new stories
                all_story_ids = new_story_ids[:30] + [
                    id for id in top_story_ids[:20] if id not in new_story_ids[:30]]
                all_story_ids = all_story_ids[:self.max_stories_to_check]

                logger.info(
                    f"📡 Checking {len(all_story_ids)} recent HackerNews stories")

                # Fetch and process individual stories
                for i, story_id in enumerate(all_story_ids):
                    try:
                        story_data = await self._fetch_story_details(session, story_id)
                        if not story_data:
                            continue

                        monitoring_stats['total_stories_checked'] += 1

                        # Check if story is recent enough
                        if not self._is_recent_story(story_data):
                            continue

                        monitoring_stats['recent_stories'] += 1

                        # Check relevance (NYC-related stories using expanded search terms)
                        if not self._is_hackernews_nyc_relevant(story_data.get('title', ''), story_data.get('text', '')):
                            continue

                        monitoring_stats['relevant_stories'] += 1

                        # DEBUG: Log the NYC-relevant story title
                        title = story_data.get('title', 'No Title')
                        story_url = story_data.get(
                            'url', f"https://news.ycombinator.com/item?id={story_data.get('id', '')}")
                        hn_url = f"https://news.ycombinator.com/item?id={story_data.get('id', '')}"
                        content = story_data.get('text', '')

                        logger.info(f"🎯 Found NYC-relevant story: {title}")
                        logger.info(f"   Story URL: {story_url}")
                        logger.info(f"   HN Discussion: {hn_url}")
                        logger.info(
                            f"   Content preview: {content[:100]}..." if content else "   Content: (no text content)")
                        logger.info(
                            f"   Story ID: {story_data.get('id', 'unknown')}")

                        # Convert to standardized signal format
                        signal = await self._story_to_signal(story_data)
                        if signal:
                            all_signals.append(signal)

                            # Track statistics
                            has_priority = signal['metadata'].get(
                                'has_priority_content', False)
                            keywords = signal['metadata'].get(
                                'priority_keywords', [])
                            priority_flags = signal['metadata'].get(
                                'priority_flags', [])

                            monitoring_stats['keywords_found'].update(keywords)
                            monitoring_stats['priority_flags'].update(
                                priority_flags)

                            if has_priority:
                                monitoring_stats['priority_stories'] += 1
                                logger.info(
                                    f"🚨 PRIORITY HN STORY: {signal['title'][:60]}... (Keywords: {priority_flags})")
                            elif keywords:
                                logger.info(
                                    f"⚠️  RELEVANT HN STORY: {signal['title'][:60]}... (Keywords: {keywords})")
                            else:
                                logger.info(
                                    f"📍 NYC-RELEVANT HN STORY: {signal['title'][:60]}...")

                        # Rate limiting - small delay between requests
                        if i % 10 == 9:  # Every 10 requests
                            await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.error(
                            f"❌ Error processing HN story {story_id}: {str(e)}")
                        continue

            # Sort signals: priority content first, then by HN score
            all_signals.sort(key=lambda x: (
                # Priority content first
                x['metadata'].get('has_priority_content', False),
                x.get('score', 0)  # Then by HN score
            ), reverse=True)

            # Limit results
            final_signals = all_signals[:self.max_signals_to_return]

            # Report monitoring summary
            logger.info(f"📊 HACKERNEWS MONITORING SUMMARY:")
            logger.info(
                f"   Total stories checked: {monitoring_stats['total_stories_checked']}")
            logger.info(
                f"   Recent stories: {monitoring_stats['recent_stories']}")
            logger.info(
                f"   Relevant stories: {monitoring_stats['relevant_stories']}")
            logger.info(
                f"   Priority stories: {monitoring_stats['priority_stories']}")

            if monitoring_stats['priority_flags']:
                logger.warning(
                    f"🚨 PRIORITY KEYWORDS DETECTED: {list(monitoring_stats['priority_flags'])}")

            if monitoring_stats['keywords_found']:
                top_keywords = list(monitoring_stats['keywords_found'])[:10]
                logger.info(f"🔍 Priority keywords found: {top_keywords}")

            logger.info(
                f"📊 COLLECTION SUMMARY: {len(final_signals)} HackerNews signals collected from {monitoring_stats['relevant_stories']} relevant stories")

            return final_signals

        except Exception as e:
            logger.error(
                f"❌ FATAL ERROR in HackerNews signal collection: {str(e)}")
            logger.error(f"   Exception type: {type(e).__name__}")
            return []

    async def _fetch_story_ids(self, session: aiohttp.ClientSession, url: str, story_type: str) -> List[int]:
        """Fetch story IDs from HackerNews API"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    story_ids = await response.json()
                    logger.debug(
                        f"✅ Fetched {len(story_ids)} {story_type} story IDs")
                    return story_ids
                else:
                    logger.error(
                        f"❌ Failed to fetch {story_type} stories: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"❌ Error fetching {story_type} story IDs: {str(e)}")
            return []

    async def _fetch_story_details(self, session: aiohttp.ClientSession, story_id: int) -> Optional[Dict]:
        """Fetch individual story details from HackerNews API"""
        try:
            url = self.item_url.format(story_id)
            async with session.get(url) as response:
                if response.status == 200:
                    story_data = await response.json()
                    # Only return if it's actually a story (not comment, poll, etc.)
                    if story_data and story_data.get('type') == 'story':
                        return story_data
                return None
        except Exception as e:
            logger.debug(f"Error fetching story {story_id}: {str(e)}")
            return None

    def _is_recent_story(self, story_data: Dict) -> bool:
        """Check if story is within our time window"""
        try:
            story_time = datetime.fromtimestamp(
                story_data.get('time', 0), tz=timezone.utc)
            cutoff_time = datetime.now(
                timezone.utc) - timedelta(hours=self.time_window_hours)
            return story_time >= cutoff_time
        except Exception as e:
            logger.debug(f"Error checking story time: {e}")
            return False

    async def _story_to_signal(self, story_data: Dict) -> Optional[Dict]:
        """Convert HackerNews story to standardized signal format"""
        try:
            # Extract story data
            story_id = story_data.get('id', '')
            title = story_data.get('title', 'No Title')
            url = story_data.get(
                'url', f"https://news.ycombinator.com/item?id={story_id}")
            score = story_data.get('score', 0)
            # descendants = total comment count
            comment_count = story_data.get('descendants', 0)
            author = story_data.get('by', '[deleted]')
            created_timestamp = story_data.get('time', 0)
            text = story_data.get('text', '')  # Story text (if any)

            # Convert timestamp to datetime
            created_at = datetime.fromtimestamp(
                created_timestamp, tz=timezone.utc)

            # Combine title and text for analysis
            content = text if text else ''
            full_text = f"{title}\n\n{content}".strip()

            # Analyze keywords for priority detection
            keyword_analysis = self._analyze_keywords(title, content)

            # Extract location information
            location_info = self.location_extractor.extract_location_info(
                title, content)

            # Get coordinates using geocoding service
            geocoding_result = await self._geocode_location_info(location_info, title, content)

            # Assess location specificity
            location_specificity = self._assess_location_specificity(
                title, content, location_info)

            # Filter out signals without sufficient location specificity
            # Only pass signals that have either:
            # 1. Specific location info, OR
            # 2. Priority emergency content (regardless of location specificity)
            if not location_specificity['is_specific'] and not keyword_analysis['has_priority_content']:
                logger.info(
                    f"🚫 Filtering NYC story due to insufficient location specificity: {title[:80]}...")
                logger.info(
                    f"   📍 Location specific: {location_specificity['is_specific']}")
                logger.info(
                    f"   🚨 Priority content: {keyword_analysis['has_priority_content']}")
                logger.info(
                    f"   🔑 Keywords found: {keyword_analysis['keywords']}")
                logger.info(
                    f"   📍 Locations found: {location_info.get('locations_found', [])}")
                return None

            raw_signal = {
                'title': title,
                'content': content,
                'url': url,
                'score': score,
                'comments': comment_count,
                'shares': 0,  # HN doesn't track shares
                'created_at': created_at,
                'timestamp': created_at,
                'full_text': full_text,
                'content_length': len(content),
                'metadata': {
                    'story_id': story_id,
                    'story_type': 'story',
                    'author': author,
                    'hn_url': f"https://news.ycombinator.com/item?id={story_id}",
                    # Basic pre-filtering data (for cost optimization)
                    'priority_keywords': keyword_analysis['keywords'],
                    'has_priority_content': keyword_analysis['has_priority_content'],
                    'priority_flags': keyword_analysis['priority_flags'],
                    'keyword_count': keyword_analysis['keyword_count'],
                    'nyc_relevant': True,  # All returned signals are NYC-relevant
                    # Enhanced location data with real geocoding
                    'locations': location_info['locations_found'],
                    'latitude': geocoding_result.get('lat'),
                    'longitude': geocoding_result.get('lng'),
                    'formatted_address': geocoding_result.get('formatted_address'),
                    'geocoding_confidence': geocoding_result.get('confidence', 0.0),
                    'geocoding_source': geocoding_result.get('source', 'none'),
                    'location_count': location_info['location_count'],
                    'primary_borough': location_info['primary_borough'],
                    'has_coordinates': geocoding_result.get('success', False),
                    # Location specificity assessment
                    'location_specificity': location_specificity['specificity_score'],
                    'specific_streets': location_specificity['specific_streets'],
                    'named_venues': location_specificity['named_venues'],
                    'cross_streets': location_specificity['cross_streets'],
                    'has_actionable_location': location_specificity['is_specific'],
                }
            }

            logger.info(
                f"✅ Successfully converted NYC story to signal: {title[:80]}...")
            return self.standardize_signal(raw_signal)

        except Exception as e:
            logger.error(f"❌ Failed to parse HackerNews story: {e}")
            logger.error(f"   Story ID: {story_data.get('id', 'unknown')}")
            return None

    async def _geocode_location_info(self, location_info: Dict, title: str, content: str) -> Dict:
        """
        Geocode location information to get real coordinates
        (Same logic as Reddit collector)
        """
        try:
            locations = location_info['locations_found']
            borough = location_info.get('primary_borough')

            if locations:
                # Extract the location name string from the first location dict
                first_location = locations[0]
                if isinstance(first_location, dict):
                    location_text = first_location.get('name', '')
                else:
                    location_text = str(first_location)

                logger.debug(
                    f"Geocoding location: '{location_text}' with borough: '{borough}'")
                geocoding_result = await geocode_nyc_location(location_text, borough)
            elif borough:
                logger.debug(f"Geocoding borough: '{borough}'")
                geocoding_result = await geocode_nyc_location(borough)
            else:
                return self._empty_geocoding_result()

            return geocoding_result
        except Exception as e:
            logger.warning(f"Warning: Failed to geocode HN location: {e}")
            return self._empty_geocoding_result()

    def _empty_geocoding_result(self) -> Dict:
        """Return empty geocoding result"""
        return {
            'lat': None,
            'lng': None,
            'formatted_address': None,
            'confidence': 0.0,
            'source': 'none',
            'success': False
        }

    def _is_hackernews_nyc_relevant(self, title: str, text: str) -> bool:
        """Check if story is relevant to NYC using expanded search terms"""
        for term in self.nyc_search_terms:
            if term in title or term in text:
                return True
        return False
