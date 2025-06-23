"""
Twitter collector for NYC monitor system.
Collects recent tweets with NYC-related content and emergency/event keywords.
Optimized for reliable 15-minute monitoring cycles.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging
import re
import tweepy
import asyncio
import json
from pathlib import Path

from .base_collector import BaseCollector
from monitor.utils.location_extractor import NYCLocationExtractor
from monitor.utils.geocode import geocode_nyc_location

logger = logging.getLogger(__name__)


class TwitterCollector(BaseCollector):
    """Twitter collector for NYC signals - optimized for reliability"""

    def __init__(self):
        super().__init__("twitter")

        # Create debug directory if it doesn't exist
        self.debug_dir = Path("debug/twitter")
        self.debug_dir.mkdir(parents=True, exist_ok=True)

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

        # Search parameters - optimized for 15-minute cycles
        self.max_tweets_per_query = 5      # Reduce from 10 to 5 to avoid rate limits
        self.time_window_hours = 2         # Increase to 2 hours for more coverage
        self.max_collection_time = 30      # Reduce to 30 seconds to be safer
        self.wait_on_rate_limit = True     # Change to True to handle rate limits better
        self.rate_limit_reset_time = None  # Track when rate limit will reset
        self.contexts_per_cycle = 2        # Reduce from 3 to 2 contexts per cycle
        self.delay_between_contexts = 5    # Increase delay from 2 to 5 seconds

        # NYC contexts to monitor - simplified and more targeted
        self.nyc_contexts = [
            # Core NYC areas - prioritize Manhattan and Brooklyn with more targeted searches
            {'name': 'NYC_Emergency',
                'query': '(NYC OR "New York") (emergency OR fire OR police OR ambulance) -is:retweet -is:reply lang:en', 'priority': 1},
            {'name': 'NYC_Events',
                'query': '(NYC OR "New York") (parade OR festival OR concert OR protest OR event OR closing OR traffic) -is:retweet -is:reply lang:en', 'priority': 1},
            {'name': 'NYC_Infrastructure',
                'query': '(NYC OR "New York") (subway OR "power outage" OR "water main" OR "road closure" OR MTA) -is:retweet -is:reply lang:en', 'priority': 2},
            {'name': 'Manhattan_Local',
                'query': 'Manhattan (happening OR breaking OR live OR urgent OR now) -is:retweet -is:reply lang:en', 'priority': 2},
            {'name': 'Brooklyn_Local',
                'query': 'Brooklyn (happening OR breaking OR live OR urgent OR now) -is:retweet -is:reply lang:en', 'priority': 3},
        ]

        # Sort contexts by priority
        self.nyc_contexts.sort(key=lambda x: x['priority'])

        # Priority terms from BaseCollector.PRIORITY_KEYWORDS
        # No need to redefine - we'll use self.priority_keywords

        logger.info(
            f"🔍 Monitoring {len(self.nyc_contexts)} NYC contexts (processing {self.contexts_per_cycle} per cycle)")
        logger.info(
            f"   Priority terms: {', '.join(self.priority_keywords[:5])}...")

        # Initialize Twitter API clients
        try:
            logger.info("🔗 Initializing Twitter API clients...")
            self.client_v2 = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_key_secret,
                wait_on_rate_limit=self.wait_on_rate_limit
            )
            logger.info("✅ Twitter API client initialized successfully")
        except Exception as e:
            logger.error(
                f"❌ Failed to initialize Twitter API client: {str(e)}")
            raise

        # Initialize location extractor
        self.location_extractor = NYCLocationExtractor()
        logger.info(
            f"🗺️ Location extractor initialized with {self.location_extractor.get_location_count()} NYC locations")

    async def collect_signals(self) -> List[Dict]:
        """
        Collect recent signals from Twitter with reliable monitoring
        Optimized for 15-minute monitoring cycles
        """
        logger.info("🔍 STARTING TWITTER SIGNAL COLLECTION")
        try:
            all_signals = []
            monitoring_stats = {
                'contexts_processed': 0,
                'total_tweets': 0,
                'relevant_tweets': 0,
                'context_stats': {},
                'collection_time': 0,
                'rate_limits_hit': 0,
                'raw_tweets': [],
                'time_limit_reached': False,
                'contexts_skipped': []  # Track which contexts were skipped
            }

            # Calculate time window for recent tweets
            since_time = datetime.utcnow().replace(tzinfo=timezone.utc) - \
                timedelta(hours=self.time_window_hours)
            start_time = datetime.utcnow()

            # Process only top N contexts per cycle
            contexts_to_process = self.nyc_contexts[:self.contexts_per_cycle]

            # Process each NYC context (similar to Reddit's subreddit approach)
            for context in contexts_to_process:
                try:
                    # Check if we've hit our time limit
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed > self.max_collection_time:
                        logger.warning(
                            f"⏰ Collection time limit ({self.max_collection_time}s) reached, stopping")
                        monitoring_stats['time_limit_reached'] = True
                        # Add remaining contexts to skipped list
                        remaining_contexts = [
                            c['name'] for c in contexts_to_process[monitoring_stats['contexts_processed']:]]
                        monitoring_stats['contexts_skipped'].extend(
                            remaining_contexts)
                        break

                    # Check if we're in a rate limit cooldown
                    if self.rate_limit_reset_time and datetime.utcnow() < self.rate_limit_reset_time:
                        remaining = (self.rate_limit_reset_time -
                                     datetime.utcnow()).total_seconds()
                        if remaining > self.max_collection_time - elapsed:
                            logger.warning(
                                f"⏰ Rate limit cooldown ({remaining:.0f}s) would exceed time limit, stopping")
                            monitoring_stats['time_limit_reached'] = True
                            # Add remaining contexts to skipped list
                            remaining_contexts = [
                                c['name'] for c in contexts_to_process[monitoring_stats['contexts_processed']:]]
                            monitoring_stats['contexts_skipped'].extend(
                                remaining_contexts)
                            break
                        logger.info(
                            f"⏳ Waiting for rate limit reset ({remaining:.0f}s remaining)")
                        await asyncio.sleep(min(remaining, self.max_collection_time - elapsed))
                        if (datetime.utcnow() - start_time).total_seconds() > self.max_collection_time:
                            logger.warning(
                                "⏰ Time limit reached during rate limit cooldown")
                            monitoring_stats['time_limit_reached'] = True
                            break

                    context_name = context['name']
                    base_query = context['query']
                    logger.info(
                        f"🔍 Processing {context_name} context (Priority: {context['priority']})")

                    try:
                        # Add delay between contexts to avoid rate limits
                        if monitoring_stats['contexts_processed'] > 0:
                            await asyncio.sleep(self.delay_between_contexts)

                        # Search recent tweets for this context
                        tweets = self.client_v2.search_recent_tweets(
                            query=base_query,
                            tweet_fields=[
                                'created_at', 'public_metrics', 'geo', 'entities'],
                            user_fields=['username', 'location'],
                            expansions=['author_id', 'geo.place_id'],
                            place_fields=['full_name', 'geo'],
                            max_results=self.max_tweets_per_query,
                            start_time=since_time
                        )

                        if tweets and tweets.data:
                            # Store raw results for debugging
                            raw_batch = {
                                'context': context_name,
                                'query': base_query,
                                'timestamp': datetime.utcnow().isoformat(),
                                'tweets': [tweet.data for tweet in tweets.data],
                                'includes': tweets.includes if hasattr(tweets, 'includes') else None,
                                'meta': tweets.meta if hasattr(tweets, 'meta') else None
                            }
                            monitoring_stats['raw_tweets'].extend(
                                [tweet.data for tweet in tweets.data])

                            # Save raw results
                            debug_file = self.debug_dir / \
                                f"raw_results_{context_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                            with open(debug_file, 'w') as f:
                                json.dump(raw_batch, f,
                                          default=str, indent=2)
                            logger.info(
                                f"💾 Saved raw results to {debug_file}")

                            # Process tweets
                            context_tweets = []
                            for tweet in tweets.data:
                                monitoring_stats['total_tweets'] += 1
                                signal = await self._tweet_to_signal(tweet, base_query)
                                if signal and self._is_relevant_signal(signal):
                                    signal['metadata']['context'] = context_name
                                    context_tweets.append(signal)
                                    monitoring_stats['relevant_tweets'] += 1
                                    logger.info(
                                        f"📝 RELEVANT TWEET: {signal['title'][:60]}...")
                                    logger.info(
                                        f"   Score: {signal.get('score', 0)} | Keywords: {signal['metadata'].get('priority_keywords', [])}")

                            # Update context stats
                            monitoring_stats['context_stats'][context_name] = len(
                                context_tweets)
                            all_signals.extend(context_tweets)
                            monitoring_stats['contexts_processed'] += 1

                    except tweepy.TooManyRequests as e:
                        monitoring_stats['rate_limits_hit'] += 1
                        reset_time = getattr(e, 'reset_time', None)
                        if reset_time:
                            self.rate_limit_reset_time = reset_time
                            logger.warning(
                                f"⚠️ Rate limit hit for {context_name}. Reset at {reset_time}")
                        else:
                            # If no reset time provided, assume 15 minutes
                            self.rate_limit_reset_time = datetime.utcnow() + timedelta(minutes=15)
                            logger.warning(
                                f"⚠️ Rate limit hit for {context_name}. Assuming 15-minute cooldown.")

                        # Save rate limit info
                        rate_limit_info = {
                            'timestamp': datetime.utcnow().isoformat(),
                            'context': context_name,
                            'query': base_query,
                            'error': str(e),
                            'reset_time': self.rate_limit_reset_time.isoformat() if self.rate_limit_reset_time else None
                        }
                        debug_file = self.debug_dir / \
                            f"rate_limit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                        with open(debug_file, 'w') as f:
                            json.dump(rate_limit_info, f,
                                      default=str, indent=2)
                        break  # Stop processing when we hit a rate limit

                except Exception as e:
                    logger.error(
                        f"❌ Error processing context {context['name']}: {str(e)}")
                    continue

            # Save final monitoring stats
            stats_file = self.debug_dir / \
                f"monitoring_stats_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(stats_file, 'w') as f:
                json.dump(monitoring_stats, f, default=str, indent=2)
            logger.info(f"💾 Saved monitoring stats to {stats_file}")

            # Calculate total collection time
            end_time = datetime.utcnow()
            monitoring_stats['collection_time'] = (
                end_time - start_time).total_seconds()

            # Report monitoring summary
            logger.info(f"📊 TWITTER MONITORING SUMMARY:")
            logger.info(
                f"   Collection time: {monitoring_stats['collection_time']:.1f} seconds")
            logger.info(
                f"   Contexts processed: {monitoring_stats['contexts_processed']}/{len(self.nyc_contexts)}")
            logger.info(
                f"   Total tweets analyzed: {monitoring_stats['total_tweets']}")
            logger.info(
                f"   Relevant tweets: {monitoring_stats['relevant_tweets']}")
            logger.info(
                f"   Rate limits hit: {monitoring_stats['rate_limits_hit']}")
            if monitoring_stats['time_limit_reached']:
                logger.info("   ⚠️ Collection stopped due to time limit")
            logger.info("   Context breakdown:")
            for context, count in monitoring_stats['context_stats'].items():
                logger.info(f"      {context}: {count} tweets")

            logger.info(
                f"📊 COLLECTION SUMMARY: {len(all_signals)} unique Twitter signals collected")
            return all_signals

        except Exception as e:
            logger.error(
                f"❌ FATAL ERROR in Twitter signal collection: {str(e)}")
            logger.error(f"   Exception type: {type(e).__name__}")
            return []

    def _is_relevant_signal(self, signal: Dict) -> bool:
        """Check if a signal is relevant for NYC monitoring"""
        # Must be NYC relevant using base collector's criteria
        is_nyc_relevant = self._is_nyc_relevant(
            signal.get('title', ''),
            signal.get('content', '')
        )

        # Must have either priority keywords or location information
        has_priority = bool(signal['metadata'].get('priority_keywords'))
        has_location = bool(signal['metadata'].get('locations'))
        has_coordinates = signal['metadata'].get('has_coordinates', False)

        # Check if location is explicitly needed (like alerts ending with 'location_needed')
        needs_location = 'location_needed' in signal.get('title', '').lower()

        # Must have some engagement (retweets, likes, or replies)
        has_engagement = signal.get('score', 0) > 0

        # Log relevance details for debugging
        if is_nyc_relevant or has_priority or has_location or has_coordinates or needs_location:
            logger.debug(
                f"Signal relevance check: NYC={is_nyc_relevant}, "
                f"Priority={has_priority}, Location={has_location}, "
                f"Coords={has_coordinates}, NeedsLocation={needs_location}, Engagement={has_engagement}"
            )

        # Signal is relevant if:
        # 1. It's NYC relevant AND
        # 2. Has either priority keywords, location info, coordinates, OR needs location AND
        # 3. Has some engagement
        return (is_nyc_relevant and
                (has_priority or has_location or has_coordinates or needs_location) and
                has_engagement)

    async def _tweet_to_signal(self, tweet, search_query: str) -> Optional[Dict]:
        """Convert Twitter tweet to standardized signal format matching Reddit's structure"""
        try:
            # Extract basic tweet data
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

            # Calculate engagement score (similar to Reddit's score)
            engagement_score = (retweet_count * 2) + like_count + reply_count

            # Build tweet URL
            tweet_url = f"https://twitter.com/user/status/{tweet_id}"

            # Extract location information using the dedicated extractor with geocoding
            location_info = await self.location_extractor.extract_location_info_with_geocoding(
                tweet_text, '')

            # Extract coordinates from the geocoding-enhanced location info (matching Reddit)
            geocoding_result = {
                'lat': location_info.get('center_latitude'),
                'lng': location_info.get('center_longitude'),
                'formatted_address': location_info['locations_found'][0].get('name') if location_info['locations_found'] else None,
                'confidence': location_info['locations_found'][0].get('confidence', 0.0) if location_info['locations_found'] else 0.0,
                'source': location_info.get('geocoding_source', 'hardcoded'),
                'success': location_info.get('has_coordinates', False)
            }

            # Analyze keywords for priority content
            keyword_analysis = self._analyze_keywords(tweet_text, '')

            # Assess location specificity
            location_specificity = self._assess_location_specificity(
                tweet_text, '', location_info)

            # Extract borough from tweet text if present
            borough = None
            for b in ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']:
                if b.lower() in tweet_text.lower():
                    borough = b
                    break

            # Build standardized signal format matching Reddit's structure
            raw_signal = {
                'title': tweet_text,
                'content': '',  # Twitter doesn't have separate content
                'url': tweet_url,
                'timestamp': created_at,
                'engagement': {
                    'score': engagement_score,
                    'comments': reply_count,
                    'shares': retweet_count
                },
                'metadata': {
                    # Basic identification
                    'tweet_id': str(tweet_id),
                    'post_type': 'tweet',  # Equivalent to Reddit's post_type
                    'author': getattr(tweet, 'author_id', '[deleted]'),
                    'search_query': search_query,

                    # Priority content analysis (matching Reddit)
                    'priority_keywords': keyword_analysis['keywords'],
                    'has_priority_content': keyword_analysis['has_priority_content'],
                    'priority_flags': keyword_analysis['priority_flags'],
                    'keyword_count': keyword_analysis['keyword_count'],
                    'nyc_relevant': True,  # All returned signals are NYC-relevant

                    # Location information (matching Reddit)
                    'locations': location_info['locations_found'],
                    'latitude': geocoding_result['lat'],
                    'longitude': geocoding_result['lng'],
                    'formatted_address': geocoding_result['formatted_address'],
                    'geocoding_confidence': geocoding_result['confidence'],
                    'geocoding_source': geocoding_result['source'],
                    'location_count': location_info['location_count'],
                    'primary_borough': borough or location_info['primary_borough'],
                    'has_coordinates': geocoding_result['success'],

                    # Location specificity (matching Reddit)
                    'location_specificity': location_specificity['specificity_score'],
                    'specific_streets': location_specificity['specific_streets'],
                    'named_venues': location_specificity['named_venues'],
                    'cross_streets': location_specificity['cross_streets'],
                    'has_actionable_location': location_specificity['is_specific'],

                    # Twitter-specific metrics
                    'retweet_count': retweet_count,
                    'like_count': like_count,
                    'reply_count': reply_count,
                    'engagement_score': engagement_score,
                    'context': None  # Will be set by collect_signals
                },
                'raw_data': tweet.data  # Original tweet data
            }

            return self.standardize_signal(raw_signal)

        except Exception as e:
            logger.error(f"❌ Failed to parse tweet: {e}")
            logger.error(f"   Tweet ID: {getattr(tweet, 'id', 'unknown')}")
            return None

    # Old geocoding methods removed - now using location_extractor.extract_location_info_with_geocoding()
