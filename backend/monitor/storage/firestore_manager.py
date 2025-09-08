"""
Firestore manager for storing and retrieving monitor alerts.
Handles NYC-focused alerts with structured data including topic, confidence scores, and metadata.
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from google.cloud import firestore
from google.cloud.firestore import Query
import logging

logger = logging.getLogger(__name__)


class FirestoreManager:
    """Manages monitor alerts storage in Firestore"""

    def __init__(self, project_id: Optional[str] = None):
        """Initialize Firestore client"""
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.db = firestore.Client(project=self.project_id)
        self.alerts_collection = 'nyc_monitor_alerts'
        self.trends_collection = 'nyc_trending_topics'
        self.monitor_runs_collection = 'monitor_runs'

    async def store_alert(self, alert: Dict, document_id: Optional[str] = None) -> str:
        """
        Store a monitor alert in Firestore

        Args:
            alert: Dictionary containing alert data from triage agent
            document_id: Optional custom document ID to use instead of auto-generated

        Returns:
            Document ID of stored alert
        """
        try:
            # Extract event date from alert title if it follows YYYY-MM-DD format
            event_date = self._extract_event_date(alert)

            # Convert triage agent format to Firestore format
            alert_data = {
                # Core alert information
                'title': alert.get('title', 'Unknown Alert'),
                'description': alert.get('description', ''),
                'alert_id': alert.get('id', ''),
                'area': alert.get('area', 'Unknown'),
                'severity': alert.get('severity', 0),
                'category': alert.get('category', 'general'),
                'event_type': alert.get('event_type', 'general'),
                'keywords': alert.get('keywords', []),

                # Date and time information
                'event_date': event_date,  # NEW: Actual event date
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),

                # Location information
                'coordinates': alert.get('coordinates', {}),
                'venue_address': alert.get('venue_address', ''),
                'specific_streets': alert.get('specific_streets', []),
                'cross_streets': alert.get('cross_streets', []),
                'transportation_impact': alert.get('transportation_impact', ''),

                # Event details
                'estimated_attendance': alert.get('estimated_attendance', ''),
                'crowd_impact': alert.get('crowd_impact', 'unknown'),

                # Sources and metadata
                'signals': alert.get('signals', []),
                'source': ', '.join(alert.get('signals', ['unknown'])),
                'url': alert.get('url', ''),

                # System metadata
                'location': 'NYC',
                'status': 'active',
                'monitor_system_version': '1.0',

                # Legacy compatibility (for existing queries)
                'topic': alert.get('title', 'Unknown Alert'),
                'alert_type': alert.get('category', 'general'),

                # Preserve original triage data for debugging
                'original_alert': alert
            }

            # Store in Firestore with custom document ID if provided
            if document_id:
                doc_ref = self.db.collection(
                    self.alerts_collection).document(document_id)
            elif alert.get('id'):
                doc_ref = self.db.collection(
                    self.alerts_collection).document(alert['id'])
            else:
                doc_ref = self.db.collection(self.alerts_collection).document()

            doc_ref.set(alert_data)

            # Enhanced logging for verification
            logger.info(f"✅ STORED ALERT - ID: {doc_ref.id}")
            logger.info(f"   Title: {alert_data['title']}")
            logger.info(f"   Event Date: {alert_data['event_date']}")
            logger.info(f"   Severity: {alert_data['severity']}")
            logger.info(f"   Area: {alert_data['area']}")
            logger.info(f"   Collection: {self.alerts_collection}")
            logger.info(
                f"   Firestore Path: {self.alerts_collection}/{doc_ref.id}")

            return doc_ref.id

        except Exception as e:
            logger.error(f"❌ FAILED TO STORE ALERT: {str(e)}")
            logger.error(f"   Alert data: {alert}")
            raise

    def _extract_event_date(self, alert: Dict) -> Optional[datetime]:
        """
        Extract event date from alert data

        Args:
            alert: Alert dictionary containing event_date field

        Returns:
            datetime object or None if no date available
        """
        try:
            # Get event_date directly from alert (provided by triage agent)
            event_date = alert.get('event_date')

            if event_date:
                if isinstance(event_date, datetime):
                    return event_date
                elif isinstance(event_date, str):
                    try:
                        # Handle YYYY-MM-DD format
                        return datetime.strptime(event_date, '%Y-%m-%d')
                    except ValueError:
                        try:
                            # Handle ISO format as fallback
                            return datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                        except ValueError:
                            pass

            return None
        except Exception as e:
            logger.warning(f"Error extracting event date: {e}")
            return None

    async def get_alerts_by_topic(self, topic: str, limit: int = 50) -> List[Dict]:
        """
        Retrieve alerts by topic, ordered by creation time (newest first)

        Args:
            topic: Topic to filter by
            limit: Maximum number of alerts to return

        Returns:
            List of alert dictionaries
        """
        try:
            query = (self.db.collection(self.alerts_collection)
                     .where(filter=firestore.FieldFilter('topic', '==', topic))
                     .where(filter=firestore.FieldFilter('status', '==', 'active'))
                     .order_by('created_at', direction=firestore.Query.DESCENDING)
                     .limit(limit))

            docs = query.stream()
            alerts = []
            for doc in docs:
                alert_data = doc.to_dict()
                alert_data['id'] = doc.id
                alerts.append(alert_data)

            return alerts

        except Exception as e:
            logger.error(f"Error retrieving alerts by topic {topic}: {str(e)}")
            return []

    async def get_high_severity_alerts(self, min_severity: int = 7, hours_back: int = 24) -> List[Dict]:
        """
        Get high-severity alerts from the last N hours

        Args:
            min_severity: Minimum severity score threshold (1-10)
            hours_back: Number of hours to look back

        Returns:
            List of high-severity alerts
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

            query = (self.db.collection(self.alerts_collection)
                     .where(filter=firestore.FieldFilter('severity', '>=', min_severity))
                     .where(filter=firestore.FieldFilter('created_at', '>=', cutoff_time))
                     .where(filter=firestore.FieldFilter('status', '==', 'active'))
                     .order_by('severity', direction=firestore.Query.DESCENDING))

            docs = query.stream()
            alerts = []
            for doc in docs:
                alert_data = doc.to_dict()
                alert_data['id'] = doc.id
                alerts.append(alert_data)

            return alerts

        except Exception as e:
            logger.error(f"Error retrieving high-severity alerts: {str(e)}")
            return []

    async def get_trending_topics(self, limit: int = 10) -> List[Dict]:
        """
        Get currently trending topics in NYC

        Args:
            limit: Maximum number of trending topics to return

        Returns:
            List of trending topic dictionaries
        """
        try:
            # Get alerts from last 6 hours and aggregate by topic
            cutoff_time = datetime.utcnow() - timedelta(hours=6)

            query = (self.db.collection(self.alerts_collection)
                     .where(filter=firestore.FieldFilter('created_at', '>=', cutoff_time))
                     .where(filter=firestore.FieldFilter('status', '==', 'active')))

            docs = query.stream()

            # Aggregate by topic
            topic_stats = {}
            for doc in docs:
                alert = doc.to_dict()
                topic = alert['topic']

                if topic not in topic_stats:
                    topic_stats[topic] = {
                        'topic': topic,
                        'alert_count': 0,
                        'avg_severity': 0,
                        'latest_alert': None,
                        'sources': set()
                    }

                stats = topic_stats[topic]
                stats['alert_count'] += 1
                stats['avg_severity'] = (
                    stats['avg_severity'] + alert.get('severity', 0)) / 2
                stats['sources'].add(alert['source'])

                if not stats['latest_alert'] or alert['created_at'] > stats['latest_alert']:
                    stats['latest_alert'] = alert['created_at']

            # Convert to list and sort by trending score
            trending = []
            for topic, stats in topic_stats.items():
                # Convert set to list for JSON serialization
                stats['sources'] = list(stats['sources'])
                trending_score = stats['alert_count'] * stats['avg_severity']
                stats['trending_score'] = trending_score
                trending.append(stats)

            # Sort by trending score and return top results
            trending.sort(key=lambda x: x['trending_score'], reverse=True)
            return trending[:limit]

        except Exception as e:
            logger.error(f"Error retrieving trending topics: {str(e)}")
            return []

    async def mark_alert_processed(self, alert_id: str) -> bool:
        """
        Mark an alert as processed

        Args:
            alert_id: ID of the alert to mark as processed

        Returns:
            True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(
                self.alerts_collection).document(alert_id)
            doc_ref.update({
                'status': 'processed',
                'updated_at': datetime.utcnow()
            })
            return True

        except Exception as e:
            logger.error(
                f"Error marking alert {alert_id} as processed: {str(e)}")
            return False

    async def cleanup_old_alerts(self, days_old: int = 30) -> int:
        """
        Clean up alerts older than specified days

        Args:
            days_old: Number of days after which to delete alerts

        Returns:
            Number of alerts deleted
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_old)

            query = (self.db.collection(self.alerts_collection)
                     .where(filter=firestore.FieldFilter('created_at', '<', cutoff_time)))

            docs = query.stream()
            deleted_count = 0

            for doc in docs:
                doc.reference.delete()
                deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old alerts")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {str(e)}")
            return 0

    async def store_monitor_run(self, run_stats: Dict) -> str:
        """
        Store monitor run statistics

        Args:
            run_stats: Dictionary containing run statistics and metadata

        Returns:
            Document ID of stored monitor run
        """
        try:
            logger.info("📊 Storing monitor run statistics...")

            # Add server timestamp
            run_stats['server_timestamp'] = firestore.SERVER_TIMESTAMP

            # Store in monitor_runs collection
            doc_ref = self.db.collection('monitor_runs').document()
            doc_ref.set(run_stats)

            logger.info(
                f"✅ Monitor run statistics stored with ID: {doc_ref.id}")
            return doc_ref.id

        except Exception as e:
            logger.error(f"❌ Failed to store monitor run statistics: {e}")
            raise

    async def get_recent_monitor_runs(self, limit: int = 10) -> List[Dict]:
        """
        Get recent monitor runs for debugging and monitoring

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of monitor run dictionaries
        """
        try:
            query = (self.db.collection(self.monitor_runs_collection)
                     .order_by('created_at', direction=firestore.Query.DESCENDING)
                     .limit(limit))

            docs = query.stream()
            runs = []
            for doc in docs:
                run_data = doc.to_dict()
                run_data['id'] = doc.id
                runs.append(run_data)

            return runs

        except Exception as e:
            logger.error(f"Error retrieving recent monitor runs: {str(e)}")
            return []

    async def get_monitor_run_stats(self, hours_back: int = 24) -> Dict:
        """
        Get aggregate statistics for monitor runs in the last N hours

        Args:
            hours_back: Number of hours to look back

        Returns:
            Dictionary with aggregate statistics
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

            query = (self.db.collection(self.monitor_runs_collection)
                     .where(filter=firestore.FieldFilter('created_at', '>=', cutoff_time))
                     .order_by('created_at', direction=firestore.Query.DESCENDING))

            docs = query.stream()

            total_runs = 0
            total_signals = 0
            total_alerts = 0
            successful_runs = 0
            source_totals = {}

            for doc in docs:
                run = doc.to_dict()
                total_runs += 1

                if run.get('status') == 'completed' and not run.get('errors'):
                    successful_runs += 1

                total_signals += run.get('total_signals_collected', 0)
                total_alerts += run.get('alerts_generated', 0)

                # Aggregate by source
                for source, stats in run.get('source_stats', {}).items():
                    if source not in source_totals:
                        source_totals[source] = 0
                    source_totals[source] += stats.get('signals_collected', 0)

            return {
                'period_hours': hours_back,
                'total_runs': total_runs,
                'successful_runs': successful_runs,
                'success_rate': successful_runs / total_runs if total_runs > 0 else 0,
                'total_signals_collected': total_signals,
                'total_alerts_generated': total_alerts,
                'avg_signals_per_run': total_signals / total_runs if total_runs > 0 else 0,
                'avg_alerts_per_run': total_alerts / total_runs if total_runs > 0 else 0,
                'source_totals': source_totals,
                'last_updated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating monitor run stats: {str(e)}")
            return {
                'error': str(e),
                'period_hours': hours_back,
                'last_updated': datetime.utcnow().isoformat()
            }

    async def get_recent_alerts(self, hours_back: int = 6) -> List[Dict]:
        """
        Get recent alerts from Firestore for duplicate detection

        Args:
            hours_back: How many hours back to search

        Returns:
            List of recent alert documents
        """
        try:
            logger.info(
                f"🔍 Querying recent alerts (last {hours_back} hours)...")

            # Calculate cutoff time
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

            # Query recent alerts
            alerts_ref = self.db.collection('nyc_monitor_alerts')
            query = alerts_ref.where(filter=firestore.FieldFilter('created_at', '>=', cutoff_time)).order_by(
                'created_at', direction=firestore.Query.DESCENDING).limit(50)

            docs = query.stream()
            recent_alerts = []

            for doc in docs:
                alert_data = doc.to_dict()
                alert_data['document_id'] = doc.id
                recent_alerts.append(alert_data)

            logger.info(f"✅ Found {len(recent_alerts)} recent alerts")
            return recent_alerts

        except Exception as e:
            logger.error(f"❌ Failed to query recent alerts: {e}")
            return []
