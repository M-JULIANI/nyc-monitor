"""
Twitter collector for NYC monitor system.
Collects recent tweets with NYC-related content and emergency/event keywords.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging
import re
import tweepy
import asyncio

from .base_collector import BaseCollector
from monitor.utils.location_extractor import NYCLocationExtractor
from monitor.utils.geocode import geocode_nyc_location

logger = logging.getLogger(__name__)


class TwitterCollector(BaseCollector):
    """Twitter collector for NYC signals"""

    def __init__(self):
        super().__init__("twitter")

        # Twitter API credentials
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_key_secret = os.getenv("TWITTER_API_KEY_SECRET")
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

        # Debug logging for credentials
        logger.info("🔑 TWITTER CREDENTIALS CHECK:")
        logger.info(
            f"   API_KEY: {'✅ SET' if self.api_key else '❌ MISSING'} ({self.api_key[:10] + '...' if self.api_key else 'None'})")
        logger.info(
            f"   API_KEY_SECRET: {'✅ SET' if self.api_key_secret else '❌ MISSING'} ({'[REDACTED]' if self.api_key_secret else 'None'})")
        logger.info(
            f"   BEARER_TOKEN: {'✅ SET' if self.bearer_token else '❌ MISSING'} ({self.bearer_token[:10] + '...' if self.bearer_token else 'None'})")

        if not all([self.api_key, self.api_key_secret, self.bearer_token]):
            error_msg = "Missing Twitter API credentials. Please set TWITTER_API_KEY, TWITTER_API_KEY_SECRET, and TWITTER_BEARER_TOKEN environment variables."
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # Initialize Twitter API clients
        try:
            logger.info("🔗 Initializing Twitter API clients...")

            # V2 Client (recommended for new features)
            self.client_v2 = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_key_secret,
                wait_on_rate_limit=True
            )

            # V1.1 API for additional functionality if needed
            auth = tweepy.OAuth2BearerHandler(self.bearer_token)
            self.api_v1 = tweepy.API(auth, wait_on_rate_limit=True)

            logger.info("✅ Twitter API clients initialized successfully")
        except Exception as e:
            logger.error(
                f"❌ Failed to initialize Twitter API clients: {str(e)}")
            raise

        # NYC-specific search queries combining location and priority keywords
        self.search_queries = self._build_search_queries()

        # Search parameters
        self.max_tweets_per_query = 25  # Twitter API limit is 100 for recent search
        self.max_total_tweets = 100     # Total limit across all queries
        self.time_window_hours = 2      # Look for tweets from last 2 hours

        logger.info(
            f"🔍 Configured {len(self.search_queries)} search queries for NYC monitoring")

        # Initialize location extractor
        self.location_extractor = NYCLocationExtractor()
        logger.info(
            f"🗺️ Location extractor initialized with {self.location_extractor.get_location_count()} NYC locations")

    def _build_search_queries(self) -> List[str]:
        """Build optimized search queries for NYC emergency/event monitoring"""

        # Use emergency keywords directly from BaseCollector.PRIORITY_KEYWORDS
        emergency_keywords = [
            keyword for keyword in BaseCollector.PRIORITY_KEYWORDS
            if keyword in ['911', 'emergency', 'fire', 'shooting', 'explosion', 'ambulance',
                           'police', 'evacuation', 'lockdown', 'collapse', 'accident']
        ]

        # Use infrastructure keywords directly from BaseCollector.PRIORITY_KEYWORDS
        infrastructure_keywords = [
            keyword for keyword in BaseCollector.PRIORITY_KEYWORDS
            if keyword in ['power outage', 'blackout', 'gas leak', 'subway shutdown',
                           'bridge closed', 'road closure']
        ]

        # Use event keywords directly from BaseCollector.PRIORITY_KEYWORDS
        event_keywords = [
            keyword for keyword in BaseCollector.PRIORITY_KEYWORDS
            if keyword in ['parade', 'festival', 'concert', 'marathon', 'protest',
                           'rally', 'demonstration', 'street fair', 'large crowd']
        ]

        # NYC location identifiers for geo-filtering
        nyc_locations = [
            "NYC", "New York City", "Manhattan", "Brooklyn", "Queens",
            "Bronx", "Staten Island", "Times Square", "Central Park"
        ]

        queries = []

        # Emergency queries (highest priority)
        for keyword in emergency_keywords[:5]:  # Top 5 emergency terms
            for location in nyc_locations[:4]:   # Top 4 locations
                query = f'"{keyword}" "{location}" -is:retweet lang:en'
                queries.append(query)

        # Infrastructure queries
        for keyword in infrastructure_keywords[:3]:
            query = f'"{keyword}" (NYC OR "New York City" OR Manhattan) -is:retweet lang:en'
            queries.append(query)

        # Event queries
        for keyword in event_keywords[:3]:
            query = f'"{keyword}" (NYC OR "New York City") -is:retweet lang:en'
            queries.append(query)

        # General NYC monitoring with priority keywords
        priority_terms = " OR ".join(
            [f'"{k}"' for k in emergency_keywords[:3]])
        query = f'({priority_terms}) NYC -is:retweet lang:en'
        queries.append(query)

        return queries[:15]  # Limit to 15 queries to stay within rate limits

    async def collect_signals(self) -> List[Dict]:
        """
        Collect recent signals from Twitter with NYC relevance and priority filtering

        Returns:
            List of Twitter signals for triage analysis, prioritized by emergency/safety keywords
        """
        logger.info("🔍 STARTING TWITTER SIGNAL COLLECTION")
        try:
            all_signals = []
            monitoring_stats = {
                'queries_executed': 0,
                'total_tweets': 0,
                'relevant_tweets': 0,
                'priority_tweets': 0,
                'emergency_tweets': 0,
                'keywords_found': set(),
                'priority_flags': set()
            }

            # Calculate time window for recent tweets
            since_time = datetime.utcnow().replace(tzinfo=timezone.utc) - \
                timedelta(hours=self.time_window_hours)

            # Execute search queries
            for i, query in enumerate(self.search_queries, 1):
                try:
                    logger.info(
                        f"🔍 Executing query {i}/{len(self.search_queries)}: {query}")

                    # Search recent tweets
                    tweets = tweepy.Paginator(
                        self.client_v2.search_recent_tweets,
                        query=query,
                        tweet_fields=['created_at', 'public_metrics',
                                      'context_annotations', 'geo'],
                        user_fields=['username', 'public_metrics'],
                        expansions=['author_id'],
                        # API max is 100
                        max_results=min(self.max_tweets_per_query, 100),
                        start_time=since_time
                    ).flatten(limit=self.max_tweets_per_query)

                    monitoring_stats['queries_executed'] += 1
                    query_tweet_count = 0

                    for tweet in tweets:
                        try:
                            monitoring_stats['total_tweets'] += 1
                            query_tweet_count += 1

                            # Convert tweet to signal format
                            signal = await self._tweet_to_signal(tweet, query)
                            if signal:
                                all_signals.append(signal)
                                monitoring_stats['relevant_tweets'] += 1

                                # Track statistics
                                has_priority = signal['metadata'].get(
                                    'has_priority_content', False)
                                keywords = signal['metadata'].get(
                                    'priority_keywords', [])
                                priority_flags = signal['metadata'].get(
                                    'priority_flags', [])

                                monitoring_stats['keywords_found'].update(
                                    keywords)
                                monitoring_stats['priority_flags'].update(
                                    priority_flags)

                                # Emergency vs event categorization
                                if has_priority:
                                    monitoring_stats['priority_tweets'] += 1

                                    # Use emergency keywords directly from BaseCollector.PRIORITY_KEYWORDS
                                    emergency_terms = [
                                        keyword for keyword in BaseCollector.PRIORITY_KEYWORDS
                                        if keyword in ['911', 'emergency', 'fire', 'shooting', 'explosion',
                                                       'ambulance', 'police', 'evacuation', 'lockdown', 'collapse',
                                                       'accident', 'power outage', 'blackout', 'gas leak', 'outbreak']
                                    ]

                                    has_emergency = any(
                                        term in priority_flags for term in emergency_terms)

                                    if has_emergency:
                                        monitoring_stats['emergency_tweets'] += 1
                                        logger.warning(f"🚨 EMERGENCY TWEET: {signal['title'][:60]}... "
                                                       f"(Keywords: {priority_flags})")
                                    else:
                                        logger.info(f"🎉 EVENT/GATHERING TWEET: {signal['title'][:60]}... "
                                                    f"(Keywords: {priority_flags})")
                                elif keywords:
                                    logger.info(f"⚠️  RELEVANT TWEET: {signal['title'][:60]}... "
                                                f"(Keywords: {keywords})")

                            # Rate limiting - small delay between tweet processing
                            if query_tweet_count % 10 == 0:
                                await asyncio.sleep(0.1)

                        except Exception as e:
                            logger.error(f"❌ Error processing tweet: {str(e)}")
                            continue

                    logger.info(
                        f"✅ Processed {query_tweet_count} tweets from query {i}")

                    # Prevent hitting rate limits
                    if monitoring_stats['total_tweets'] >= self.max_total_tweets:
                        logger.info(
                            f"📊 Reached tweet limit ({self.max_total_tweets}), stopping collection")
                        break

                    # Rate limiting between queries
                    await asyncio.sleep(1.0)

                except Exception as e:
                    logger.error(f"❌ Error executing query {i}: {str(e)}")
                    continue

            # Sort signals: priority content first, then by engagement
            all_signals.sort(key=lambda x: (
                x['metadata'].get('has_priority_content',
                                  False),  # Priority first
                x.get('score', 0)  # Then by engagement score
            ), reverse=True)

            # Remove duplicates based on tweet ID
            unique_signals = []
            seen_ids = set()
            for signal in all_signals:
                tweet_id = signal['metadata'].get('tweet_id')
                if tweet_id and tweet_id not in seen_ids:
                    unique_signals.append(signal)
                    seen_ids.add(tweet_id)

            # Report monitoring summary
            logger.info(f"📊 TWITTER MONITORING SUMMARY:")
            logger.info(
                f"   Queries executed: {monitoring_stats['queries_executed']}")
            logger.info(
                f"   Total tweets analyzed: {monitoring_stats['total_tweets']}")
            logger.info(
                f"   Relevant tweets: {monitoring_stats['relevant_tweets']}")
            logger.info(
                f"   Priority tweets: {monitoring_stats['priority_tweets']}")
            logger.info(
                f"   Emergency tweets: {monitoring_stats['emergency_tweets']}")

            if monitoring_stats['priority_flags']:
                logger.warning(
                    f"🚨 PRIORITY KEYWORDS DETECTED: {list(monitoring_stats['priority_flags'])}")

            if monitoring_stats['keywords_found']:
                top_keywords = list(monitoring_stats['keywords_found'])[:10]
                logger.info(f"🔍 Priority keywords found: {top_keywords}")

            logger.info(
                f"📊 COLLECTION SUMMARY: {len(unique_signals)} unique Twitter signals collected")

            return unique_signals

        except Exception as e:
            logger.error(
                f"❌ FATAL ERROR in Twitter signal collection: {str(e)}")
            logger.error(f"   Exception type: {type(e).__name__}")
            return []

    async def _tweet_to_signal(self, tweet, search_query: str) -> Optional[Dict]:
        """Convert Twitter tweet to standardized signal format"""
        try:
            # Extract tweet data
            tweet_text = getattr(tweet, 'text', '')
            tweet_id = getattr(tweet, 'id', '')
            created_at = getattr(tweet, 'created_at', datetime.utcnow())

            # Handle timezone
            if created_at and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            # Get public metrics (engagement)
            public_metrics = getattr(tweet, 'public_metrics', {})
            retweet_count = public_metrics.get('retweet_count', 0)
            like_count = public_metrics.get('like_count', 0)
            reply_count = public_metrics.get('reply_count', 0)
            quote_count = public_metrics.get('quote_count', 0)

            # Calculate engagement score
            engagement_score = (
                retweet_count * 3) + (like_count * 1) + (reply_count * 2) + (quote_count * 2)

            # Check NYC relevance (filter broader searches)
            if not self._is_nyc_relevant(tweet_text, ''):
                logger.debug(f"🚫 Filtered non-NYC tweet: {tweet_text[:60]}...")
                return None

            # Analyze keywords for priority detection
            keyword_analysis = self._analyze_keywords(tweet_text, '')

            # Extract location information
            location_info = self.location_extractor.extract_location_info(
                tweet_text, '')

            # Geocode location information
            geocoding_result = await self._geocode_location_info(location_info, tweet_text, '')

            # Assess location specificity
            location_specificity = self._assess_location_specificity(
                tweet_text, '', location_info)

            # Filter out tweets without sufficient location specificity unless high priority
            if not location_specificity['is_specific'] and not keyword_analysis['has_priority_content']:
                logger.debug(
                    f"🚫 Filtered tweet due to insufficient location specificity: {tweet_text[:60]}...")
                return None

            # Build tweet URL
            tweet_url = f"https://twitter.com/user/status/{tweet_id}"

            raw_signal = {
                'title': tweet_text,  # For tweets, text is the title
                'content': '',        # No separate content for tweets
                'url': tweet_url,
                'score': engagement_score,
                'comments': reply_count,
                'shares': retweet_count,
                'created_at': created_at,
                'timestamp': created_at,
                'full_text': tweet_text,
                'content_length': len(tweet_text),
                'metadata': {
                    'tweet_id': str(tweet_id),
                    'search_query': search_query,
                    'author_id': getattr(tweet, 'author_id', ''),
                    'retweet_count': retweet_count,
                    'like_count': like_count,
                    'reply_count': reply_count,
                    'quote_count': quote_count,
                    'engagement_score': engagement_score,
                    # Priority keyword analysis
                    'priority_keywords': keyword_analysis['keywords'],
                    'has_priority_content': keyword_analysis['has_priority_content'],
                    'priority_flags': keyword_analysis['priority_flags'],
                    'keyword_count': keyword_analysis['keyword_count'],
                    'nyc_relevant': True,  # All returned signals are NYC-relevant
                    # Location data with geocoding
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

            return self.standardize_signal(raw_signal)

        except Exception as e:
            logger.error(f"❌ Failed to parse tweet: {e}")
            logger.error(f"   Tweet ID: {getattr(tweet, 'id', 'unknown')}")
            return None

    async def _geocode_location_info(self, location_info: Dict, title: str, content: str) -> Dict:
        """
        Geocode location information to get real coordinates
        (Same logic as other collectors)
        """
        try:
            locations = location_info['locations_found']
            borough = location_info.get('primary_borough')

            if locations:
                first_location = locations[0]
                if isinstance(first_location, dict):
                    location_text = first_location.get('name', '')
                else:
                    location_text = str(first_location)

                logger.debug(
                    f"Geocoding Twitter location: '{location_text}' with borough: '{borough}'")
                geocoding_result = await geocode_nyc_location(location_text, borough)
            elif borough:
                logger.debug(f"Geocoding Twitter borough: '{borough}'")
                geocoding_result = await geocode_nyc_location(borough)
            else:
                return self._empty_geocoding_result()

            return geocoding_result
        except Exception as e:
            logger.warning(f"Warning: Failed to geocode Twitter location: {e}")
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
