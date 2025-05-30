"""
Reddit collector for NYC monitor system.
Collects raw data from NYC-related subreddits for triage analysis.
"""
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from redditwarp.ASYNC import Client
from redditwarp.models.submission_ASYNC import LinkPost, TextPost, GalleryPost
import logging

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


class RedditCollector(BaseCollector):
    """Reddit collector for NYC signals"""

    def __init__(self):
        super().__init__("reddit")

        # Reddit API credentials
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.refresh_token = os.getenv("REDDIT_REFRESH_TOKEN")

        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError(
                "Missing Reddit API credentials. Please set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_REFRESH_TOKEN environment variables.")

        self.client = Client(
            self.client_id, self.client_secret, self.refresh_token)

        # NYC-specific subreddits to monitor
        self.nyc_subreddits = [
            'nyc', 'newyorkcity', 'manhattan', 'brooklyn', 'queens',
            'bronx', 'statenisland', 'asknyc', 'nycapartments', 'nycjobs'
        ]

    async def collect_signals(self) -> List[Dict]:
        """
        Collect recent signals from NYC subreddits

        Returns:
            List of raw Reddit signals for triage analysis
        """
        try:
            all_signals = []

            # Collect recent hot posts from NYC subreddits
            for subreddit in self.nyc_subreddits:
                try:
                    signals = await self._fetch_subreddit_signals(subreddit, limit=10)
                    all_signals.extend(signals)
                    self.logger.debug(
                        f"Collected {len(signals)} signals from r/{subreddit}")
                except Exception as e:
                    self.logger.warning(
                        f"Error collecting from r/{subreddit}: {str(e)}")
                    continue

            self.logger.info(
                f"Collected {len(all_signals)} total Reddit signals")
            return all_signals

        except Exception as e:
            self.logger.error(f"Error in Reddit signal collection: {str(e)}")
            return []

    async def _fetch_subreddit_signals(self, subreddit: str, limit: int = 10) -> List[Dict]:
        """Fetch recent signals from a specific subreddit"""
        signals = []

        try:
            # Get both hot and new posts for better coverage
            hot_posts = []
            new_posts = []

            # Fetch hot posts
            async for submission in self.client.p.subreddit.pull.hot(subreddit, limit=limit//2):
                hot_posts.append(
                    self._submission_to_signal(submission, subreddit))

            # Fetch recent posts (last 4 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=4)
            async for submission in self.client.p.subreddit.pull.new(subreddit, limit=limit):
                post_time = datetime.fromtimestamp(submission.created_ts)
                if post_time >= cutoff_time:
                    new_posts.append(
                        self._submission_to_signal(submission, subreddit))
                else:
                    break  # Posts are ordered by time, so we can break early

            # Combine and deduplicate
            all_posts = hot_posts + new_posts
            seen_ids = set()
            for post in all_posts:
                post_id = post['metadata']['post_id']
                if post_id not in seen_ids:
                    signals.append(post)
                    seen_ids.add(post_id)

            return signals[:limit]  # Return top N unique posts

        except Exception as e:
            self.logger.error(f"Error fetching from r/{subreddit}: {str(e)}")
            return []

    def _submission_to_signal(self, submission, subreddit: str) -> Dict:
        """Convert Reddit submission to standardized signal format"""
        raw_signal = {
            'title': submission.title,
            'content': self._get_content(submission),
            'url': f"https://reddit.com{submission.permalink}",
            'score': submission.score,
            'comments': submission.comment_count,
            'shares': 0,  # Reddit doesn't track shares
            'created_at': datetime.fromtimestamp(submission.created_ts),
            'timestamp': datetime.fromtimestamp(submission.created_ts),
            'metadata': {
                'subreddit': subreddit,
                'post_id': submission.id36,
                'post_type': self._get_post_type(submission),
                'author': submission.author_display_name or '[deleted]',
                'is_stickied': getattr(submission, 'is_stickied', False),
                'is_nsfw': getattr(submission, 'is_nsfw', False)
            }
        }

        return self.standardize_signal(raw_signal)

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
        if isinstance(submission, LinkPost):
            return submission.url or ''
        elif isinstance(submission, TextPost):
            return submission.body or ''
        elif isinstance(submission, GalleryPost):
            return str(submission.gallery_link) if hasattr(submission, 'gallery_link') else ''
        return ''
