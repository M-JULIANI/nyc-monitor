"""
Main Monitor Job for NYC Background Monitor System.
Implements the background_monitor() flow: collect signals → triage analysis → store alerts.
Designed to run every 15 minutes as a Cloud Run Job.
"""
from monitor.collectors.reddit_collector import RedditCollector
from monitor.collectors.hackernews_collector import HackerNewsCollector
from monitor.collectors.twitter_collector import TwitterCollector
from monitor.agents.triage_agent import TriageAgent
from monitor.storage.firestore_manager import FirestoreManager
from monitor.types.alert_categories import (
    categorize_monitor_event,
    get_alert_type_info,
    AlertCategory
)
import os
import asyncio
import logging
from datetime import datetime
from typing import List, Dict
import sys
import signal

# Set up the Python path to include the backend directory
backend_dir = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

# Now import using the full path from backend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            '/tmp/monitor.log') if os.path.exists('/tmp') else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MonitorJob:
    """Main background monitor job implementing the triage system"""

    def __init__(self):
        """Initialize the monitor job with collectors, triage agent, and storage"""
        self.start_time = datetime.utcnow()

        # Initialize components
        try:
            # Initialize data collectors
            self.collectors = []

            # Reddit collector (only if credentials are available)
            try:
                reddit_collector = RedditCollector()
                self.collectors.append(reddit_collector)
                logger.info("✅ Reddit collector initialized successfully")
            except ValueError as e:
                logger.warning(
                    f"⚠️  Reddit collector not initialized: {str(e)}")

            # HackerNews collector (no credentials required)
            try:
                hackernews_collector = HackerNewsCollector()
                self.collectors.append(hackernews_collector)
                logger.info("✅ HackerNews collector initialized successfully")
            except Exception as e:
                logger.warning(
                    f"⚠️  HackerNews collector not initialized: {str(e)}")

            # Twitter collector (only if credentials are available)
            try:
                twitter_collector = TwitterCollector()
                self.collectors.append(twitter_collector)
                logger.info("✅ Twitter collector initialized successfully")
            except ValueError as e:
                logger.warning(
                    f"⚠️  Twitter collector not initialized: {str(e)}")

            # Initialize triage agent
            self.triage_agent = TriageAgent()
            logger.info("Triage agent initialized successfully")

            # Initialize Firestore storage
            self.storage = FirestoreManager()
            logger.info("Firestore manager initialized successfully")

            # Job statistics
            self.stats = {
                'collectors_used': len(self.collectors),
                'signals_collected': 0,
                'alerts_generated': 0,
                'alerts_stored': 0,
                'errors': [],
                'source_stats': {}  # NEW: Detailed stats by source
            }

        except Exception as e:
            logger.error(f"Failed to initialize monitor job: {str(e)}")
            raise

    async def background_monitor(self) -> Dict:
        """
        Run the complete background monitoring cycle:
        1. Collect signals from APIs
        2. Run triage analysis 
        3. Store alerts in Firestore

        Returns:
            Dictionary with job execution statistics
        """
        logger.info("🚀 === STARTING NYC BACKGROUND MONITOR CYCLE ===")
        logger.info(f"   Timestamp: {datetime.utcnow().isoformat()}")
        logger.info(f"   Project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
        logger.info(f"   Collectors: {len(self.collectors)}")

        try:
            # Step 1: Collect raw signals from all sources
            logger.info("📡 PHASE 1: COLLECTING SIGNALS")
            raw_signals = await self._collect_all_signals()

            if not raw_signals:
                logger.warning("⚠️  No signals collected from any sources")
                logger.info(
                    "🔍 Check collector configuration and API credentials")
                return self._generate_stats_report()

            logger.info(f"✅ Collected signals from {len(raw_signals)} sources")
            for source, data in raw_signals.items():
                if isinstance(data, list):
                    logger.info(f"   📊 {source}: {len(data)} items")

            # Step 2: Query recent alerts for duplicate detection
            logger.info("🔍 PHASE 2: QUERYING RECENT ALERTS")
            recent_alerts = await self.storage.get_recent_alerts(hours_back=6)
            logger.info(
                f"📋 Found {len(recent_alerts)} recent alerts for duplicate checking")

            # Step 3: Run triage analysis on collected signals with duplicate detection
            logger.info("🧠 PHASE 3: TRIAGE ANALYSIS WITH DUPLICATE DETECTION")
            triage_results = await self._run_triage_analysis(raw_signals, recent_alerts)

            if not triage_results or not triage_results.get('alerts'):
                if triage_results and triage_results.get('error'):
                    logger.error(
                        "⚠️  Triage analysis failed - no alerts will be stored")
                    logger.error(f"   Error: {triage_results.get('error')}")
                    logger.info(
                        "📊 Raw signals collected but not processed into alerts")
                else:
                    logger.info(
                        "ℹ️  No alerts generated from current signals (normal operation)")
                    logger.info("🔍 All signals appear to be routine activity")
                return self._generate_stats_report()

            alerts = triage_results['alerts']

            # Filter out any system/fallback alerts that shouldn't go to Firestore
            real_alerts = [alert for alert in alerts
                           if alert.get('category') != 'infrastructure' or
                           'system' not in alert.get('keywords', [])]

            if len(real_alerts) != len(alerts):
                logger.info(
                    f"🔍 Filtered out {len(alerts) - len(real_alerts)} system alerts")
                alerts = real_alerts

            if not alerts:
                logger.info(
                    "ℹ️  No actionable alerts after filtering - normal operation")
                return self._generate_stats_report()

            self.stats['alerts_generated'] = len(alerts)
            logger.info(
                f"✅ Triage analysis generated {len(alerts)} actionable alerts")

            # Log alert severity and type distribution
            severity_counts = {}
            event_type_counts = {}
            for alert in alerts:
                severity = alert.get('severity', 0)
                event_type = alert.get('event_type', 'unknown')
                severity_counts[severity] = severity_counts.get(
                    severity, 0) + 1
                event_type_counts[event_type] = event_type_counts.get(
                    event_type, 0) + 1

            logger.info(f"   📈 Severity distribution: {severity_counts}")
            logger.info(f"   🎭 Event type distribution: {event_type_counts}")

            # Step 4: Store alerts in Firestore
            logger.info("💾 PHASE 4: STORING ALERTS")
            stored_count = await self._store_alerts(alerts)
            self.stats['alerts_stored'] = stored_count

            # Final summary
            logger.info("🎉 === MONITOR CYCLE COMPLETED ===")
            logger.info(
                f"   ✅ Signals collected: {self.stats['signals_collected']}")
            logger.info(
                f"   ✅ Alerts generated: {self.stats['alerts_generated']}")
            logger.info(f"   ✅ Alerts stored: {stored_count}")
            logger.info(
                f"   ⏱️  Execution time: {(datetime.utcnow() - self.start_time).total_seconds():.2f}s")

            if stored_count > 0:
                logger.info(f"🎯 VERIFICATION LINKS:")
                logger.info(
                    f"   Firestore: https://console.cloud.google.com/firestore/data/nyc_monitor_alerts")
                logger.info(
                    f"   Logs: https://console.cloud.google.com/run/jobs/details/{os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')}/atlas-monitor")

            # Store monitor run statistics
            run_stats = self._generate_stats_report()
            try:
                await self.storage.store_monitor_run(run_stats)
                logger.info("✅ Monitor run statistics stored successfully")
            except Exception as e:
                logger.error(f"❌ Failed to store monitor run statistics: {e}")

            return run_stats

        except Exception as e:
            error_msg = f"❌ Background monitor failed: {str(e)}"
            logger.error(error_msg)
            logger.error(f"   Exception type: {type(e).__name__}")
            self.stats['errors'].append(error_msg)

            # Store monitor run statistics even on failure
            run_stats = self._generate_stats_report()
            run_stats['status'] = 'failed'
            try:
                await self.storage.store_monitor_run(run_stats)
                logger.info(
                    "✅ Monitor run statistics stored (with failure status)")
            except Exception as storage_error:
                logger.error(
                    f"❌ Failed to store monitor run statistics: {storage_error}")

            return run_stats

    async def _collect_all_signals(self) -> Dict:
        """
        Collect raw signals from all available data sources

        Returns:
            Dictionary with signals organized by source
        """
        all_signals = {}
        total_count = 0

        for collector in self.collectors:
            try:
                logger.info(f"Collecting signals from {collector.source_name}")

                # Track start time for this collector
                collector_start_time = datetime.utcnow()

                signals = await collector.collect_signals()

                # Track end time and calculate duration
                collector_end_time = datetime.utcnow()
                collection_duration = (
                    collector_end_time - collector_start_time).total_seconds()

                if signals:
                    all_signals[collector.source_name] = signals
                    total_count += len(signals)
                    logger.info(
                        f"Collected {len(signals)} signals from {collector.source_name}")
                else:
                    logger.info(
                        f"No signals collected from {collector.source_name}")

                # Store detailed source statistics
                self.stats['source_stats'][collector.source_name] = {
                    'signals_collected': len(signals) if signals else 0,
                    'collection_duration_seconds': collection_duration,
                    'collection_start_time': collector_start_time.isoformat(),
                    'collection_end_time': collector_end_time.isoformat(),
                    'success': True,
                    'error': None
                }

            except Exception as e:
                error_msg = f"Error collecting from {collector.source_name}: {str(e)}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)

                # Store error statistics for this source
                self.stats['source_stats'][collector.source_name] = {
                    'signals_collected': 0,
                    'collection_duration_seconds': 0,
                    'collection_start_time': None,
                    'collection_end_time': None,
                    'success': False,
                    'error': str(e)
                }
                continue

        self.stats['signals_collected'] = total_count
        return all_signals

    async def _run_triage_analysis(self, raw_signals: Dict, recent_alerts: List[Dict] = None) -> Dict:
        """
        Run lightweight triage analysis on collected signals

        Args:
            raw_signals: Dictionary of signals organized by source
            recent_alerts: List of recent alerts for duplicate detection

        Returns:
            Triage analysis results with severity-scored alerts
        """
        try:
            logger.info(
                "Running triage analysis on collected signals with duplicate detection")

            # Add timestamp and recent alerts for analysis context
            signals_with_metadata = {
                **raw_signals,
                'timestamp': datetime.utcnow().isoformat(),
                'collection_window': '15_minutes',
                'recent_alerts': recent_alerts or []
            }

            # Run triage analysis with duplicate detection
            triage_results = await self.triage_agent.analyze_signals(signals_with_metadata)

            # Log triage summary
            summary = triage_results.get('summary', 'No summary available')
            logger.info(f"Triage summary: {summary}")

            # Log action categories
            action_required = triage_results.get('action_required', {})
            for category, items in action_required.items():
                if items:
                    logger.info(f"{category}: {len(items)} alerts")

            return triage_results

        except Exception as e:
            error_msg = f"Error in triage analysis: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            # Return empty results instead of fallback - no fake alerts
            return {
                'summary': 'Triage analysis failed due to exception',
                'alerts': [],
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'sources_analyzed': list(raw_signals.keys()) if raw_signals else [],
                'action_required': {
                    'urgent_investigation': [],
                    'user_investigation': [],
                    'monitor_only': [],
                    'normal_activity': []
                }
            }

    async def _store_alerts(self, alerts: List[Dict]) -> int:
        """
        Store alerts in Firestore

        Args:
            alerts: List of alert dictionaries from triage analysis

        Returns:
            Number of alerts successfully stored
        """
        logger.info(f"📦 STORING {len(alerts)} ALERTS IN FIRESTORE")
        logger.info(f"   Target Collection: nyc_monitor_alerts")
        logger.info(
            f"   Firestore Project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")

        stored_count = 0
        failed_count = 0

        for i, alert in enumerate(alerts, 1):
            try:
                logger.info(
                    f"📝 Storing alert {i}/{len(alerts)}: {alert.get('title', 'Unknown')}")

                # Generate a descriptive document ID based on the alert
                alert_id = self._generate_alert_document_id(alert)

                # Extract event date from alert title or use current date as fallback
                event_date = self._extract_event_date_from_alert(alert)

                # Use the new categorization system
                event_type_from_alert = alert.get('event_type', 'general')
                categorized_event_type = categorize_monitor_event(
                    event_type_from_alert,
                    alert.get('title', ''),
                    alert.get('description', '')
                )

                # Get alert type information for metadata
                alert_type_info = get_alert_type_info(categorized_event_type)

                # Enhance alert with additional metadata and frontend-compatible format
                enhanced_alert = {
                    # Frontend-expected fields (no transformation needed)
                    'id': alert_id,  # Use our generated ID
                    'title': alert.get('title', 'Untitled Alert'),
                    'description': alert.get('description', ''),

                    # Safely handle coordinates with None checks
                    'latitude': self._safe_float_conversion(alert.get('coordinates', {}).get('lat'), 40.7128),
                    'longitude': self._safe_float_conversion(alert.get('coordinates', {}).get('lng'), -74.0060),

                    # Store both numeric severity AND text priority
                    # Numeric 1-10 scale from triage agent
                    'severity': alert.get('severity', alert_type_info.default_severity),
                    # Text priority for frontend
                    'priority': self._map_severity_to_priority(alert.get('severity', alert_type_info.default_severity)),

                    'source': self._map_source(alert.get('source', 'reddit')),
                    'status': self._map_status(alert.get('status', 'pending')),
                    'timestamp': datetime.utcnow().isoformat(),
                    'neighborhood': self._extract_neighborhood(alert),
                    'borough': self._extract_borough(alert),

                    # Enhanced categorization fields
                    'event_type': categorized_event_type,  # Normalized event type
                    'category': alert_type_info.category.value,  # Alert category
                    'alert_type_name': alert_type_info.name,  # Human-readable name

                    # Additional metadata for backend use
                    'created_at': datetime.utcnow(),
                    'monitor_cycle': datetime.utcnow().strftime('%Y%m%d_%H%M'),
                    'expires_at': None,  # Will be set based on severity
                    'document_id': alert_id,  # Store the document ID for reference
                    'event_date': event_date,  # Extracted or inferred event date

                    # Enhanced queryability fields
                    'date_created': datetime.utcnow().strftime('%Y-%m-%d'),
                    'time_created': datetime.utcnow().strftime('%H:%M'),
                    'year': datetime.utcnow().year,
                    'month': datetime.utcnow().month,
                    'day': datetime.utcnow().day,
                    'hour': datetime.utcnow().hour,

                    # Event date queryability
                    'event_year': event_date.year if event_date else None,
                    'event_month': event_date.month if event_date else None,
                    'event_day': event_date.day if event_date else None,
                    'event_date_str': event_date.strftime('%Y-%m-%d') if event_date else None,

                    # Location queryability
                    'has_specific_location': bool(alert.get('specific_streets') or alert.get('venue_address')),
                    'street_count': len(alert.get('specific_streets', [])),
                    'has_coordinates': bool(alert.get('coordinates', {}).get('lat')),
                    'borough_primary': self._extract_borough(alert),

                    # Original alert data for reference
                    'original_alert_data': alert
                }

                # Use the custom alert_id as the document ID
                stored_alert_id = await self.storage.store_alert(enhanced_alert, document_id=alert_id)
                stored_count += 1
                logger.info(
                    f"✅ SUCCESS - Alert stored with ID: {stored_alert_id}")

            except Exception as e:
                failed_count += 1
                error_msg = f"❌ FAILED to store alert {i}: {alert.get('title', 'Unknown')} - {str(e)}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)
                continue

        # Summary logging
        logger.info(f"📊 STORAGE SUMMARY:")
        logger.info(f"   ✅ Stored: {stored_count}")
        logger.info(f"   ❌ Failed: {failed_count}")
        logger.info(f"   📍 Collection: nyc_monitor_alerts")

        if stored_count > 0:
            logger.info(f"🎯 VERIFICATION: Check Firestore console at:")
            logger.info(
                f"   https://console.cloud.google.com/firestore/data/nyc_monitor_alerts")

        return stored_count

    def _generate_alert_document_id(self, alert: Dict) -> str:
        """
        Generate a descriptive document ID for the alert based on date, event type, and location

        Format: YYYY-MM-DD_HHMI_[event_type]_[location_key]
        Example: 2025-06-01_1430_parade_5th_ave
        """
        try:
            # Use event date if available, otherwise current time
            event_date = self._extract_event_date_from_alert(alert)
            date_prefix = event_date.strftime('%Y-%m-%d')
            time_prefix = datetime.utcnow().strftime('%H%M')

            # Event type (cleaned) - ensure it's a string
            event_type_raw = alert.get('event_type', 'event')
            event_type = str(event_type_raw).lower().replace(' ', '_')

            # Location key - extract from venue_address, specific_streets, or area
            location_key = self._extract_location_key(alert)

            # Generate document ID
            document_id = f"{date_prefix}_{time_prefix}_{event_type}_{location_key}"

            return document_id

        except Exception as e:
            # Fallback to timestamp-based ID
            logger.warning(f"Error generating alert ID: {e}")
            event_type_fallback = str(alert.get('event_type', 'alert')).lower()
            return f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{event_type_fallback}"

    def _extract_location_key(self, alert: Dict) -> str:
        """Extract a short location key for the document ID"""
        try:
            # Try venue_address first
            venue = alert.get('venue_address', '')
            if venue:
                venue = str(venue)  # Ensure it's a string
                # Extract street name from address
                # "5th Avenue from 36th Street to 8th Street" -> "5th_ave"
                if 'avenue' in venue.lower():
                    key = venue.lower().split('avenue')[0].strip().replace(' ', '_').replace(
                        'th', '').replace('nd', '').replace('rd', '').replace('st', '')
                    return f"{key}_ave"[:20]
                elif 'street' in venue.lower():
                    key = venue.lower().split('street')[0].strip().replace(' ', '_').replace(
                        'th', '').replace('nd', '').replace('rd', '').replace('st', '')
                    return f"{key}_st"[:20]

            # Try specific_streets
            streets = alert.get('specific_streets', [])
            if streets and len(streets) > 0:
                street = str(streets[0]).lower().replace(' ', '_').replace(
                    'avenue', 'ave').replace('street', 'st')
                return street[:20]

            # Try area
            area = alert.get('area', '')
            if area:
                area = str(area)  # Ensure it's a string
                # "Midtown Manhattan - 5th Avenue corridor" -> "midtown_manhattan"
                area_clean = area.lower().split(' - ')[0].replace(' ', '_')
                return area_clean[:20]

            # Fallback
            return 'unknown_location'

        except Exception:
            return 'unknown_location'

    def _extract_event_date_from_alert(self, alert: Dict) -> datetime:
        """Extract event date from alert or use current date as fallback"""
        try:
            # Check if alert has an explicit event_date field (from triage agent)
            if alert.get('event_date'):
                if isinstance(alert['event_date'], datetime):
                    return alert['event_date']
                elif isinstance(alert['event_date'], str):
                    try:
                        # Handle YYYY-MM-DD format from triage agent
                        return datetime.strptime(alert['event_date'], '%Y-%m-%d')
                    except ValueError:
                        try:
                            # Handle ISO format as fallback
                            return datetime.fromisoformat(alert['event_date'].replace('Z', '+00:00'))
                        except ValueError:
                            pass

            # Fallback to current date if no event_date provided
            return datetime.utcnow()

        except Exception:
            return datetime.utcnow()

    def _map_severity_to_priority(self, severity) -> str:
        """Map alert severity to frontend priority"""
        # Handle numeric severity scores from triage agent (1-10 scale)
        if isinstance(severity, (int, float)):
            if severity >= 9:
                return 'critical'  # 9-10: Critical emergencies
            elif severity >= 7:
                return 'high'      # 7-8: High priority
            elif severity >= 5:
                return 'medium'    # 5-6: Medium priority
            elif severity >= 3:
                return 'low'       # 3-4: Low priority
            else:
                return 'low'       # 1-2: Normal activity (still low priority)

        # Handle string severity values (fallback for other sources)
        severity_str = str(severity).lower() if severity else 'medium'
        priority_mapping = {
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low',
            'urgent': 'critical',
            'moderate': 'medium',
            'minor': 'low'
        }
        return priority_mapping.get(severity_str, 'medium')

    def _map_source(self, source: str) -> str:
        """Map alert source to frontend source"""
        source = str(source).lower() if source else 'reddit'
        source_mapping = {
            'reddit': 'reddit',
            '311': '311',
            'twitter': 'twitter',
            'nyc311': '311',
            'social': 'twitter'
        }
        return source_mapping.get(source, 'reddit')

    def _map_status(self, status: str) -> str:
        """Map alert status to frontend status"""
        status = str(status).lower() if status else 'new'
        status_mapping = {
            'new': 'new',
            'investigating': 'investigating',
            'resolved': 'resolved',
            'active': 'new',
            'closed': 'resolved',
            'open': 'new',
            'pending': 'new'
        }
        return status_mapping.get(status, 'new')

    def _extract_neighborhood(self, alert: Dict) -> str:
        """Extract neighborhood from alert data"""
        # Try multiple sources for neighborhood info
        if alert.get('area'):
            area = alert['area']
            if ',' in area:
                return area.split(',')[0].strip()
            elif ' - ' in area:
                return area.split(' - ')[0].strip()
            else:
                return area
        elif alert.get('venue_address'):
            return alert['venue_address']
        elif alert.get('specific_streets') and len(alert['specific_streets']) > 0:
            return alert['specific_streets'][0]
        else:
            return 'Unknown'

    def _extract_borough(self, alert: Dict) -> str:
        """Extract borough from alert data"""
        # Try multiple sources for borough info
        if alert.get('area'):
            area = alert['area']
            if ',' in area and len(area.split(',')) > 1:
                return area.split(',')[1].strip()
            elif ' - ' in area and len(area.split(' - ')) > 1:
                borough_part = area.split(' - ')[1]
                # Extract just the borough name if it contains additional info
                for borough in ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']:
                    if borough in borough_part:
                        return borough
                return borough_part.strip()

        # Check for direct borough field or primary_borough
        if alert.get('borough'):
            return alert['borough']
        elif alert.get('primary_borough'):
            return alert['primary_borough']

        # Try to extract from coordinates or location data
        coordinates = alert.get('coordinates', {})
        if coordinates.get('borough'):
            return coordinates['borough']

        return 'Unknown'

    def _safe_float_conversion(self, value, default):
        """Safely convert value to float or return default if conversion fails"""
        try:
            if value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    def _generate_stats_report(self) -> Dict:
        """Generate comprehensive execution statistics report for monitor_runs collection"""
        execution_time = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            # Execution metadata
            'run_id': f"{self.start_time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}",
            'execution_time_seconds': execution_time,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'status': 'completed',  # Will be overridden to 'failed' in exception handler

            # High-level statistics
            'collectors_used': self.stats['collectors_used'],
            'total_signals_collected': self.stats['signals_collected'],
            'alerts_generated': self.stats['alerts_generated'],
            'alerts_stored': self.stats['alerts_stored'],
            'success': len(self.stats['errors']) == 0,
            'error_count': len(self.stats['errors']),
            'errors': self.stats['errors'],

            # Detailed source statistics
            'source_stats': self.stats['source_stats'],
            'sources_successful': len([s for s in self.stats['source_stats'].values() if s.get('success', False)]),
            'sources_failed': len([s for s in self.stats['source_stats'].values() if not s.get('success', True)]),

            # Environment information
            'environment': {
                'google_cloud_project': os.getenv('GOOGLE_CLOUD_PROJECT'),
                'google_cloud_location': os.getenv('GOOGLE_CLOUD_LOCATION'),
                'monitor_system_version': '1.0',
                'hostname': os.getenv('HOSTNAME', 'unknown'),
                'container_id': os.getenv('CONTAINER_ID', 'unknown')[:12] if os.getenv('CONTAINER_ID') else 'unknown'
            },

            # Performance metrics
            'performance': {
                'signals_per_second': self.stats['signals_collected'] / execution_time if execution_time > 0 else 0,
                'alerts_per_signal_ratio': self.stats['alerts_generated'] / self.stats['signals_collected'] if self.stats['signals_collected'] > 0 else 0,
                'storage_success_rate': self.stats['alerts_stored'] / self.stats['alerts_generated'] if self.stats['alerts_generated'] > 0 else 1.0
            }
        }

# Signal handlers for graceful shutdown


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


async def main():
    """Main entry point for the background monitor job"""
    logger.info("=== NYC Background Monitor Starting ===")

    try:
        # Create and run the monitor job
        job = MonitorJob()
        stats = await job.background_monitor()

        # Log final statistics
        logger.info("=== Background Monitor Complete ===")
        logger.info(
            f"Execution time: {stats['execution_time_seconds']:.2f} seconds")
        logger.info(f"Signals collected: {stats['total_signals_collected']}")
        logger.info(f"Alerts generated: {stats['alerts_generated']}")
        logger.info(f"Alerts stored: {stats['alerts_stored']}")

        if stats['errors']:
            logger.warning(f"Errors encountered: {len(stats['errors'])}")
            for error in stats['errors']:
                logger.warning(f"  - {error}")

        # Exit with appropriate code
        exit_code = 0 if stats['success'] else 1
        logger.info(f"Job completed with exit code: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.error(f"Fatal error in background monitor: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the background monitor
    asyncio.run(main())
