"""
NYC 311 Service Requests collector for NYC monitor system.
Collects raw 311 data for triage analysis.
"""
import os
import requests
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging
from collections import defaultdict

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


class NYC311Collector(BaseCollector):
    """NYC 311 Service Requests collector"""

    def __init__(self):
        super().__init__("nyc_311")

        # NYC Open Data 311 API endpoint
        self.base_url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

        # Optional app token for higher rate limits (register at NYC Open Data)
        self.app_token = os.getenv("NYC_311_APP_TOKEN")
        self.headers = {
            "X-App-Token": self.app_token} if self.app_token else {}

        # Debug logging for credentials
        logger.info("🔑 NYC 311 API CREDENTIALS CHECK:")
        logger.info(
            f"   APP_TOKEN: {'✅ SET' if self.app_token else '❌ MISSING (optional - using public access)'} ({self.app_token[:10] + '...' if self.app_token else 'None'})")

        if not self.app_token:
            logger.info(
                "💡 For higher rate limits, register for free app token at: https://data.cityofnewyork.us/")

        # Emergency-related complaint types for priority detection
        self.emergency_complaint_types = [
            'Emergency Response Team (ERT)',
            'Fire Safety Director - F58',
            'Gas',
            'Lead',
            'Water System',
            'Electrical',
            'Emergency',
            'Fire/EMS',
            'Police Department',
            'Structural',
            'Building/Use',
            'Construction',
            'Scaffold Safety',
            'Elevator',
            'Plumbing',
            'Heat/Hot Water'
        ]

        # Event-related complaint types
        self.event_complaint_types = [
            'Special Event',
            'Parade Permit',
            'Block Party',
            'Film Permit',
            'Sidewalk Café',
            'Street Fair Permit',
            'Public Assembly',
            'Street Festival',
            'Outdoor Event'
        ]

        # Emergency keywords in descriptions
        self.emergency_keywords = [
            'EMERGENCY', 'EXPLOSION', 'FIRE', 'GAS LEAK', 'WATER MAIN',
            'POWER OUTAGE', 'STRUCTURAL', 'COLLAPSE', 'EVACUATION',
            'FLOODING', 'BLACKOUT', 'ACCIDENT', 'URGENT'
        ]

        logger.info(
            f"📍 Monitoring {len(self.emergency_complaint_types)} emergency complaint types")
        logger.info(
            f"🎉 Monitoring {len(self.event_complaint_types)} event complaint types")

    async def collect_signals(self) -> List[Dict]:
        """
        Collect recent 311 signals with priority-based filtering for triage analysis

        Returns:
            List of raw 311 signals for triage analysis
        """
        logger.info("🔍 STARTING NYC 311 SIGNAL COLLECTION")

        try:
            all_signals = []
            collection_stats = {
                'total_requests': 0,
                'emergency_requests': 0,
                'event_requests': 0,
                'high_volume_areas': 0,
                'complaint_types_found': set(),
                'agencies_involved': set(),
                'boroughs_active': set()
            }

            # Calculate time window (last 2 days to account for API delays)
            now = datetime.utcnow()
            since = now - timedelta(days=2)
            since_str = since.strftime('%Y-%m-%dT%H:%M:%S.000')

            logger.info(
                f"📅 Collecting 311 requests since: {since_str} (last 2 days)")
            logger.info(
                f"🕐 Current time: {now.strftime('%Y-%m-%dT%H:%M:%S.000')}")

            # Collect different types of 311 signals
            signals_collected = await self._collect_priority_signals(since_str, collection_stats)
            all_signals.extend(signals_collected)

            # Report collection summary
            logger.info(f"📊 NYC 311 COLLECTION SUMMARY:")
            logger.info(
                f"   Total requests: {collection_stats['total_requests']}")
            logger.info(
                f"   Emergency requests: {collection_stats['emergency_requests']}")
            logger.info(
                f"   Event requests: {collection_stats['event_requests']}")
            logger.info(
                f"   Boroughs active: {len(collection_stats['boroughs_active'])}")
            logger.info(
                f"   Agencies involved: {len(collection_stats['agencies_involved'])}")

            if collection_stats['emergency_requests'] > 0:
                logger.warning(
                    f"🚨 EMERGENCY SIGNALS: {collection_stats['emergency_requests']} emergency-related 311 requests detected")

            if collection_stats['event_requests'] > 0:
                logger.info(
                    f"🎉 EVENT SIGNALS: {collection_stats['event_requests']} event-related 311 requests detected")

            logger.info(
                f"📊 COLLECTION COMPLETE: {len(all_signals)} total 311 signals collected")
            return all_signals

        except Exception as e:
            logger.error(
                f"❌ FATAL ERROR in NYC 311 signal collection: {str(e)}")
            logger.error(f"   Exception type: {type(e).__name__}")
            return []

    async def _collect_priority_signals(self, since_time: str, stats: Dict) -> List[Dict]:
        """Collect priority 311 signals: emergency, events, and volume spikes"""
        all_signals = []

        # 1. Emergency-related requests
        emergency_signals = await self._fetch_emergency_requests(since_time, stats)
        all_signals.extend(emergency_signals)

        # 2. Event-related requests
        event_signals = await self._fetch_event_requests(since_time, stats)
        all_signals.extend(event_signals)

        # 3. High-volume general requests (potential incidents)
        volume_signals = await self._fetch_high_volume_requests(since_time, stats)
        all_signals.extend(volume_signals)

        # 4. Geographic clusters (same complaint type in same area)
        cluster_signals = await self._fetch_geographic_clusters(since_time, stats)
        all_signals.extend(cluster_signals)

        return all_signals

    async def _fetch_emergency_requests(self, since_time: str, stats: Dict) -> List[Dict]:
        """Fetch emergency-related 311 requests"""
        logger.info("🚨 Fetching emergency-related 311 requests")

        try:
            # Build filter for emergency complaint types
            emergency_filter = " OR ".join(
                [f"complaint_type='{ct}'" for ct in self.emergency_complaint_types])

            params = {
                '$where': f"created_date >= '{since_time}' AND ({emergency_filter})",
                '$select': 'unique_key,created_date,complaint_type,descriptor,borough,latitude,longitude,incident_zip,agency,agency_name,status,due_date',
                '$limit': 500,
                '$order': 'created_date DESC'
            }

            response = requests.get(
                self.base_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()

            emergency_data = response.json()
            logger.info(
                f"📞 Found {len(emergency_data)} emergency-type 311 requests")

            # Also search for emergency keywords in descriptions
            keyword_filter = " OR ".join(
                [f"descriptor LIKE '%{kw}%'" for kw in self.emergency_keywords])

            params_desc = {
                '$where': f"created_date >= '{since_time}' AND ({keyword_filter})",
                '$select': 'unique_key,created_date,complaint_type,descriptor,borough,latitude,longitude,incident_zip,agency,agency_name,status,due_date',
                '$limit': 300,
                '$order': 'created_date DESC'
            }

            response_desc = requests.get(
                self.base_url, params=params_desc, headers=self.headers, timeout=30)
            response_desc.raise_for_status()

            keyword_data = response_desc.json()
            logger.info(
                f"🔍 Found {len(keyword_data)} requests with emergency keywords")

            # Combine and deduplicate
            all_emergency = emergency_data + keyword_data
            seen_ids = set()
            unique_emergency = []

            for request in all_emergency:
                request_id = request.get('unique_key')
                if request_id and request_id not in seen_ids:
                    seen_ids.add(request_id)
                    unique_emergency.append(request)

            logger.info(
                f"✅ Collected {len(unique_emergency)} unique emergency 311 requests")

            # Convert to standardized signals
            signals = []
            for request in unique_emergency:
                signal = await self._request_to_signal(request, 'emergency', stats)
                if signal:
                    signals.append(signal)
                    stats['emergency_requests'] += 1

            return signals

        except Exception as e:
            logger.error(f"❌ Error fetching emergency 311 requests: {e}")
            return []

    async def _fetch_event_requests(self, since_time: str, stats: Dict) -> List[Dict]:
        """Fetch event-related 311 requests"""
        logger.info("🎉 Fetching event-related 311 requests")

        try:
            # Build filter for event complaint types
            event_filter = " OR ".join(
                [f"complaint_type LIKE '%{et}%'" for et in self.event_complaint_types])

            params = {
                '$where': f"created_date >= '{since_time}' AND ({event_filter})",
                '$select': 'unique_key,created_date,complaint_type,descriptor,borough,latitude,longitude,incident_zip,agency,agency_name,status,due_date',
                '$limit': 200,
                '$order': 'created_date DESC'
            }

            response = requests.get(
                self.base_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()

            event_data = response.json()
            logger.info(
                f"🎭 Found {len(event_data)} event-related 311 requests")

            # Convert to standardized signals
            signals = []
            for request in event_data:
                signal = await self._request_to_signal(request, 'event', stats)
                if signal:
                    signals.append(signal)
                    stats['event_requests'] += 1

            return signals

        except Exception as e:
            logger.error(f"❌ Error fetching event 311 requests: {e}")
            return []

    async def _fetch_high_volume_requests(self, since_time: str, stats: Dict) -> List[Dict]:
        """Fetch general requests to detect volume spikes"""
        logger.info("📈 Fetching general 311 requests for volume analysis")

        try:
            params = {
                '$where': f"created_date >= '{since_time}'",
                '$select': 'unique_key,created_date,complaint_type,descriptor,borough,latitude,longitude,incident_zip,agency,agency_name,status',
                '$limit': 300,
                '$order': 'created_date DESC'
            }

            response = requests.get(
                self.base_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()

            volume_data = response.json()
            logger.info(
                f"📊 Found {len(volume_data)} recent 311 requests for volume analysis")

            # Convert to standardized signals
            signals = []
            for request in volume_data:
                signal = await self._request_to_signal(request, 'volume', stats)
                if signal:
                    signals.append(signal)

            return signals

        except Exception as e:
            logger.error(f"❌ Error fetching volume 311 requests: {e}")
            return []

    async def _fetch_geographic_clusters(self, since_time: str, stats: Dict) -> List[Dict]:
        """Fetch requests with coordinates for geographic cluster analysis"""
        logger.info("🗺️ Fetching geolocated 311 requests for cluster analysis")

        try:
            params = {
                '$where': f"created_date >= '{since_time}' AND latitude IS NOT NULL AND longitude IS NOT NULL",
                '$select': 'unique_key,created_date,complaint_type,descriptor,borough,latitude,longitude,incident_zip,community_board,agency,agency_name',
                '$limit': 400,
                '$order': 'created_date DESC'
            }

            response = requests.get(
                self.base_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()

            geo_data = response.json()
            logger.info(f"📍 Found {len(geo_data)} geolocated 311 requests")

            # Convert to standardized signals
            signals = []
            for request in geo_data:
                signal = await self._request_to_signal(request, 'geographic', stats)
                if signal:
                    signals.append(signal)

            return signals

        except Exception as e:
            logger.error(f"❌ Error fetching geographic 311 requests: {e}")
            return []

    async def _request_to_signal(self, request: Dict, signal_category: str, stats: Dict) -> Optional[Dict]:
        """Convert 311 request to standardized signal format"""
        try:
            # Extract basic information
            unique_key = request.get('unique_key', '')
            created_date = request.get('created_date', '')
            complaint_type = request.get('complaint_type', 'Unknown')
            descriptor = request.get('descriptor', '')
            borough = request.get('borough', 'Unknown')
            agency = request.get('agency', 'Unknown')
            agency_name = request.get('agency_name', agency)
            status = request.get('status', 'Unknown')

            # Parse coordinates
            latitude = request.get('latitude')
            longitude = request.get('longitude')
            has_coordinates = latitude is not None and longitude is not None

            # Parse created date
            try:
                if created_date:
                    # NYC 311 API returns ISO format: "2024-12-03T15:30:00.000"
                    created_at = datetime.fromisoformat(
                        created_date.replace('Z', '+00:00'))
                else:
                    created_at = datetime.utcnow()
            except:
                created_at = datetime.utcnow()

            # Update collection statistics
            stats['total_requests'] += 1
            stats['complaint_types_found'].add(complaint_type)
            stats['agencies_involved'].add(agency_name)
            stats['boroughs_active'].add(borough)

            # Analyze keywords for priority detection (inherited from BaseCollector)
            keyword_analysis = self._analyze_keywords(
                complaint_type, descriptor)

            # Determine priority level based on complaint type and keywords
            is_emergency = (complaint_type in self.emergency_complaint_types or
                            any(keyword.upper() in descriptor.upper() for keyword in self.emergency_keywords))
            is_event = complaint_type in self.event_complaint_types

            # Create standardized signal
            raw_signal = {
                'title': f"{complaint_type}: {descriptor[:100]}" if descriptor else complaint_type,
                'content': f"311 Request: {complaint_type}\nDescription: {descriptor}\nBorough: {borough}\nAgency: {agency_name}\nStatus: {status}",
                # Generic 311 portal URL
                'url': f"https://portal.311.nyc.gov/article/?kanumber=KA-01010",
                # Priority scoring
                'score': 5 + (5 if is_emergency else 0) + (3 if is_event else 0),
                'comments': 0,  # 311 doesn't have comments
                'shares': 0,    # 311 doesn't have shares
                'created_at': created_at,
                'timestamp': created_at,
                'full_text': f"{complaint_type} {descriptor}".strip(),
                'content_length': len(descriptor) if descriptor else 0,
                'metadata': {
                    'unique_key': unique_key,
                    'complaint_type': complaint_type,
                    'descriptor': descriptor,
                    'borough': borough,
                    'agency': agency,
                    'agency_name': agency_name,
                    'status': status,
                    'incident_zip': request.get('incident_zip', ''),
                    'community_board': request.get('community_board', ''),
                    'due_date': request.get('due_date', ''),

                    # Location data
                    'latitude': float(latitude) if latitude else None,
                    'longitude': float(longitude) if longitude else None,
                    'has_coordinates': has_coordinates,

                    # Priority analysis
                    'signal_category': signal_category,
                    'is_emergency': is_emergency,
                    'is_event': is_event,
                    'priority_keywords': keyword_analysis['keywords'],
                    'has_priority_content': keyword_analysis['has_priority_content'],
                    'priority_flags': keyword_analysis['priority_flags'],
                    'keyword_count': keyword_analysis['keyword_count'],

                    # NYC relevance (always true for 311)
                    'nyc_relevant': True,
                    'primary_borough': borough,
                }
            }

            return self.standardize_signal(raw_signal)

        except Exception as e:
            logger.error(f"❌ Failed to parse 311 request: {e}")
            logger.error(f"   Request data: {request}")
            return None
