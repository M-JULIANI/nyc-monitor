"""
Base collector class for NYC monitor system.
Focused on simple data collection - analysis is handled by the triage agent.
"""
from abc import ABC, abstractmethod
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Abstract base class for all data collectors"""

    def __init__(self, source_name: str):
        """
        Initialize the collector

        Args:
            source_name: Name of the data source (e.g., 'reddit', 'twitter')
        """
        self.source_name = source_name
        self.logger = logging.getLogger(f"{__name__}.{source_name}")

    @abstractmethod
    async def collect_signals(self) -> List[Dict]:
        """
        Collect raw signals/data from the source

        Returns:
            List of raw data items for triage analysis
        """
        pass

    def standardize_signal(self, raw_item: Dict) -> Dict:
        """
        Standardize a raw signal into consistent format

        Args:
            raw_item: Raw data item from the source

        Returns:
            Standardized signal format
        """
        return {
            'source': self.source_name,
            'title': raw_item.get('title', ''),
            'content': raw_item.get('content', ''),
            'url': raw_item.get('url', ''),
            'timestamp': raw_item.get('created_at') or raw_item.get('timestamp'),
            'engagement': {
                'score': raw_item.get('score', 0),
                'comments': raw_item.get('comments', 0),
                'shares': raw_item.get('shares', 0)
            },
            'metadata': raw_item.get('metadata', {}),
            'raw_data': raw_item  # Keep original for detailed analysis if needed
        }
