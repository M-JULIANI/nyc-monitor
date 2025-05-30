"""
Main Monitor Job for NYC Background Monitor System.
Implements the background_monitor() flow: collect signals → triage analysis → store alerts.
Designed to run every 15 minutes as a Cloud Run Job.
"""
from storage.firestore_manager import FirestoreManager
from agents.triage_agent import TriageAgent
from collectors.reddit_collector import RedditCollector
import os
import asyncio
import logging
from datetime import datetime
from typing import List, Dict
import sys
import signal

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
                logger.info("Reddit collector initialized successfully")
            except ValueError as e:
                logger.warning(f"Reddit collector not initialized: {str(e)}")

            # TODO: Add more collectors here (traffic, crime, 311, etc.)

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
                'errors': []
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
        logger.info("=== Starting background monitor cycle ===")

        try:
            # Step 1: Collect raw signals from all sources
            raw_signals = await self._collect_all_signals()

            if not raw_signals:
                logger.info("No signals collected from any sources")
                return self._generate_stats_report()

            logger.info(f"Collected signals from {len(raw_signals)} sources")

            # Step 2: Run triage analysis on collected signals
            triage_results = await self._run_triage_analysis(raw_signals)

            if not triage_results or not triage_results.get('alerts'):
                logger.info("No alerts generated from triage analysis")
                return self._generate_stats_report()

            alerts = triage_results['alerts']
            self.stats['alerts_generated'] = len(alerts)
            logger.info(f"Triage analysis generated {len(alerts)} alerts")

            # Step 3: Store alerts in Firestore
            stored_count = await self._store_alerts(alerts)
            self.stats['alerts_stored'] = stored_count

            logger.info(
                f"Background monitor cycle completed. Stored {stored_count} alerts.")
            return self._generate_stats_report()

        except Exception as e:
            error_msg = f"Background monitor failed: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return self._generate_stats_report()

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

                signals = await collector.collect_signals()
                if signals:
                    all_signals[collector.source_name] = signals
                    total_count += len(signals)
                    logger.info(
                        f"Collected {len(signals)} signals from {collector.source_name}")
                else:
                    logger.info(
                        f"No signals collected from {collector.source_name}")

            except Exception as e:
                error_msg = f"Error collecting from {collector.source_name}: {str(e)}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)
                continue

        self.stats['signals_collected'] = total_count
        return all_signals

    async def _run_triage_analysis(self, raw_signals: Dict) -> Dict:
        """
        Run lightweight triage analysis on collected signals

        Args:
            raw_signals: Dictionary of signals organized by source

        Returns:
            Triage analysis results with severity-scored alerts
        """
        try:
            logger.info("Running triage analysis on collected signals")

            # Add timestamp for analysis context
            signals_with_metadata = {
                **raw_signals,
                'timestamp': datetime.utcnow().isoformat(),
                'collection_window': '15_minutes'
            }

            # Run triage analysis
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
            return {}

    async def _store_alerts(self, alerts: List[Dict]) -> int:
        """
        Store alerts in Firestore

        Args:
            alerts: List of alert dictionaries from triage analysis

        Returns:
            Number of alerts successfully stored
        """
        stored_count = 0

        for alert in alerts:
            try:
                # Enhance alert with additional metadata
                enhanced_alert = {
                    **alert,
                    'created_at': datetime.utcnow(),
                    'status': 'pending',
                    'monitor_cycle': datetime.utcnow().strftime('%Y%m%d_%H%M'),
                    'expires_at': None  # Will be set based on severity
                }

                alert_id = await self.storage.store_alert(enhanced_alert)
                stored_count += 1
                logger.debug(
                    f"Stored alert {alert_id}: {alert.get('title', 'Unknown')}")

            except Exception as e:
                error_msg = f"Error storing alert {alert.get('title', 'Unknown')}: {str(e)}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)
                continue

        return stored_count

    def _generate_stats_report(self) -> Dict:
        """Generate execution statistics report"""
        execution_time = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            'execution_time_seconds': execution_time,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'collectors_used': self.stats['collectors_used'],
            'signals_collected': self.stats['signals_collected'],
            'alerts_generated': self.stats['alerts_generated'],
            'alerts_stored': self.stats['alerts_stored'],
            'errors': self.stats['errors'],
            'success': len(self.stats['errors']) == 0
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
        logger.info(f"Signals collected: {stats['signals_collected']}")
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
