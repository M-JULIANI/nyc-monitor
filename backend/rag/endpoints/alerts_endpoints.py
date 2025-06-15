from fastapi import FastAPI, HTTPException
from sse_starlette.sse import EventSourceResponse
from firebase_admin import firestore
import asyncio
from datetime import datetime, timedelta
import json

app = FastAPI()
db = firestore.client()


async def alert_stream():
    """Stream new alerts via SSE"""
    try:
        # Get initial alerts from last 15 minutes
        alerts_ref = db.collection('nyc_monitor_alerts')
        cutoff_time = datetime.utcnow() - timedelta(minutes=120)

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
                    new_alerts.append(alert_data)
                    last_alert = alert_data

                if new_alerts:
                    yield {
                        'event': 'alerts',
                        'data': json.dumps({
                            'alerts': new_alerts,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    }

                # Wait before next poll
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in alert stream: {e}")
                await asyncio.sleep(5)  # Wait before retry

    except Exception as e:
        logger.error(f"Fatal error in alert stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/alerts/stream')
async def stream_alerts():
    return EventSourceResponse(alert_stream())
