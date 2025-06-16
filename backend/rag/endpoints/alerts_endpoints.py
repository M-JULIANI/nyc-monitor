from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from google.cloud import firestore
from ..config import get_config
import asyncio
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

# Initialize router
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_db():
    """Get Firestore client instance"""
    return firestore.Client(project=get_config().GOOGLE_CLOUD_PROJECT)


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
                    yield {
                        'event': 'alerts',
                        'data': json.dumps({
                            'alerts': new_alerts,
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
                 .limit(limit))

        docs = query.stream()
        alerts = []

        for doc in docs:
            alert_data = doc.to_dict()
            alert_data['id'] = doc.id  # Add document ID if not present
            alerts.append(alert_data)

        return {'alerts': alerts, 'count': len(alerts)}

    except Exception as e:
        logger.error(f"Error fetching recent alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")
