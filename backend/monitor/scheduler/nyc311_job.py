"""
NYC 311 Daily Collector Job.
Collects 311 service requests daily and stores them directly in Firestore.
Uses triage agent for severity scoring (consistent with monitor alerts).
"""
from monitor.storage.firestore_manager import FirestoreManager
from monitor.collectors.nyc_311_collector import NYC311Collector
from monitor.agents.triage_agent import TriageAgent
import os
import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Set
import json

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            '/tmp/nyc311.log') if os.path.exists('/tmp') else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NYC311Job:
    """Daily NYC 311 collector job with direct storage and duplicate checking"""

    def __init__(self):
        """Initialize the NYC 311 job with collector, triage agent, and storage"""
        self.start_time = datetime.utcnow()

        # Initialize components
        try:
            # Initialize NYC 311 collector
            self.collector = NYC311Collector()
            logger.info("✅ NYC 311 collector initialized successfully")

            # Initialize triage agent for severity scoring
            self.triage_agent = TriageAgent()
            logger.info("✅ Triage agent initialized successfully")

            # Initialize Firestore storage
            self.storage = FirestoreManager()
            logger.info("✅ Firestore manager initialized successfully")

            # Collection name for 311 signals
            self.collection_name = 'nyc_311_signals'

            # Job statistics
            self.stats = {
                'signals_collected': 0,
                'signals_stored': 0,
                'duplicates_found': 0,
                'triage_analysis_time': 0,
                'errors': [],
                'collection_duration': 0,
                'storage_duration': 0,
                'complaint_type_breakdown': {},
                'borough_breakdown': {},
                'agency_breakdown': {},
                'severity_distribution': {}
            }

        except Exception as e:
            logger.error(f"Failed to initialize NYC 311 job: {str(e)}")
            raise

    async def run_daily_collection(self) -> Dict:
        """
        Run the daily NYC 311 collection cycle:
        1. Collect signals from NYC 311 API
        2. Check for duplicates against existing data  
        3. Store new signals directly in Firestore

        Returns:
            Dictionary with job execution statistics
        """
        logger.info("🚀 === STARTING NYC 311 DAILY COLLECTION ===")
        logger.info(f"   Timestamp: {datetime.utcnow().isoformat()}")
        logger.info(f"   Project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
        logger.info(f"   Target Collection: {self.collection_name}")

        try:
            # Step 1: Collect signals from NYC 311 API
            logger.info("📡 PHASE 1: COLLECTING 311 SIGNALS")
            collection_start = datetime.utcnow()

            signals = await self.collector.collect_signals()

            collection_end = datetime.utcnow()
            self.stats['collection_duration'] = (
                collection_end - collection_start).total_seconds()
            self.stats['signals_collected'] = len(signals)

            if not signals:
                logger.warning("⚠️  No 311 signals collected")
                logger.info("🔍 Check NYC 311 API status and configuration")
                return self._generate_stats_report()

            logger.info(f"✅ Collected {len(signals)} 311 signals")

            # Analyze signal composition
            self._analyze_signal_composition(signals)

            # Step 2: Query existing signals for duplicate detection
            logger.info("🔍 PHASE 2: DUPLICATE DETECTION")
            existing_unique_keys = await self._get_existing_unique_keys()
            logger.info(
                f"📋 Found {len(existing_unique_keys)} existing 311 records for duplicate checking")

            # Step 3: Filter out duplicates using unique_key
            logger.info("🔄 PHASE 3: FILTERING DUPLICATES")
            new_signals = self._filter_duplicates(
                signals, existing_unique_keys)

            duplicates_count = len(signals) - len(new_signals)
            self.stats['duplicates_found'] = duplicates_count

            logger.info(f"🔄 Duplicate analysis complete:")
            logger.info(f"   Total signals: {len(signals)}")
            logger.info(f"   Duplicates found: {duplicates_count}")
            logger.info(f"   New signals to store: {len(new_signals)}")

            if not new_signals:
                logger.info(
                    "ℹ️  No new 311 signals to store (all were duplicates)")
                return self._generate_stats_report()

            # Step 4: Run triage analysis for severity scoring
            logger.info("🧠 PHASE 4: TRIAGE ANALYSIS FOR SEVERITY SCORING")
            triage_start = datetime.utcnow()

            scored_signals = await self._run_triage_analysis(new_signals)

            triage_end = datetime.utcnow()
            self.stats['triage_analysis_time'] = (
                triage_end - triage_start).total_seconds()

            if not scored_signals:
                logger.warning(
                    "⚠️  Triage analysis failed - using fallback severity scores")
                scored_signals = self._apply_fallback_severity(new_signals)

            # Step 5: Store new signals in Firestore
            logger.info("💾 PHASE 5: STORING NEW SIGNALS")
            storage_start = datetime.utcnow()

            stored_count = await self._store_signals(scored_signals)

            storage_end = datetime.utcnow()
            self.stats['storage_duration'] = (
                storage_end - storage_start).total_seconds()
            self.stats['signals_stored'] = stored_count

            # Final summary
            logger.info("🎉 === NYC 311 COLLECTION COMPLETED ===")
            logger.info(
                f"   ✅ Signals collected: {self.stats['signals_collected']}")
            logger.info(
                f"   🔄 Duplicates filtered: {self.stats['duplicates_found']}")
            logger.info(
                f"   🧠 Triage analysis time: {self.stats['triage_analysis_time']:.2f}s")
            logger.info(f"   ✅ New signals stored: {stored_count}")
            logger.info(
                f"   ⏱️  Total execution time: {(datetime.utcnow() - self.start_time).total_seconds():.2f}s")
            logger.info(
                f"   📊 Collection efficiency: {(stored_count/len(signals)*100):.1f}% new data")
            logger.info(
                f"   🎯 Severity distribution: {self.stats.get('severity_distribution', {})}")

            if stored_count > 0:
                logger.info(f"🎯 VERIFICATION LINKS:")
                logger.info(
                    f"   Firestore: https://console.cloud.google.com/firestore/data/{self.collection_name}")

            # Store job run statistics
            run_stats = self._generate_stats_report()
            try:
                await self._store_job_stats(run_stats)
                logger.info("✅ Job run statistics stored successfully")
            except Exception as e:
                logger.error(f"❌ Failed to store job run statistics: {e}")

            return run_stats

        except Exception as e:
            error_msg = f"❌ NYC 311 collection failed: {str(e)}"
            logger.error(error_msg)
            logger.error(f"   Exception type: {type(e).__name__}")
            self.stats['errors'].append(error_msg)

            # Store job run statistics even on failure
            run_stats = self._generate_stats_report()
            run_stats['status'] = 'failed'
            try:
                await self._store_job_stats(run_stats)
                logger.info(
                    "✅ Job run statistics stored (with failure status)")
            except Exception as storage_error:
                logger.error(
                    f"❌ Failed to store job run statistics: {storage_error}")

            return run_stats

    def _analyze_signal_composition(self, signals: List[Dict]):
        """Analyze the composition of collected signals for reporting"""

        for signal in signals:
            metadata = signal.get('metadata', {})

            # Track complaint types
            complaint_type = metadata.get('complaint_type', 'Unknown')
            self.stats['complaint_type_breakdown'][complaint_type] = \
                self.stats['complaint_type_breakdown'].get(
                    complaint_type, 0) + 1

            # Track boroughs
            borough = metadata.get('borough', 'Unknown')
            self.stats['borough_breakdown'][borough] = \
                self.stats['borough_breakdown'].get(borough, 0) + 1

            # Track agencies
            agency = metadata.get('agency_name', 'Unknown')
            self.stats['agency_breakdown'][agency] = \
                self.stats['agency_breakdown'].get(agency, 0) + 1

        # Log top complaint types and boroughs
        top_complaints = sorted(self.stats['complaint_type_breakdown'].items(),
                                key=lambda x: x[1], reverse=True)[:5]
        top_boroughs = sorted(self.stats['borough_breakdown'].items(),
                              key=lambda x: x[1], reverse=True)[:5]

        logger.info(f"📊 Signal composition analysis:")
        logger.info(f"   Top complaint types: {dict(top_complaints)}")
        logger.info(f"   Borough distribution: {dict(top_boroughs)}")
        logger.info(
            "   Severity distribution will be calculated after triage analysis")

    async def _get_existing_unique_keys(self, days_back: int = 7) -> Set[str]:
        """
        Get existing unique_key values from Firestore for duplicate detection

        Args:
            days_back: Number of days to look back for existing keys

        Returns:
            Set of existing unique_key values
        """
        try:
            # Query recent documents to build duplicate detection set
            cutoff_time = datetime.utcnow() - timedelta(days=days_back)

            # Use direct Firestore query for efficiency
            query = (self.storage.db.collection(self.collection_name)
                     .where('created_at', '>=', cutoff_time)
                     .select(['unique_key']))  # Only fetch unique_key field for efficiency

            docs = query.stream()
            existing_keys = set()

            for doc in docs:
                data = doc.to_dict()
                unique_key = data.get('unique_key')
                if unique_key:
                    existing_keys.add(unique_key)

            logger.info(
                f"✅ Loaded {len(existing_keys)} existing unique keys for duplicate detection")
            return existing_keys

        except Exception as e:
            logger.error(f"❌ Error getting existing unique keys: {e}")
            # Return empty set to continue with processing (will skip duplicate detection)
            return set()

    def _filter_duplicates(self, signals: List[Dict], existing_keys: Set[str]) -> List[Dict]:
        """
        Filter out duplicate signals based on unique_key

        Args:
            signals: List of collected signals
            existing_keys: Set of existing unique_key values

        Returns:
            List of new (non-duplicate) signals
        """
        if not existing_keys:
            logger.warning(
                "⚠️  No existing keys loaded - skipping duplicate detection")
            return signals

        new_signals = []

        for signal in signals:
            unique_key = signal.get('metadata', {}).get('unique_key')

            if not unique_key:
                # If no unique_key, treat as new (shouldn't happen with 311 data)
                logger.warning(
                    "⚠️  Signal missing unique_key - treating as new")
                new_signals.append(signal)
                continue

            if unique_key not in existing_keys:
                new_signals.append(signal)
            # else: duplicate found, skip this signal

        return new_signals

    async def _store_signals(self, signals: List[Dict]) -> int:
        """
        Store NYC 311 signals directly in Firestore with AI-calculated severity scores

        Args:
            signals: List of 311 signals with severity scores from triage analysis

        Returns:
            Number of signals successfully stored
        """
        logger.info(f"📦 STORING {len(signals)} NEW 311 SIGNALS")
        logger.info(f"   Target Collection: {self.collection_name}")

        stored_count = 0
        failed_count = 0

        for i, signal in enumerate(signals, 1):
            try:
                # Extract unique_key for document ID
                unique_key = signal.get('metadata', {}).get('unique_key')
                if not unique_key:
                    unique_key = f"311_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{i}"
                    logger.warning(f"⚠️  Generated fallback ID: {unique_key}")

                # Use pre-calculated severity from triage analysis
                severity_score = signal.get('severity', 3)
                priority = signal.get(
                    'priority') or self._map_severity_to_priority(severity_score)
                triage_method = signal.get('triage_method', 'unknown')

                # Prepare document data optimized for queries
                doc_data = {
                    # Core 311 data
                    'unique_key': unique_key,
                    'complaint_type': signal.get('metadata', {}).get('complaint_type', ''),
                    'descriptor': signal.get('metadata', {}).get('descriptor', ''),
                    'borough': signal.get('metadata', {}).get('borough', ''),
                    'agency': signal.get('metadata', {}).get('agency', ''),
                    'agency_name': signal.get('metadata', {}).get('agency_name', ''),
                    'status': signal.get('metadata', {}).get('status', ''),
                    'incident_zip': signal.get('metadata', {}).get('incident_zip', ''),

                    # Location data
                    'latitude': signal.get('metadata', {}).get('latitude'),
                    'longitude': signal.get('metadata', {}).get('longitude'),
                    'has_coordinates': signal.get('metadata', {}).get('has_coordinates', False),

                    # Atlas metadata
                    'signal_category': signal.get('metadata', {}).get('signal_category', ''),
                    'is_emergency': signal.get('metadata', {}).get('is_emergency', False),
                    'is_event': signal.get('metadata', {}).get('is_event', False),

                    # AI Triage results (consistent with monitor alerts)
                    'severity': severity_score,
                    'priority': priority,
                    'triage_method': triage_method,

                    # Timestamps
                    'created_at': datetime.utcnow(),
                    'signal_timestamp': signal.get('timestamp'),

                    # Queryable date fields
                    'date_created': datetime.utcnow().strftime('%Y-%m-%d'),
                    'year': datetime.utcnow().year,
                    'month': datetime.utcnow().month,
                    'day': datetime.utcnow().day,

                    # Full signal data for reference
                    'full_signal_data': signal
                }

                # Store with unique_key as document ID for guaranteed uniqueness
                doc_ref = self.storage.db.collection(
                    self.collection_name).document(unique_key)
                doc_ref.set(doc_data)

                stored_count += 1

                if i % 100 == 0:  # Log progress every 100 items
                    logger.info(
                        f"📝 Progress: {i}/{len(signals)} signals stored")

            except Exception as e:
                failed_count += 1
                error_msg = f"❌ Failed to store signal {i}: {str(e)}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)
                continue

        # Summary
        logger.info(f"📊 STORAGE SUMMARY:")
        logger.info(f"   ✅ Stored: {stored_count}")
        logger.info(f"   ❌ Failed: {failed_count}")
        logger.info(f"   📍 Collection: {self.collection_name}")

        return stored_count

    def _map_severity_to_priority(self, severity: int) -> str:
        """
        Map numeric severity to priority string (consistent with monitor alerts)
        """
        if severity >= 9:
            return 'critical'  # 9-10: Critical emergencies
        elif severity >= 7:
            return 'high'      # 7-8: High priority
        elif severity >= 5:
            return 'medium'    # 5-6: Medium priority
        elif severity >= 3:
            return 'low'       # 3-4: Low priority
        else:
            return 'low'       # 1-2: Normal activity

    async def _store_job_stats(self, stats: Dict):
        """Store job execution statistics"""
        try:
            stats_doc = {
                **stats,
                'created_at': datetime.utcnow(),
                'job_type': 'nyc311_daily_collection'
            }

            doc_ref = self.storage.db.collection('nyc311_job_runs').document()
            doc_ref.set(stats_doc)

        except Exception as e:
            logger.error(f"Error storing job stats: {e}")

    def _generate_stats_report(self) -> Dict:
        """Generate comprehensive execution statistics report"""
        execution_time = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            # Execution metadata
            'run_id': f"nyc311_{self.start_time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}",
            'execution_time_seconds': execution_time,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'status': 'completed',

            # Collection statistics
            'signals_collected': self.stats['signals_collected'],
            'signals_stored': self.stats['signals_stored'],
            'duplicates_found': self.stats['duplicates_found'],
            'success': len(self.stats['errors']) == 0,
            'error_count': len(self.stats['errors']),
            'errors': self.stats['errors'],

            # Performance metrics
            'collection_duration_seconds': self.stats['collection_duration'],
            'storage_duration_seconds': self.stats['storage_duration'],
            'triage_analysis_duration_seconds': self.stats['triage_analysis_time'],
            'efficiency_percent': (self.stats['signals_stored'] / self.stats['signals_collected'] * 100) if self.stats['signals_collected'] > 0 else 0,

            # Data composition
            'complaint_type_breakdown': self.stats['complaint_type_breakdown'],
            'borough_breakdown': self.stats['borough_breakdown'],
            'agency_breakdown': self.stats['agency_breakdown'],
            'severity_distribution': self.stats['severity_distribution'],

            # Environment
            'environment': {
                'google_cloud_project': os.getenv('GOOGLE_CLOUD_PROJECT'),
                'google_cloud_location': os.getenv('GOOGLE_CLOUD_LOCATION'),
                'hostname': os.getenv('HOSTNAME', 'unknown')
            }
        }

    async def _run_triage_analysis(self, signals: List[Dict]) -> List[Dict]:
        """
        Run triage analysis on 311 signals to assign severity scores

        Args:
            signals: List of 311 signals to analyze

        Returns:
            List of signals with severity scores added
        """
        try:
            logger.info(
                f"🧠 Running AI triage analysis on {len(signals)} 311 signals")

            # Format signals for triage agent (similar to monitor job)
            signals_for_triage = {
                'nyc_311': signals,
                'timestamp': datetime.utcnow().isoformat(),
                'collection_window': 'daily_311',
                'signal_count': len(signals)
            }

            # Run triage analysis
            triage_results = await self.triage_agent.analyze_signals(signals_for_triage)

            if not triage_results or not triage_results.get('alerts'):
                logger.warning(
                    "⚠️  Triage agent returned no alerts for 311 signals")
                return []

            # Map triage results back to original signals
            scored_signals = self._map_triage_results_to_signals(
                signals, triage_results)

            # Log triage summary
            summary = triage_results.get('summary', 'No summary available')
            logger.info(f"✅ Triage analysis complete: {summary}")

            # Log severity distribution
            severity_counts = {}
            for signal in scored_signals:
                severity = signal.get('severity', 3)
                priority = self._map_severity_to_priority(severity)
                severity_counts[priority] = severity_counts.get(
                    priority, 0) + 1

            logger.info(f"📊 Severity distribution: {severity_counts}")
            self.stats['severity_distribution'] = severity_counts

            return scored_signals

        except Exception as e:
            logger.error(f"❌ Error in 311 triage analysis: {str(e)}")
            return []

    def _map_triage_results_to_signals(self, original_signals: List[Dict], triage_results: Dict) -> List[Dict]:
        """
        Map triage analysis results back to original 311 signals
        Enhanced mapping to better utilize AI severity assessment

        Args:
            original_signals: Original 311 signals
            triage_results: Results from triage agent

        Returns:
            Signals with AI-determined severity scores added
        """
        try:
            alerts = triage_results.get('alerts', [])
            scored_signals = []

            logger.info(
                f"🔍 Mapping {len(alerts)} AI alerts to {len(original_signals)} 311 signals")

            # If we have AI alerts, use them as the basis for severity scoring
            if alerts:
                # Create signals based on AI analysis
                for alert in alerts:
                    # Find the best matching original signal for this AI alert
                    best_match = None
                    best_score = 0

                    alert_keywords = set((alert.get('description', '') + ' ' +
                                          ' '.join(alert.get('keywords', []))).lower().split())

                    for signal in original_signals:
                        metadata = signal.get('metadata', {})
                        signal_text = f"{metadata.get('complaint_type', '')} {metadata.get('descriptor', '')}".lower(
                        )
                        signal_keywords = set(signal_text.split())

                        # Calculate similarity score
                        common_keywords = alert_keywords.intersection(
                            signal_keywords)
                        if common_keywords:
                            score = len(common_keywords) / \
                                max(len(alert_keywords), len(signal_keywords))
                            if score > best_score:
                                best_score = score
                                best_match = signal

                    if best_match:
                        # Create enhanced signal with AI severity
                        signal_copy = best_match.copy()
                        signal_copy['severity'] = alert.get(
                            'severity', 5)  # Use AI severity
                        signal_copy['priority'] = self._map_severity_to_priority(
                            alert.get('severity', 5))
                        signal_copy['triage_method'] = 'ai_triage'
                        signal_copy['ai_alert_match'] = alert.get(
                            'title', 'Unknown')
                        signal_copy['ai_confidence'] = best_score

                        scored_signals.append(signal_copy)
                        # Remove from unmatched list
                        original_signals.remove(best_match)

            # For any remaining unmatched signals, apply simple defaults
            for signal in original_signals:
                metadata = signal.get('metadata', {})
                is_emergency = metadata.get('is_emergency', False)

                # Use metadata hints for unmatched signals
                severity = 8 if is_emergency else 4  # Emergency or medium default

                signal_copy = signal.copy()
                signal_copy['severity'] = severity
                signal_copy['priority'] = self._map_severity_to_priority(
                    severity)
                signal_copy['triage_method'] = 'metadata_based'
                signal_copy['ai_alert_match'] = None
                signal_copy['ai_confidence'] = 0.0

                scored_signals.append(signal_copy)

            # Log severity distribution from AI analysis
            severity_counts = {}
            for signal in scored_signals:
                priority = signal.get('priority', 'unknown')
                severity_counts[priority] = severity_counts.get(
                    priority, 0) + 1

            logger.info(f"✅ AI-based severity mapping complete:")
            logger.info(f"   Matched to AI alerts: {len(alerts)}")
            logger.info(f"   Metadata-based defaults: {len(original_signals)}")
            logger.info(f"   Severity distribution: {severity_counts}")

            self.stats['severity_distribution'] = severity_counts
            return scored_signals

        except Exception as e:
            logger.error(f"❌ Error mapping AI triage results: {str(e)}")
            # Fallback to simple default scoring
            return self._apply_simple_defaults(original_signals)

    def _apply_simple_defaults(self, signals: List[Dict]) -> List[Dict]:
        """Apply simple default severity when AI mapping fails"""
        scored_signals = []
        for signal in signals:
            metadata = signal.get('metadata', {})
            is_emergency = metadata.get('is_emergency', False)

            severity = 8 if is_emergency else 3
            signal_copy = signal.copy()
            signal_copy['severity'] = severity
            signal_copy['priority'] = self._map_severity_to_priority(severity)
            signal_copy['triage_method'] = 'error_fallback'

            scored_signals.append(signal_copy)

        return scored_signals

    def _apply_fallback_severity(self, signals: List[Dict]) -> List[Dict]:
        """
        Apply simple fallback severity scoring when AI triage fails
        Uses simple default values instead of complex rules

        Args:
            signals: List of 311 signals

        Returns:
            Signals with fallback severity scores
        """
        logger.info(
            "🔄 Applying simple fallback severity scoring (AI triage failed)")

        scored_signals = []
        severity_counts = {}

        for signal in signals:
            # Simple fallback: use metadata hints if available, otherwise default to 3
            metadata = signal.get('metadata', {})
            is_emergency = metadata.get('is_emergency', False)

            if is_emergency:
                severity = 8  # High priority for emergencies
            else:
                severity = 3  # Default low priority for everything else

            priority = self._map_severity_to_priority(severity)

            signal_copy = signal.copy()
            signal_copy['severity'] = severity
            signal_copy['priority'] = priority
            signal_copy['triage_method'] = 'simple_fallback'

            scored_signals.append(signal_copy)
            severity_counts[priority] = severity_counts.get(priority, 0) + 1

        logger.info(
            f"📊 Simple fallback severity distribution: {severity_counts}")
        logger.info(
            "ℹ️  Note: AI triage agent should be the primary severity scoring method")
        self.stats['severity_distribution'] = severity_counts

        return scored_signals


# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


async def main():
    """Main entry point for the NYC 311 daily job"""
    logger.info("=== NYC 311 Daily Collection Starting ===")

    try:
        # Create and run the NYC 311 job
        job = NYC311Job()
        stats = await job.run_daily_collection()

        # Log final statistics
        logger.info("=== NYC 311 Daily Collection Complete ===")
        logger.info(
            f"Execution time: {stats['execution_time_seconds']:.2f} seconds")
        logger.info(f"Signals collected: {stats['signals_collected']}")
        logger.info(f"Duplicates found: {stats['duplicates_found']}")
        logger.info(f"New signals stored: {stats['signals_stored']}")
        logger.info(f"Efficiency: {stats['efficiency_percent']:.1f}% new data")

        if stats['errors']:
            logger.warning(f"Errors encountered: {len(stats['errors'])}")
            for error in stats['errors']:
                logger.warning(f"  - {error}")

        # Exit with appropriate code
        exit_code = 0 if stats['success'] else 1
        logger.info(f"Job completed with exit code: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.error(f"Fatal error in NYC 311 collection: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the NYC 311 daily collection
    asyncio.run(main())
