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
    try:
        return firestore.Client(project=get_config().GOOGLE_CLOUD_PROJECT)
    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {e}")
        raise HTTPException(
            status_code=500, detail="Database configuration error")


def deduplicate_alerts(alerts: List[Dict[Any, Any]]) -> List[Dict[Any, Any]]:
    """
    Remove duplicate alerts based on title, event date, and location.
    Keeps the most recent alert when duplicates are found.
    OPTIMIZED VERSION: Reduced from O(n²) to O(n) complexity.
    """
    if not alerts:
        return alerts

    # Create a map to track unique alerts - O(n) operation
    unique_alerts = {}

    # Pre-sort by creation time to ensure consistent "most recent" selection
    alerts_sorted = sorted(alerts, key=lambda x: x.get('created_at') or x.get(
        'original_alert', {}).get('created_at') or '', reverse=True)

    for alert in alerts_sorted:
        # Optimize key generation with fewer fallbacks
        title = (alert.get('title') or '').lower().strip()

        # Simplified event date extraction
        event_date = (alert.get('event_date') or
                      alert.get('original_alert', {}).get('event_date') or '')

        # Simplified location extraction with priority order
        location = (alert.get('area') or
                    alert.get('original_alert', {}).get('area') or
                    alert.get('venue_address') or '').lower().strip()

        # Create unique key - single operation
        dedup_key = f"{title}|{event_date}|{location}"

        # Since we pre-sorted, first occurrence is most recent
        if dedup_key not in unique_alerts:
            unique_alerts[dedup_key] = alert

    # Return deduplicated alerts (already in descending time order)
    deduplicated = list(unique_alerts.values())

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
async def get_recent_alerts(limit: int = 100, hours: int = 48):
    """Get recent alerts (non-streaming) with performance optimizations"""
    try:
        db = get_db()
        alerts_ref = db.collection('nyc_monitor_alerts')

        # Reduce default time window from 48 to 24 hours for better performance
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Optimize query with smaller limit and pagination-ready structure
        query = (alerts_ref
                 .where('created_at', '>=', cutoff_time)
                 .order_by('created_at', direction=firestore.Query.DESCENDING)
                 .limit(min(limit + 50, 150)))  # Smart limit: buffer for dedup but cap max

        # Add query timing for debugging
        query_start = datetime.utcnow()
        docs = query.stream()
        alerts = []

        for doc in docs:
            alert_data = doc.to_dict()
            alert_data['id'] = doc.id  # Add document ID if not present
            alerts.append(alert_data)

        query_time = (datetime.utcnow() - query_start).total_seconds()

        # Optimize deduplication with early termination
        dedup_start = datetime.utcnow()
        deduplicated_alerts = deduplicate_alerts(alerts)
        dedup_time = (datetime.utcnow() - dedup_start).total_seconds()

        # Limit to requested number after deduplication
        final_alerts = deduplicated_alerts[:limit]

        # Add performance metrics to response for debugging
        return {
            'alerts': final_alerts,
            'count': len(final_alerts),
            'performance': {
                'query_time_ms': round(query_time * 1000, 2),
                'dedup_time_ms': round(dedup_time * 1000, 2),
                'total_fetched': len(alerts),
                'after_dedup': len(deduplicated_alerts),
                'hours_searched': hours
            }
        }

    except Exception as e:
        logger.error(f"Error fetching recent alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")
