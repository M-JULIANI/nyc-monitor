from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from google.cloud import firestore
from ..config import get_config
import asyncio
from datetime import datetime, timedelta
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Initialize router
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_db():
    """Get Firestore client instance"""
    return firestore.Client(project=get_config().GOOGLE_CLOUD_PROJECT)


def deduplicate_alerts(alerts: List[Dict[Any, Any]]) -> List[Dict[Any, Any]]:
    """
    Remove duplicate alerts based on title, event date, and location.
    Keeps the most recent alert when duplicates are found.
    """
    if not alerts:
        return alerts

    # Create a map to track unique alerts
    unique_alerts = {}

    for alert in alerts:
        # Create a deduplication key from title, event date, and location
        title = (alert.get('title') or '').lower().strip()

        # Try to get event date from multiple possible fields
        event_date = None
        if alert.get('event_date'):
            event_date = alert['event_date']
        elif alert.get('original_alert', {}).get('event_date'):
            event_date = alert['original_alert']['event_date']

        # Try to get location info
        location = ''
        if alert.get('area'):
            location = alert['area'].lower().strip()
        elif alert.get('original_alert', {}).get('area'):
            location = alert['original_alert']['area'].lower().strip()
        elif alert.get('venue_address'):
            location = alert['venue_address'].lower().strip()
        elif alert.get('original_alert', {}).get('original_alert_data', {}).get('venue_address'):
            location = alert['original_alert']['original_alert_data']['venue_address'].lower(
            ).strip()

        # Create unique key
        dedup_key = f"{title}|{event_date}|{location}"

        # Get creation timestamp for comparison
        created_at = alert.get('created_at') or alert.get(
            'original_alert', {}).get('created_at')

        # If this key exists, keep the more recent alert
        if dedup_key in unique_alerts:
            existing_created_at = unique_alerts[dedup_key].get(
                'created_at') or unique_alerts[dedup_key].get('original_alert', {}).get('created_at')

            # Compare timestamps (keep more recent)
            if created_at and existing_created_at:
                if created_at > existing_created_at:
                    unique_alerts[dedup_key] = alert
            # If no timestamp comparison possible, keep the first one
        else:
            unique_alerts[dedup_key] = alert

    # Return deduplicated alerts, sorted by creation time (most recent first)
    deduplicated = list(unique_alerts.values())
    deduplicated.sort(key=lambda x: x.get('created_at') or x.get(
        'original_alert', {}).get('created_at') or '', reverse=True)

    logger.info(
        f"Deduplicated {len(alerts)} alerts down to {len(deduplicated)} unique alerts")
    return deduplicated


async def alert_stream():
    """Stream new alerts via SSE"""
    try:
        db = get_db()
        # Get initial alerts from last 2 hours
        alerts_ref = db.collection('nyc_monitor_alerts')
        cutoff_time = datetime.utcnow() - timedelta(hours=2)

        # Initial query for recent alerts
        query = (alerts_ref
                 .where('created_at', '>=', cutoff_time)
                 .order_by('created_at', direction=firestore.Query.DESCENDING))

        # Track last seen alert
        last_alert = None

        while True:
            try:
                # Get new alerts
                if last_alert:
                    query = (alerts_ref
                             .where('created_at', '>', last_alert.get('created_at'))
                             .order_by('created_at', direction=firestore.Query.DESCENDING))

                docs = query.limit(10).stream()
                new_alerts = []

                for doc in docs:
                    alert_data = doc.to_dict()
                    alert_data['id'] = doc.id  # Add document ID if not present
                    new_alerts.append(alert_data)
                    last_alert = alert_data  # Keep original for timestamp comparison

                if new_alerts:
                    # Deduplicate before sending
                    deduplicated_alerts = deduplicate_alerts(new_alerts)

                    if deduplicated_alerts:  # Only send if we have unique alerts
                        yield {
                            'event': 'alerts',
                            'data': json.dumps({
                                'alerts': deduplicated_alerts,
                                'timestamp': datetime.utcnow().isoformat()
                            })
                        }

                # Wait 30 minutes before next poll
                await asyncio.sleep(1800)  # 30 minutes = 1800 seconds

            except Exception as e:
                logger.error(f"Error in alert stream: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes before retry

    except Exception as e:
        logger.error(f"Fatal error in alert stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@alerts_router.get('/stream')
async def stream_alerts():
    """Stream alerts via Server-Sent Events"""
    return EventSourceResponse(alert_stream())


@alerts_router.get('/recent')
async def get_recent_alerts(limit: int = 100):
    """Get recent alerts (non-streaming)"""
    try:
        db = get_db()
        alerts_ref = db.collection('nyc_monitor_alerts')
        cutoff_time = datetime.utcnow() - timedelta(hours=48)

        query = (alerts_ref
                 .where('created_at', '>=', cutoff_time)
                 .order_by('created_at', direction=firestore.Query.DESCENDING)
                 .limit(limit * 2))  # Get more alerts to account for deduplication

        docs = query.stream()
        alerts = []

        for doc in docs:
            alert_data = doc.to_dict()
            alert_data['id'] = doc.id  # Add document ID if not present
            alerts.append(alert_data)

        # Deduplicate alerts before returning
        deduplicated_alerts = deduplicate_alerts(alerts)

        # Limit to requested number after deduplication
        final_alerts = deduplicated_alerts[:limit]

        return {'alerts': final_alerts, 'count': len(final_alerts)}

    except Exception as e:
        logger.error(f"Error fetching recent alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")
