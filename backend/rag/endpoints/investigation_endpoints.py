"""Investigation-related API endpoints."""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from typing import List
import json
import os
from datetime import datetime

from ..investigation_service import investigate_alert
from ..investigation.state_manager import AlertData
from ..investigation.progress_tracker import get_progress_tracker
from ..auth import verify_google_token

# Router
investigation_router = APIRouter(prefix="/investigate", tags=["investigation"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_google_token(token: str = Depends(oauth2_scheme)):
    """Token verification - should be moved to a shared auth module."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as grequests

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

    try:
        idinfo = id_token.verify_oauth2_token(
            token, grequests.Request(), GOOGLE_CLIENT_ID)
        return idinfo
    except Exception:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials")


class InvestigationResult(BaseModel):
    investigation_id: str
    status: str
    findings: str
    artifacts: list
    confidence_score: float


@investigation_router.post("", response_model=InvestigationResult)
@limiter.limit("3/minute")
async def investigate_alert_endpoint(
    request: Request,
    alert_data: AlertData,
    user=Depends(verify_google_token)
):
    """
    Investigate a specific alert using the multi-agent system.

    This triggers a full investigation including:
    - Research agent collecting data and artifacts
    - Analysis of findings  
    - Generation of investigation report

    Use GET /{investigation_id}/progress for real-time progress updates.
    Use GET /{investigation_id}/stream for Server-Sent Events streaming.
    """
    try:
        # Run the async investigation
        findings = await investigate_alert(alert_data)

        # Return structured investigation results
        investigation_result = InvestigationResult(
            investigation_id=alert_data.alert_id,
            status="completed",
            findings=findings,
            artifacts=[
                f"media_{alert_data.event_type}_0_0.png",
                f"screenshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            ],
            confidence_score=0.8
        )

        return investigation_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@investigation_router.get("/{investigation_id}/progress")
async def get_investigation_progress(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Get current progress for an investigation (polling endpoint)."""
    try:
        tracker = get_progress_tracker()
        progress = tracker.get_progress(investigation_id)
        latest = tracker.get_latest_progress(investigation_id)
        is_active = tracker.is_active(investigation_id)

        return {
            "investigation_id": investigation_id,
            "is_active": is_active,
            "latest_status": latest.status.value if latest else "unknown",
            "latest_message": latest.message if latest else None,
            "active_agent": latest.active_agent if latest else None,
            "current_task": latest.current_task if latest else None,
            "progress_history": [
                {
                    "timestamp": update.timestamp.isoformat(),
                    "status": update.status.value,
                    "active_agent": update.active_agent,
                    "current_task": update.current_task,
                    "message": update.message,
                    "metadata": update.metadata
                }
                for update in progress
            ],
            "total_updates": len(progress)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@investigation_router.get("/{investigation_id}/stream")
async def stream_investigation_progress(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Stream real-time progress updates for an investigation (Server-Sent Events)."""
    async def generate_progress_stream():
        tracker = get_progress_tracker()

        try:
            async for update in tracker.stream_progress(investigation_id):
                data = {
                    "timestamp": update.timestamp.isoformat(),
                    "investigation_id": update.investigation_id,
                    "status": update.status.value,
                    "active_agent": update.active_agent,
                    "current_task": update.current_task,
                    "message": update.message,
                    "metadata": update.metadata
                }

                yield f"data: {json.dumps(data)}\n\n"

                if update.status.value in ["completed", "error"]:
                    break

        except Exception as e:
            error_data = {
                "error": str(e),
                "investigation_id": investigation_id,
                "status": "error"
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_progress_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )
