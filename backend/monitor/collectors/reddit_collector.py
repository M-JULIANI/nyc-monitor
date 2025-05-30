"""
Reddit collector for NYC monitor system.
Collects raw data from NYC-related subreddits for triage analysis.
"""
import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from redditwarp.ASYNC import Client
from redditwarp.models.submission_ASYNC import LinkPost, TextPost, GalleryPost
import logging
import re

from .base_collector import BaseCollector
from ..utils.location_extractor import NYCLocationExtractor

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

        # Emergency and city operations keywords to monitor
        self.priority_keywords = [
            # Emergency Keywords
            '911', 'emergency', 'ambulance', 'fire', 'police', 'shooting',
            'explosion', 'accident', 'collapse', 'evacuation', 'lockdown',

            # Infrastructure Issues
            'power outage', 'blackout', 'water main', 'gas leak', 'subway delay',
            'train stuck', 'signal problem', 'road closure', 'bridge closed',

            # Health & Safety
            'food poisoning', 'contamination', 'outbreak', 'air quality',
            'pollution', 'smog alert', 'heat wave', 'weather emergency',

            # City Operations
            'city hall', 'mayor', 'DOT', 'DSNY', 'FDNY', 'NYPD', 'permit',
            'inspection', 'violation', 'citation', 'budget', 'policy',

            # Community Concerns
            'noise complaint', 'quality of life', 'safety concern', 'homeless',
            'housing crisis', 'rent increase', 'eviction', 'protest', 'rally'
        ]

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
                'emergency_flags': set()
            }

            # Collect recent hot posts from NYC subreddits
            for i, subreddit in enumerate(self.nyc_subreddits, 1):
                try:
                    logger.info(
                        f"📡 Collecting from r/{subreddit} ({i}/{len(self.nyc_subreddits)})")
                    signals = await self._fetch_subreddit_signals(subreddit, limit=10)

                    # Categorize signals by priority
                    for signal in signals:
                        all_signals.append(signal)
                        monitoring_stats['total_posts'] += 1

                        priority_score = signal['metadata'].get(
                            'priority_score', 0)
                        keywords = signal['metadata'].get(
                            'priority_keywords', [])
                        emergency_flags = signal['metadata'].get(
                            'emergency_flags', [])

                        # Track statistics
                        monitoring_stats['keywords_found'].update(keywords)
                        monitoring_stats['emergency_flags'].update(
                            emergency_flags)

                        # Categorize by priority
                        if emergency_flags:
                            priority_signals.append(signal)
                            monitoring_stats['emergency_posts'] += 1
                            logger.warning(f"🚨 EMERGENCY POST DETECTED: {signal['title'][:60]}... "
                                           f"(Keywords: {emergency_flags}, Score: {priority_score})")
                        elif priority_score >= 10:
                            priority_signals.append(signal)
                            monitoring_stats['priority_posts'] += 1
                            logger.info(f"⚠️  HIGH PRIORITY: {signal['title'][:60]}... "
                                        f"(Score: {priority_score})")

                    logger.info(
                        f"✅ Collected {len(signals)} signals from r/{subreddit}")

                except Exception as e:
                    logger.error(
                        f"❌ Error collecting from r/{subreddit}: {str(e)}")
                    logger.error(f"   Exception type: {type(e).__name__}")
                    continue

            # Sort all signals by priority score (highest first)
            all_signals.sort(key=lambda x: x['metadata'].get(
                'priority_score', 0), reverse=True)

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

            if monitoring_stats['emergency_flags']:
                logger.warning(
                    f"🚨 EMERGENCY KEYWORDS DETECTED: {list(monitoring_stats['emergency_flags'])}")

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

                    signal = self._submission_to_signal(submission, subreddit)
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
                        signal = self._submission_to_signal(
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

    def _submission_to_signal(self, submission, subreddit: str) -> Dict:
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

            # Analyze keywords and priority
            keyword_analysis = self._analyze_keywords(title, content)

            # Extract location information using the dedicated extractor
            location_info = self.location_extractor.extract_location_info(
                title, content)

            raw_signal = {
                'title': title,
                'content': content,
                'url': permalink,  # permalink is already a full URL
                'score': score,
                'comments': comment_count,
                'shares': 0,  # Reddit doesn't track shares
                'created_at': created_at,
                'timestamp': created_at,
                'metadata': {
                    'subreddit': subreddit,
                    'post_id': id36,
                    'post_type': self._get_post_type(submission),
                    'author': author_name,
                    'is_stickied': getattr(submission, 'is_stickied', False),
                    'is_nsfw': getattr(submission, 'is_nsfw', False),
                    'priority_keywords': keyword_analysis['keywords'],
                    'priority_score': keyword_analysis['score'],
                    'emergency_flags': keyword_analysis['emergency_flags'],
                    'nyc_relevant': True,  # All returned signals are NYC-relevant
                    # Location data
                    'locations': location_info['locations_found'],
                    'latitude': location_info['center_latitude'],
                    'longitude': location_info['center_longitude'],
                    'location_count': location_info['location_count'],
                    'primary_borough': location_info['primary_borough'],
                    'has_coordinates': location_info['has_coordinates']
                }
            }

            return self.standardize_signal(raw_signal)
        except Exception as e:
            logger.error(f"Error converting submission to signal: {e}")
            logger.error(f"Submission type: {type(submission)}")
            logger.error(f"Available attributes: {dir(submission)}")
            # Return a minimal signal to avoid complete failure
            return self.standardize_signal({
                'title': 'Error parsing submission',
                'content': '',
                'url': '',
                'score': 0,
                'comments': 0,
                'shares': 0,
                'created_at': datetime.utcnow(),
                'timestamp': datetime.utcnow(),
                'metadata': {
                    'subreddit': subreddit,
                    'post_id': '',
                    'post_type': 'unknown',
                    'author': '[error]',
                    'is_stickied': False,
                    'is_nsfw': False,
                    'priority_keywords': [],
                    'priority_score': 0,
                    'emergency_flags': [],
                    'nyc_relevant': False,
                    'locations': [],
                    'latitude': None,
                    'longitude': None,
                    'location_count': 0,
                    'primary_borough': None,
                    'has_coordinates': False
                }
            })

    def _analyze_keywords(self, title: str, content: str) -> Dict:
        """Analyze text for priority keywords and emergency indicators"""
        try:
            # Combine title and content for analysis
            full_text = f"{title} {content}".lower()

            found_keywords = []
            emergency_flags = []
            priority_score = 0

            # Check for priority keywords
            for keyword in self.priority_keywords:
                if keyword.lower() in full_text:
                    found_keywords.append(keyword)

                    # Assign priority scores based on keyword type
                    if keyword in ['911', 'emergency', 'explosion', 'shooting', 'evacuation', 'lockdown']:
                        priority_score += 10  # High priority emergency
                        emergency_flags.append(keyword)
                    elif keyword in ['ambulance', 'fire', 'police', 'accident', 'collapse']:
                        priority_score += 7   # Medium-high priority
                        emergency_flags.append(keyword)
                    elif keyword in ['power outage', 'subway delay', 'gas leak', 'road closure']:
                        priority_score += 5   # Infrastructure issues
                    elif keyword in ['air quality', 'pollution', 'food poisoning', 'outbreak']:
                        priority_score += 4   # Health/environmental concerns
                    elif keyword in ['noise complaint', 'housing crisis', 'safety concern']:
                        priority_score += 2   # Community issues
                    else:
                        priority_score += 1   # General city operations

            # Bonus for multiple keywords (indicates significant event)
            if len(found_keywords) > 1:
                priority_score += len(found_keywords) * 2

            # Geographic bonus for NYC neighborhood mentions
            nyc_neighborhoods = [
                'manhattan', 'brooklyn', 'queens', 'bronx', 'staten island',
                'midtown', 'downtown', 'uptown', 'lower east side', 'upper west side',
                'williamsburg', 'park slope', 'astoria', 'flushing', 'forest hills',
                'harlem', 'soho', 'tribeca', 'chelsea', 'greenwich village'
            ]

            for neighborhood in nyc_neighborhoods:
                if neighborhood in full_text:
                    priority_score += 3  # Geographic relevance bonus
                    break

            return {
                'keywords': found_keywords,
                'score': min(priority_score, 100),  # Cap at 100
                'emergency_flags': emergency_flags
            }

        except Exception as e:
            logger.warning(f"Error analyzing keywords: {e}")
            return {
                'keywords': [],
                'score': 0,
                'emergency_flags': []
            }

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

    def _is_nyc_relevant(self, title: str, content: str) -> bool:
        """Check if content is NYC-relevant based on geographic mentions"""
        full_text = f"{title} {content}".lower()

        # NYC identifiers
        nyc_identifiers = [
            # City names
            'new york', 'nyc', 'new york city',

            # Boroughs
            'manhattan', 'brooklyn', 'queens', 'bronx', 'staten island',

            # Well-known neighborhoods
            'midtown', 'downtown', 'uptown', 'lower east side', 'upper west side',
            'upper east side', 'east village', 'west village', 'greenwich village',
            'soho', 'tribeca', 'chinatown', 'little italy', 'financial district',
            'times square', 'central park', 'battery park', 'prospect park',
            'williamsburg', 'park slope', 'bushwick', 'bed-stuy', 'crown heights',
            'astoria', 'flushing', 'forest hills', 'long island city', 'lic',
            'harlem', 'washington heights', 'inwood', 'morningside heights',
            'chelsea', 'gramercy', 'murray hill', 'hell\'s kitchen',

            # Transit/Infrastructure
            'mta', 'subway', 'metro-north', 'lirr', 'port authority',
            'grand central', 'penn station', 'brooklyn bridge', 'manhattan bridge',
            'queens-midtown tunnel', 'lincoln tunnel', 'holland tunnel',

            # Zip codes (major ones)
            '100', '101', '102', '103', '104',  # Manhattan zip prefixes
            '112', '113', '114', '116',         # Queens zip prefixes
            '110', '111', '117',                # Queens zip prefixes
            '104', '112',                       # Bronx zip prefixes
            '103',                              # Staten Island zip prefix
        ]

        for identifier in nyc_identifiers:
            if identifier in full_text:
                return True

        return False
