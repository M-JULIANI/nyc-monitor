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
        self.alerts_collection = 'monitor_alerts'
        self.trends_collection = 'trending_topics'
        
    async def store_alert(self, alert: Dict) -> str:
        """
        Store an monitor alert in Firestore
        
        Args:
            alert: Dictionary containing alert data with required fields:
                - topic: str
                - url: str  
                - confidence_score: float
                - source: str
                - alert_type: str
                - metadata: dict
                
        Returns:
            Document ID of stored alert
        """
        try:
            # Add timestamps and NYC location context
            alert_data = {
                **alert,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'location': 'NYC',
                'status': 'active'
            }
            
            # Validate required fields
            required_fields = ['topic', 'url', 'confidence_score', 'source', 'alert_type']
            for field in required_fields:
                if field not in alert_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Store in Firestore
            doc_ref = self.db.collection(self.alerts_collection).document()
            doc_ref.set(alert_data)
            
            logger.info(f"Stored alert {doc_ref.id} for topic: {alert['topic']}")
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"Error storing alert: {str(e)}")
            raise
    
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
                    .where('topic', '==', topic)
                    .where('status', '==', 'active')
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
    
    async def get_high_confidence_alerts(self, min_confidence: float = 0.8, hours_back: int = 24) -> List[Dict]:
        """
        Get high-confidence alerts from the last N hours
        
        Args:
            min_confidence: Minimum confidence score threshold
            hours_back: Number of hours to look back
            
        Returns:
            List of high-confidence alerts
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            query = (self.db.collection(self.alerts_collection)
                    .where('confidence_score', '>=', min_confidence)
                    .where('created_at', '>=', cutoff_time)
                    .where('status', '==', 'active')
                    .order_by('confidence_score', direction=firestore.Query.DESCENDING))
            
            docs = query.stream()
            alerts = []
            for doc in docs:
                alert_data = doc.to_dict()
                alert_data['id'] = doc.id
                alerts.append(alert_data)
                
            return alerts
            
        except Exception as e:
            logger.error(f"Error retrieving high-confidence alerts: {str(e)}")
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
                    .where('created_at', '>=', cutoff_time)
                    .where('status', '==', 'active'))
            
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
                        'avg_confidence': 0,
                        'latest_alert': None,
                        'sources': set()
                    }
                
                stats = topic_stats[topic]
                stats['alert_count'] += 1
                stats['avg_confidence'] = (stats['avg_confidence'] + alert['confidence_score']) / 2
                stats['sources'].add(alert['source'])
                
                if not stats['latest_alert'] or alert['created_at'] > stats['latest_alert']:
                    stats['latest_alert'] = alert['created_at']
            
            # Convert to list and sort by trending score
            trending = []
            for topic, stats in topic_stats.items():
                stats['sources'] = list(stats['sources'])  # Convert set to list for JSON serialization
                trending_score = stats['alert_count'] * stats['avg_confidence']
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
            doc_ref = self.db.collection(self.alerts_collection).document(alert_id)
            doc_ref.update({
                'status': 'processed',
                'updated_at': datetime.utcnow()
            })
            return True
            
        except Exception as e:
            logger.error(f"Error marking alert {alert_id} as processed: {str(e)}")
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
                    .where('created_at', '<', cutoff_time))
            
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