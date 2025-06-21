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
from google.cloud import firestore

from ..investigation_service import investigate_alert as investigate_alert_adk
from ..investigation_service_simple import investigate_alert_simple
from ..investigation.state_manager import AlertData, state_manager
from ..investigation.progress_tracker import progress_tracker
from ..investigation.tracing import get_distributed_tracer
from ..auth import verify_google_token
from ..config import get_config

logger = logging.getLogger(__name__)

# Router
investigation_router = APIRouter(prefix="/investigate", tags=["investigation"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Get tracing service
tracer = get_distributed_tracer()


# Configuration for investigation approach
# config.INVESTIGATION_APPROACH = os.getenv(
#     "config.INVESTIGATION_APPROACH", "simple")  # "simple" or "adk"


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
    report_url: str | None
    trace_id: str | None


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
        # Use central configuration
        config = get_config()

        logger.info(f"Investigation endpoint called by user: {user}")
        logger.info(
            f"Starting investigation for alert {alert_request.alert_id}")
        logger.info(f"Investigation approach: {config.INVESTIGATION_APPROACH}")
        logger.info(f"Alert details: {alert_request}")

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

        logger.info(f"AlertData object created: {alert_data}")

        # Choose investigation approach based on configuration
        if config.INVESTIGATION_APPROACH == "adk":
            logger.info("Using ADK multi-agent investigation approach")
            try:
                investigation_result, investigation_id = await investigate_alert_adk(alert_data)
            except Exception as adk_error:
                logger.error(
                    f"ADK investigation failed: {adk_error}", exc_info=True)
                raise
        else:
            logger.info("Using simple direct model investigation approach")
            try:
                investigation_result, investigation_id = await investigate_alert_simple(alert_data)
            except Exception as simple_error:
                logger.error(
                    f"Simple investigation failed: {simple_error}", exc_info=True)
                raise

        logger.info(
            f"Investigation completed. Result length: {len(investigation_result) if investigation_result else 0}")
        logger.info(f"Investigation ID: {investigation_id}")

        # Get the investigation state using the returned investigation_id
        if investigation_id:
            investigation_state = state_manager.get_investigation(
                investigation_id)
            if investigation_state:
                logger.info(
                    f"Found investigation state: {investigation_state.investigation_id}")

                # Generate Google Slides presentation for this investigation
                report_url = None
                trace_id = None

                try:
                    # Generate slides with artifacts collected by ADK agents
                    from ..tools.report_tools import create_slides_presentation_func

                    slides_result = create_slides_presentation_func(
                        investigation_id=investigation_id,
                        title=f"{alert_data.event_type} Investigation - {alert_data.location}",
                        template_type="status_tracker",
                        evidence_types="all"
                    )

                    if slides_result.get('success'):
                        report_url = slides_result.get('url')
                        logger.info(f"✅ Generated slides report: {report_url}")
                    else:
                        logger.warning(
                            f"⚠️ Slides generation failed: {slides_result.get('error')}")

                except Exception as e:
                    logger.warning(f"⚠️ Could not generate slides report: {e}")

                # Save agent trace to Firestore
                try:
                    trace_id = save_agent_trace_to_firestore(investigation_id)
                    if trace_id:
                        logger.info(f"✅ Saved agent trace: {trace_id}")
                    else:
                        logger.warning("⚠️ Could not save agent trace")
                except Exception as e:
                    logger.warning(f"⚠️ Error saving agent trace: {e}")

                return InvestigationResponse(
                    investigation_id=investigation_state.investigation_id,
                    status="completed",
                    findings=investigation_result,
                    artifacts=[artifact.get('filename', artifact.get('file', str(
                        artifact))) for artifact in investigation_state.artifacts] if investigation_state.artifacts else [],
                    confidence_score=investigation_state.confidence_score,
                    report_url=report_url,  # Add report URL to response
                    trace_id=trace_id       # Add trace ID to response
                )
            else:
                logger.warning(
                    f"No investigation state found for ID: {investigation_id}")

        # Fallback if state not found or no investigation_id
        logger.warning(
            "Using fallback response - no investigation state available")
        return InvestigationResponse(
            investigation_id=investigation_id or f"fallback_{alert_request.alert_id}",
            status="completed",
            findings=investigation_result,
            artifacts=[],
            confidence_score=0.7,
            report_url=None,
            trace_id=None
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Investigation endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Investigation failed: {str(e)}")


@investigation_router.get("/{investigation_id}/progress")
async def get_investigation_progress(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Get the current progress of an investigation"""
    try:
        config = get_config()
        progress = progress_tracker.get_progress(investigation_id)
        if not progress:
            raise HTTPException(
                status_code=404, detail="Investigation not found")

        return {
            "investigation_id": investigation_id,
            "progress": progress,
            "approach": config.INVESTIGATION_APPROACH
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
            yield f"data: {{'status': 'connected', 'investigation_id': '{investigation_id}', 'approach': '{config.INVESTIGATION_APPROACH}'}}\n\n"

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
            "approach": config.INVESTIGATION_APPROACH
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
            "approach": config.INVESTIGATION_APPROACH
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
        config = get_config()
        trace_data = tracer.export_trace(investigation_id)

        if not trace_data:
            raise HTTPException(status_code=404, detail="Trace data not found")

        return {
            "investigation_id": investigation_id,
            "trace_data": trace_data,
            "approach": config.INVESTIGATION_APPROACH,
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
            "approach": config.INVESTIGATION_APPROACH
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
        "investigation_approach": config.INVESTIGATION_APPROACH,
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
            "multi_agent": config.INVESTIGATION_APPROACH == "adk"
        }
    }


def save_agent_trace_to_firestore(investigation_id: str) -> str:
    """Save agent trace to Firestore and return trace ID.

    Args:
        investigation_id: Investigation ID to get trace for

    Returns:
        Firestore document ID for the saved trace
    """
    try:
        # Get trace data
        trace_data = tracer.export_trace(investigation_id)

        if not trace_data:
            logger.warning(
                f"No trace data found for investigation {investigation_id}")
            return None

        # Initialize Firestore
        db = firestore.Client()

        # Prepare trace document
        trace_doc = {
            'investigation_id': investigation_id,
            # Convert to JSON-serializable format
            'trace_data': json.loads(json.dumps(trace_data, default=str)),
            'created_at': datetime.utcnow(),
            'approach': get_config().INVESTIGATION_APPROACH
        }

        # Save to Firestore
        doc_ref = db.collection('agent_traces').add(trace_doc)
        trace_id = doc_ref[1].id

        logger.info(f"✅ Saved agent trace to Firestore: {trace_id}")
        return trace_id

    except Exception as e:
        logger.error(f"❌ Failed to save agent trace: {e}")
        return None
