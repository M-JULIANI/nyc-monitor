"""Investigation-related API endpoints."""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from typing import List, Dict
import json
import os
from datetime import datetime
import asyncio
import logging

from ..investigation_service import investigate_alert as investigate_alert_adk
from ..investigation_service_simple import investigate_alert_simple
from ..investigation.state_manager import AlertData, state_manager
from ..investigation.progress_tracker import progress_tracker
from ..investigation.tracing import get_distributed_tracer
from ..auth import verify_google_token

logger = logging.getLogger(__name__)

# Router
investigation_router = APIRouter(prefix="/investigate", tags=["investigation"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Get tracing service
tracer = get_distributed_tracer()

# Configuration for investigation approach
INVESTIGATION_APPROACH = os.getenv(
    "INVESTIGATION_APPROACH", "simple")  # "simple" or "adk"


class AlertRequest(BaseModel):
    alert_id: str
    severity: int
    event_type: str
    location: str
    summary: str
    timestamp: str
    sources: List[str]


class InvestigationResponse(BaseModel):
    investigation_id: str
    status: str
    findings: str
    artifacts: List[str]
    confidence_score: float


@investigation_router.post("", response_model=InvestigationResponse)
async def start_investigation(
    alert_request: AlertRequest,
    user=Depends(verify_google_token)
):
    """
    Start a new investigation for an alert.
    Supports both simple (direct model) and complex (ADK) approaches.
    """
    try:
        logger.info(
            f"Starting investigation for alert {alert_request.alert_id}")
        logger.info(f"Investigation approach: {INVESTIGATION_APPROACH}")

        # Create AlertData object
        alert_data = AlertData(
            alert_id=alert_request.alert_id,
            severity=alert_request.severity,
            event_type=alert_request.event_type,
            location=alert_request.location,
            summary=alert_request.summary,
            timestamp=alert_request.timestamp,
            sources=alert_request.sources
        )

        # Choose investigation approach based on configuration
        if INVESTIGATION_APPROACH == "adk":
            logger.info("Using ADK multi-agent investigation approach")
            investigation_result = await investigate_alert_adk(alert_data)
        else:
            logger.info("Using simple direct model investigation approach")
            investigation_result = await investigate_alert_simple(alert_data)

        # Get the investigation state to return structured response
        investigations = state_manager.get_investigations_by_alert(
            alert_request.alert_id)
        if investigations:
            investigation_state = investigations[0]  # Get most recent

            return InvestigationResponse(
                investigation_id=investigation_state.investigation_id,
                status="completed",
                findings=investigation_result,
                artifacts=investigation_state.artifacts,
                confidence_score=investigation_state.confidence_score
            )
        else:
            # Fallback if state not found
            return InvestigationResponse(
                investigation_id=f"fallback_{alert_request.alert_id}",
                status="completed",
                findings=investigation_result,
                artifacts=[],
                confidence_score=0.7
            )

    except Exception as e:
        logger.error(f"Failed to start investigation: {e}")
        raise HTTPException(
            status_code=500, detail=f"Investigation failed: {str(e)}")


@investigation_router.get("/{investigation_id}/progress")
async def get_investigation_progress(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Get the current progress of an investigation"""
    try:
        progress = progress_tracker.get_progress(investigation_id)
        if not progress:
            raise HTTPException(
                status_code=404, detail="Investigation not found")

        return {
            "investigation_id": investigation_id,
            "progress": progress,
            "approach": INVESTIGATION_APPROACH
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@investigation_router.get("/{investigation_id}/stream")
async def stream_investigation_progress(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Stream real-time progress updates"""
    async def generate_progress_stream():
        """Generate Server-Sent Events for progress updates"""
        try:
            # Send initial connection
            yield f"data: {{'status': 'connected', 'investigation_id': '{investigation_id}', 'approach': '{INVESTIGATION_APPROACH}'}}\n\n"

            # Stream progress updates
            last_update_count = 0
            max_iterations = 120  # 2 minutes with 1-second intervals

            for i in range(max_iterations):
                progress = progress_tracker.get_progress(investigation_id)

                if progress and len(progress) > last_update_count:
                    # Send new progress updates
                    for update in progress[last_update_count:]:
                        yield f"data: {update.to_json()}\n\n"
                    last_update_count = len(progress)

                # Check if investigation is complete
                investigation_state = state_manager.get_investigation(
                    investigation_id)
                if investigation_state and investigation_state.is_complete:
                    yield f"data: {{'status': 'completed', 'investigation_id': '{investigation_id}'}}\n\n"
                    break

                # Wait before next check
                await asyncio.sleep(1)

            # Send final status
            yield f"data: {{'status': 'stream_ended', 'investigation_id': '{investigation_id}'}}\n\n"

        except Exception as e:
            logger.error(f"Error in progress stream: {e}")
            yield f"data: {{'error': 'Stream error: {str(e)}'}}\n\n"

    return StreamingResponse(
        generate_progress_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

# Distributed Tracing Endpoints


@investigation_router.get("/{investigation_id}/trace/summary")
async def get_trace_summary(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Get high-level trace summary"""
    try:
        summary = tracer.get_trace_summary(investigation_id)

        if not summary:
            raise HTTPException(status_code=404, detail="Trace not found")

        return {
            "investigation_id": investigation_id,
            "trace_summary": summary,
            "approach": INVESTIGATION_APPROACH
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trace summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@investigation_router.get("/{investigation_id}/trace/timeline")
async def get_trace_timeline(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Get chronological timeline of trace events"""
    try:
        timeline = tracer.get_trace_timeline(investigation_id)

        if not timeline:
            raise HTTPException(
                status_code=404, detail="Trace timeline not found")

        return {
            "investigation_id": investigation_id,
            "timeline": timeline,
            "approach": INVESTIGATION_APPROACH
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trace timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@investigation_router.get("/{investigation_id}/trace/export")
async def export_trace_data(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Export complete trace data"""
    try:
        trace_data = tracer.export_trace_data(investigation_id)

        if not trace_data:
            raise HTTPException(status_code=404, detail="Trace data not found")

        return {
            "investigation_id": investigation_id,
            "trace_data": trace_data,
            "approach": INVESTIGATION_APPROACH,
            "exported_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export trace data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@investigation_router.get("/{investigation_id}/agent-flow")
async def get_agent_message_flow(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Get agent message flow visualization data"""
    try:
        agent_flow = tracer.get_agent_message_flow(investigation_id)

        if not agent_flow:
            raise HTTPException(
                status_code=404, detail="Agent flow data not found")

        return {
            "investigation_id": investigation_id,
            "agent_message_flow": agent_flow,
            "approach": INVESTIGATION_APPROACH
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Configuration endpoint


@investigation_router.get("/config")
async def get_investigation_config(user=Depends(verify_google_token)):
    """Get current investigation system configuration"""
    return {
        "investigation_approach": INVESTIGATION_APPROACH,
        "approaches_available": ["simple", "adk"],
        "simple_approach": {
            "description": "Direct model calls, no deployment required",
            "features": ["Single AI call", "Fast execution", "Basic tracing", "State management"],
            "deployment_required": False
        },
        "adk_approach": {
            "description": "Full ADK multi-agent system with deployment",
            "features": ["Multi-agent coordination", "Tool execution", "Advanced tracing", "Session management"],
            "deployment_required": True
        },
        "current_features": {
            "distributed_tracing": True,
            "progress_tracking": True,
            "state_management": True,
            "multi_agent": INVESTIGATION_APPROACH == "adk"
        }
    }
