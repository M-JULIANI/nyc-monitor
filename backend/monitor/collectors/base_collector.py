"""
Base collector class for NYC monitor system.
Focused on simple data collection - analysis is handled by the triage agent.
"""
from abc import ABC, abstractmethod
from typing import List, Dict
import logging
import re  # Import here to avoid top-level import issues

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Abstract base class for all data collectors"""

    # Priority keywords for monitoring NYC events and emergencies
    # Shared across all collectors to ensure consistent priority detection
    PRIORITY_KEYWORDS = [
        # Immediate emergencies
        '911', 'emergency', 'fire', 'shooting', 'explosion', 'ambulance',
        'police', 'evacuation', 'lockdown', 'collapse', 'accident',

        # Infrastructure emergencies
        'power outage', 'blackout', 'gas leak', 'water main break',
        'subway shutdown', 'bridge closed', 'road closure',

        # Health/safety emergencies
        'outbreak', 'contamination', 'air quality alert', 'heat emergency',

        # Major public events and crowd gatherings
        'parade', 'festival', 'pride', 'concert', 'marathon', 'protest',
        'rally', 'demonstration', 'march', 'celebration', 'block party',
        'street fair', 'outdoor event', 'large crowd', 'street closure',
        'event permit', 'public gathering', 'street festival',

        # Seasonal/Annual NYC events
        'halloween parade', 'thanksgiving parade', 'new year', 'fourth of july',
        'summer streets', 'outdoor cinema', 'bryant park', 'central park event',
        'times square event', 'brooklyn bridge park', 'pier event',

        # Sports and entertainment events
        'yankees game', 'mets game', 'knicks game', 'rangers game', 'nets game',
        'madison square garden', 'yankee stadium', 'citi field', 'barclays center',
        'big concert', 'broadway opening', 'fashion week',

        # Tech/startup events (for HackerNews relevance)
        'tech meetup', 'startup event', 'hackathon', 'tech conference'
    ]

    def __init__(self, source_name: str):
        """
        Initialize the collector

        Args:
            source_name: Name of the data source (e.g., 'reddit', 'hackernews')
        """
        self.source_name = source_name
        self.logger = logging.getLogger(f"{__name__}.{source_name}")

        # Make priority keywords available as instance attribute for easy access
        self.priority_keywords = self.PRIORITY_KEYWORDS

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

    def _analyze_keywords(self, title: str, content: str) -> Dict:
        """
        Priority keyword detection for NYC events and emergencies
        Shared across all collectors for consistency
        """
        try:
            # Combine title and content for analysis
            full_text = f"{title} {content}".lower()

            found_keywords = []
            priority_flags = []

            # Check for priority keywords
            for keyword in self.priority_keywords:
                if keyword.lower() in full_text:
                    found_keywords.append(keyword)
                    priority_flags.append(keyword)

            # Boolean: does this content have priority content?
            has_priority_content = len(priority_flags) > 0

            return {
                'keywords': found_keywords,
                'priority_flags': priority_flags,
                'has_priority_content': has_priority_content,
                'keyword_count': len(found_keywords)
            }

        except Exception as e:
            logger.warning(
                f"Error in {self.source_name} keyword detection: {e}")
            return {
                'keywords': [],
                'priority_flags': [],
                'has_priority_content': False,
                'keyword_count': 0
            }

    def _is_nyc_relevant(self, title: str, content: str) -> bool:
        """
        Check if content is NYC-relevant based on geographic mentions
        Shared across all collectors to ensure consistent NYC relevance criteria
        """
        full_text = f"{title} {content}".lower()

        # NYC identifiers - standardized across all collectors
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

            # Major venues
            'madison square garden', 'msg', 'yankee stadium', 'citi field',
            'barclays center', 'lincoln center', 'radio city music hall',

            # Tech/Business areas (for HackerNews/tech sources)
            'silicon alley', 'flatiron district', 'dumbo', 'brooklyn navy yard',
            'cornell tech', 'hudson yards', 'one world trade',

            # Zip codes (major ones)
            '100', '101', '102', '103', '104',  # Manhattan zip prefixes
            '112', '113', '114', '116',         # Queens zip prefixes
            '110', '111', '117',                # Queens zip prefixes
            '104', '112',                       # Bronx zip prefixes
            '103',                              # Staten Island zip prefix
        ]

        for identifier in nyc_identifiers:
            # For short abbreviations (3 chars or less), require word boundaries
            if len(identifier) <= 3:
                if re.search(rf'\b{re.escape(identifier)}\b', full_text, re.IGNORECASE):
                    return True
            else:
                # Regular substring match for longer location names
                if identifier in full_text:
                    return True

        return False

    def _assess_location_specificity(self, title: str, content: str, location_info: Dict) -> Dict:
        """
        Assess whether content has sufficient location specificity for actionable alerts
        Shared across all collectors to ensure consistent NYC location specificity criteria

        Returns:
            Dict with specificity assessment including specific streets, venues, etc.
        """
        full_text = f"{title} {content}".lower()

        specificity_score = 0
        specific_streets = []
        named_venues = []
        cross_streets = []

        # 1. Check for specific street addresses and intersections
        street_patterns = [
            # "123 Main Street"
            r'\b\d+\s+\w+\s+(street|st|avenue|ave|road|rd|boulevard|blvd|place|pl|drive|dr)\b',
            # "Main St and 5th Ave"
            r'\b\w+\s+(street|st|avenue|ave)\s+(and|&|at|\+)\s+\w+\s+(street|st|avenue|ave)\b',
            # "5th Ave between 42nd and 45th"
            r'\b\w+\s+(street|st|avenue|ave)\s+between\s+\w+\s+and\s+\w+\b',
            # Major avenues with cross streets
            r'\b(broadway|5th avenue|madison avenue|park avenue|lexington avenue|third avenue|second avenue|first avenue)\s+(and|at|between)\s+\w+\b',
        ]

        for pattern in street_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches:
                specific_streets.extend([match[0] if isinstance(
                    match, tuple) else match for match in matches])
                specificity_score += 3

        # 2. Check for named venues and landmarks
        venue_patterns = [
            r'\b(madison square garden|msg|central park|prospect park|brooklyn bridge|manhattan bridge|times square|union square|washington square park)\b',
            r'\b(yankee stadium|citi field|barclays center|lincoln center|grand central|penn station)\b',
            r'\b(world trade center|wtc|freedom tower|high line|chelsea market|south street seaport)\b',
            r'\b(\w+\s+museum|\w+\s+theater|\w+\s+hotel|\w+\s+center|\w+\s+plaza|\w+\s+square)\b',
        ]

        for pattern in venue_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches:
                named_venues.extend(matches)
                specificity_score += 2

        # 3. Check for cross-street references
        cross_street_patterns = [
            # "42nd St and 5th Ave"
            r'\b(\d+)(st|nd|rd|th)\s+(street|st)\s+(and|&|at)\s+(\w+\s+(avenue|ave))\b',
            # "Main St and Park Ave"
            r'\b(\w+\s+(street|st))\s+(and|&|at)\s+(\w+\s+(avenue|ave))\b',
        ]

        for pattern in cross_street_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches:
                cross_streets.extend(
                    [f"{match[0]}{match[1]} {match[2]} & {match[4]}" for match in matches])
                specificity_score += 2

        # 4. Check for subway station references with specificity
        subway_patterns = [
            r'\b(\w+\s+\w+)\s+station\b',  # "Union Square station"
            # "42nd St station"
            r'\b(\d+)(st|nd|rd|th)\s+(st\s+)?(station|subway)\b',
        ]

        for pattern in subway_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches:
                specificity_score += 1

        # 5. Penalty for vague location references
        vague_patterns = [
            r'\b(throughout|across|various|multiple|different)\s+(areas|locations|places|neighborhoods)\b',
            r'\b(all over|around|near|somewhere in)\s+(manhattan|brooklyn|queens|bronx|staten island)\b',
            # "downtown" without specific area
            r'\b(downtown|uptown|midtown)\b(?!\s+(manhattan|area))',
        ]

        for pattern in vague_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                specificity_score -= 2

        # Determine if location is specific enough
        is_specific = (
            specificity_score >= 2 or  # Has street addresses or multiple venue references
            len(specific_streets) > 0 or  # Has specific street addresses
            len(cross_streets) > 0 or  # Has intersection references
            # Has named venues with some specificity
            (len(named_venues) > 0 and specificity_score >= 1)
        )

        return {
            'is_specific': is_specific,
            'specificity_score': specificity_score,
            'specific_streets': specific_streets,
            'named_venues': named_venues,
            'cross_streets': cross_streets,
            'has_intersections': len(cross_streets) > 0,
            'has_venues': len(named_venues) > 0
        }
