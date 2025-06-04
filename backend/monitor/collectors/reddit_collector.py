"""
Reddit collector for NYC monitor system.
Collects raw data from NYC-related subreddits for triage analysis.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from redditwarp.ASYNC import Client
from redditwarp.models.submission_ASYNC import LinkPost, TextPost, GalleryPost
import logging
import re

from .base_collector import BaseCollector
from monitor.utils.location_extractor import NYCLocationExtractor
from monitor.utils.geocode import geocode_nyc_location

logger = logging.getLogger(__name__)


class RedditCollector(BaseCollector):
    """Reddit collector for NYC signals"""

    def __init__(self):
        super().__init__("reddit")

        # Reddit API credentials
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.refresh_token = os.getenv("REDDIT_REFRESH_TOKEN")

        # Debug logging for credentials
        logger.info("🔑 REDDIT CREDENTIALS CHECK:")
        logger.info(
            f"   CLIENT_ID: {'✅ SET' if self.client_id else '❌ MISSING'} ({self.client_id[:10] + '...' if self.client_id else 'None'})")
        logger.info(
            f"   CLIENT_SECRET: {'✅ SET' if self.client_secret else '❌ MISSING'} ({'[REDACTED]' if self.client_secret else 'None'})")
        logger.info(
            f"   REFRESH_TOKEN: {'✅ SET' if self.refresh_token else '❌ MISSING'} ({self.refresh_token[:10] + '...' if self.refresh_token else 'None'})")

        if not all([self.client_id, self.client_secret, self.refresh_token]):
            error_msg = "Missing Reddit API credentials. Please set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_REFRESH_TOKEN environment variables."
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # Initialize Reddit client
        try:
            logger.info("🔗 Initializing Reddit client...")
            self.client = Client(
                self.client_id, self.client_secret, self.refresh_token)
            logger.info("✅ Reddit client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Reddit client: {str(e)}")
            raise

        # NYC-specific subreddits to monitor (verified to exist)
        self.nyc_subreddits = [
            # Core NYC Communities
            'nyc', 'newyorkcity', 'manhattan', 'brooklyn', 'queens',
            'bronx', 'statenisland', 'asknyc', 'nycapartments', 'nycjobs',

            # Transportation (NYC-specific)
            'nycsubway', 'cycling',  # nyctraffic and mta don't exist as active communities

            # Housing & Development (verified)
            'gentrification', 'urbanplanning',  # removed nychousing, nycrenting

            # Remove non-existent: nypd, fdny, emergency, ems, firstresponders
            # Remove non-existent: mta, nyctraffic, bikenyc
            # Remove non-existent: nychealth, airquality, environmentnyc, publichealth
            # Remove non-existent: noisecomplaint, neighborhoodwatch, communityboard
        ]

        # Priority keywords now inherited from BaseCollector.PRIORITY_KEYWORDS
        # No need to redefine here - available as self.priority_keywords

        logger.info(
            f"📍 Monitoring {len(self.nyc_subreddits)} NYC subreddits: {', '.join(self.nyc_subreddits)}")

        # Initialize location extractor
        self.location_extractor = NYCLocationExtractor()
        logger.info(
            f"🗺️ Location extractor initialized with {self.location_extractor.get_location_count()} NYC locations")

    async def collect_signals(self) -> List[Dict]:
        """
        Collect recent signals from NYC subreddits with priority-based filtering

        Returns:
            List of raw Reddit signals for triage analysis, prioritized by emergency/safety keywords
        """
        logger.info("🔍 STARTING REDDIT SIGNAL COLLECTION")
        try:
            all_signals = []
            priority_signals = []
            monitoring_stats = {
                'total_posts': 0,
                'priority_posts': 0,
                'emergency_posts': 0,
                'subreddits_monitored': len(self.nyc_subreddits),
                'keywords_found': set(),
                'priority_flags': set()
            }

            # Collect recent hot posts from NYC subreddits
            for i, subreddit in enumerate(self.nyc_subreddits, 1):
                try:
                    logger.info(
                        f"📡 Collecting from r/{subreddit} ({i}/{len(self.nyc_subreddits)})")
                    signals = await self._fetch_subreddit_signals(subreddit, limit=10)

                    # Categorize signals by priority content (for logging)
                    for signal in signals:
                        all_signals.append(signal)
                        monitoring_stats['total_posts'] += 1

                        has_priority = signal['metadata'].get(
                            'has_priority_content', False)
                        keywords = signal['metadata'].get(
                            'priority_keywords', [])
                        priority_flags = signal['metadata'].get(
                            'priority_flags', [])

                        # Track statistics
                        monitoring_stats['keywords_found'].update(keywords)
                        monitoring_stats['priority_flags'].update(
                            priority_flags)

                        # Categorization by priority content (emergencies OR major events)
                        if has_priority:
                            priority_signals.append(signal)
                            monitoring_stats['priority_posts'] += 1

                            # Distinguish between emergencies and events in logging
                            emergency_terms = ['911', 'emergency', 'fire', 'shooting', 'explosion',
                                               'ambulance', 'police', 'evacuation', 'lockdown', 'collapse',
                                               'accident', 'power outage', 'blackout', 'gas leak', 'outbreak']

                            has_emergency = any(
                                term in priority_flags for term in emergency_terms)

                            if has_emergency:
                                monitoring_stats['emergency_posts'] += 1
                                logger.warning(f"🚨 EMERGENCY CONTENT: {signal['title'][:60]}... "
                                               f"(Keywords: {priority_flags})")
                            else:
                                logger.info(f"🎉 MAJOR EVENT/GATHERING: {signal['title'][:60]}... "
                                            f"(Keywords: {priority_flags})")
                        elif len(keywords) > 0:
                            logger.info(f"⚠️  RELEVANT KEYWORDS: {signal['title'][:60]}... "
                                        f"(Keywords: {keywords})")

                    logger.info(
                        f"✅ Collected {len(signals)} signals from r/{subreddit}")

                except Exception as e:
                    logger.error(
                        f"❌ Error collecting from r/{subreddit}: {str(e)}")
                    logger.error(f"   Exception type: {type(e).__name__}")
                    continue

            # Sort signals: priority content first, then by Reddit score
            all_signals.sort(key=lambda x: (
                x['metadata'].get('has_priority_content',
                                  False),  # Priority content first
                x.get('score', 0)  # Then by Reddit score
            ), reverse=True)

            # Report monitoring summary
            logger.info(f"📊 REDDIT MONITORING SUMMARY:")
            logger.info(
                f"   Total posts analyzed: {monitoring_stats['total_posts']}")
            logger.info(
                f"   Emergency posts: {monitoring_stats['emergency_posts']}")
            logger.info(
                f"   High priority posts: {monitoring_stats['priority_posts']}")
            logger.info(
                f"   Subreddits monitored: {monitoring_stats['subreddits_monitored']}")

            if monitoring_stats['priority_flags']:
                logger.warning(
                    f"🚨 PRIORITY KEYWORDS DETECTED: {list(monitoring_stats['priority_flags'])}")

            if monitoring_stats['keywords_found']:
                top_keywords = list(monitoring_stats['keywords_found'])[:10]
                logger.info(f"🔍 Priority keywords found: {top_keywords}")

            logger.info(
                f"📊 COLLECTION SUMMARY: {len(all_signals)} total Reddit signals collected "
                f"({len(priority_signals)} priority signals)")

            return all_signals

        except Exception as e:
            logger.error(
                f"❌ FATAL ERROR in Reddit signal collection: {str(e)}")
            logger.error(f"   Exception type: {type(e).__name__}")
            return []

    async def _fetch_subreddit_signals(self, subreddit: str, limit: int = 10) -> List[Dict]:
        """Fetch recent signals from a specific subreddit"""
        logger.debug(f"🎯 Fetching signals from r/{subreddit} (limit: {limit})")
        signals = []

        try:
            # Get both hot and new posts for better coverage
            hot_posts = []
            new_posts = []

            # Fetch hot posts (limit using counter instead of parameter)
            logger.debug(f"🔥 Fetching hot posts from r/{subreddit}")
            hot_count = 0
            try:
                async for submission in self.client.p.subreddit.pull.hot(subreddit):
                    if hot_count >= limit//2:
                        break
                    # Debug: log submission attributes for the first few posts
                    if hot_count < 2:
                        logger.debug(
                            f"HOT SUBMISSION {hot_count}: type={type(submission).__name__}")
                        logger.debug(
                            f"  Available attributes: {[attr for attr in dir(submission) if not attr.startswith('_')]}")

                    signal = await self._submission_to_signal(submission, subreddit)
                    if signal is not None:  # Only add if not filtered out
                        hot_posts.append(signal)
                    hot_count += 1
                logger.debug(
                    f"✅ Got {len(hot_posts)} hot posts from r/{subreddit}")
            except Exception as e:
                logger.error(
                    f"❌ Error fetching hot posts from r/{subreddit}: {str(e)}")
                logger.error(f"   Exception type: {type(e).__name__}")

            # Fetch recent posts (last 4 hours)
            logger.debug(f"🆕 Fetching new posts from r/{subreddit}")
            cutoff_time = datetime.utcnow().replace(
                tzinfo=timezone.utc) - timedelta(hours=4)
            new_count = 0
            try:
                async for submission in self.client.p.subreddit.pull.new(subreddit):
                    if new_count >= limit:
                        break
                    # Debug: log submission attributes for the first few posts
                    if new_count < 2:
                        logger.debug(
                            f"NEW SUBMISSION {new_count}: type={type(submission).__name__}")
                        logger.debug(
                            f"  Available attributes: {[attr for attr in dir(submission) if not attr.startswith('_')]}")

                    if hasattr(submission, 'created_at'):
                        post_time = submission.created_at
                        # Handle timezone-naive datetime
                        if post_time.tzinfo is None:
                            post_time = post_time.replace(tzinfo=timezone.utc)
                    else:
                        logger.warning(
                            f"Submission missing created_at: {submission}")
                        continue

                    if post_time >= cutoff_time:
                        signal = await self._submission_to_signal(
                            submission, subreddit)
                        if signal is not None:  # Only add if not filtered out
                            new_posts.append(signal)
                        new_count += 1
                    else:
                        break  # Posts are ordered by time, so we can break early
                logger.debug(
                    f"✅ Got {len(new_posts)} new posts from r/{subreddit}")
            except Exception as e:
                logger.error(
                    f"❌ Error fetching new posts from r/{subreddit}: {str(e)}")
                logger.error(f"   Exception type: {type(e).__name__}")

            # Combine and deduplicate
            logger.debug(
                f"🔄 Combining and deduplicating posts from r/{subreddit}")
            all_posts = hot_posts + new_posts
            seen_ids = set()
            for post in all_posts:
                if post is None:  # Skip None values from filtering
                    continue
                post_id = post['metadata']['post_id']
                if post_id not in seen_ids:
                    signals.append(post)
                    seen_ids.add(post_id)

            final_signals = signals[:limit]  # Return top N unique posts
            logger.debug(
                f"📋 Final result for r/{subreddit}: {len(final_signals)} unique signals")
            return final_signals

        except Exception as e:
            logger.error(
                f"❌ COMPLETE FAILURE fetching from r/{subreddit}: {str(e)}")
            logger.error(f"   Exception type: {type(e).__name__}")
            return []

    async def _submission_to_signal(self, submission, subreddit: str) -> Dict:
        """Convert Reddit submission to standardized signal format"""
        try:
            # Use created_at directly since it's already a datetime object in redditwarp
            created_at = getattr(submission, 'created_at', datetime.utcnow())

            # Safe access to submission attributes
            title = getattr(submission, 'title', 'No Title')
            permalink = getattr(submission, 'permalink', '')
            score = getattr(submission, 'score', 0)
            comment_count = getattr(submission, 'comment_count', 0)
            id36 = getattr(submission, 'id36', '')
            author_name = getattr(submission, 'author_name', '[deleted]')

            # Extract content for keyword analysis
            content = self._get_content(submission)

            # For broader subreddits, check NYC relevance
            broader_subreddits = ['urbanplanning', 'gentrification', 'cycling']
            if subreddit in broader_subreddits:
                if not self._is_nyc_relevant(title, content):
                    # Skip non-NYC relevant posts from broader subreddits
                    return None

            # Analyze keywords for basic emergency detection (pre-filtering)
            keyword_analysis = self._analyze_keywords(title, content)

            # Extract location information using the dedicated extractor
            location_info = self.location_extractor.extract_location_info(
                title, content)

            # NEW: Get real coordinates using geocoding service
            geocoding_result = await self._geocode_location_info(location_info, title, content)

            # NEW: Check location specificity - only pass signals with actionable location data
            location_specificity = self._assess_location_specificity(
                title, content, location_info)

            # Filter out signals without sufficient location specificity
            # Only pass signals that have either:
            # 1. Specific street addresses/intersections, OR
            # 2. Named venues/landmarks, OR
            # 3. Priority emergency content (regardless of location specificity)
            if not location_specificity['is_specific'] and not keyword_analysis['has_priority_content']:
                logger.debug(
                    f"🚫 Filtered out due to insufficient location specificity: {title[:60]}...")
                return None

            raw_signal = {
                'title': title,
                'content': content,
                'url': permalink,  # permalink is already a full URL
                'score': score,
                'comments': comment_count,
                'shares': 0,  # Reddit doesn't track shares
                'created_at': created_at,
                'timestamp': created_at,
                'full_text': f"{title}\n\n{content}".strip(),
                'content_length': len(content),
                'metadata': {
                    'subreddit': subreddit,
                    'post_id': id36,
                    'post_type': self._get_post_type(submission),
                    'author': author_name,
                    'is_stickied': getattr(submission, 'is_stickied', False),
                    'is_nsfw': getattr(submission, 'is_nsfw', False),
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
                    # NEW: Location specificity assessment
                    'location_specificity': location_specificity['specificity_score'],
                    'specific_streets': location_specificity['specific_streets'],
                    'named_venues': location_specificity['named_venues'],
                    'cross_streets': location_specificity['cross_streets'],
                    'has_actionable_location': location_specificity['is_specific'],
                }
            }

            return self.standardize_signal(raw_signal)
        except Exception as e:
            logger.error(f"❌ Failed to parse Reddit submission: {e}")
            logger.error(f"   Submission type: {type(submission)}")
            logger.error(f"   Subreddit: r/{subreddit}")
            # Don't create fake signals - just return None to skip this submission
            return None

    def _get_post_type(self, submission) -> str:
        """Determine post type"""
        if isinstance(submission, LinkPost):
            return 'link'
        elif isinstance(submission, TextPost):
            return 'text'
        elif isinstance(submission, GalleryPost):
            return 'gallery'
        return 'unknown'

    def _get_content(self, submission) -> str:
        """Extract post content based on type"""
        try:
            if isinstance(submission, LinkPost):
                # Use the 'link' attribute which contains the external URL
                return getattr(submission, 'link', '') or ''
            elif isinstance(submission, TextPost):
                return getattr(submission, 'body', '') or ''
            elif isinstance(submission, GalleryPost):
                gallery_link = getattr(submission, 'gallery_link', None)
                return str(gallery_link) if gallery_link else ''
            return ''
        except Exception as e:
            logger.warning(f"Error extracting content from submission: {e}")
            return ''

    async def _geocode_location_info(self, location_info: Dict, title: str, content: str) -> Dict:
        """
        Geocode location information to get real coordinates

        Returns:
            Dict with geocoding result including latitude, longitude, formatted address, and confidence
        """
        try:
            # Extract relevant location information
            locations = location_info['locations_found']
            borough = location_info.get('primary_borough')

            # Try to geocode the most specific location available
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
                # Fall back to borough-level geocoding
                logger.debug(f"Geocoding borough: '{borough}'")
                geocoding_result = await geocode_nyc_location(borough)
            else:
                # No specific location information available
                return self._empty_geocoding_result()

            return geocoding_result
        except Exception as e:
            logger.warning(f"Warning: Failed to geocode location: {e}")
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
