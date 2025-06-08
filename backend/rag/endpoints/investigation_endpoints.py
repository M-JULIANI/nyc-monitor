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
from ..investigation.tracing import get_distributed_tracer
from ..auth import verify_google_token

# Router
investigation_router = APIRouter(prefix="/investigate", tags=["investigation"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Get tracing service
tracer = get_distributed_tracer()


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


@investigation_router.get("/{investigation_id}/trace/summary")
async def get_trace_summary(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Get distributed tracing summary for an investigation."""
    try:
        summary = tracer.get_trace_summary(investigation_id)
        return {
            "investigation_id": investigation_id,
            "tracing_summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@investigation_router.get("/{investigation_id}/trace/timeline")
async def get_trace_timeline(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Get chronological timeline of all trace events for an investigation."""
    try:
        timeline = tracer.get_trace_timeline(investigation_id)
        return {
            "investigation_id": investigation_id,
            "trace_timeline": timeline,
            "total_events": len(timeline)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@investigation_router.get("/{investigation_id}/trace/export")
async def export_trace_data(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Export complete trace data for an investigation (spans, messages, timeline)."""
    try:
        trace_data = tracer.export_trace(investigation_id)
        return {
            "investigation_id": investigation_id,
            "trace_export": trace_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@investigation_router.get("/{investigation_id}/agent-flow")
async def get_agent_message_flow(
    investigation_id: str,
    user=Depends(verify_google_token)
):
    """Get a visualization-friendly view of agent message flow and interactions."""
    try:
        timeline = tracer.get_trace_timeline(investigation_id)
        summary = tracer.get_trace_summary(investigation_id)

        # Extract agent interactions
        agent_interactions = []
        message_events = [
            event for event in timeline if event.get("type") == "message"]

        for msg in message_events:
            agent_interactions.append({
                "timestamp": msg["timestamp"],
                "from": msg["from_agent"],
                "to": msg["to_agent"],
                "message_type": msg["message_type"],
                "content_preview": msg["content_preview"],
                "metadata": msg.get("metadata", {})
            })

        # Extract agent execution spans
        span_events = [event for event in timeline if event.get(
            "type") in ["span_start", "span_end"]]
        agent_executions = []

        for event in span_events:
            if event.get("type") == "span_start" and event.get("agent"):
                agent_executions.append({
                    "timestamp": event["timestamp"],
                    "agent": event["agent"],
                    "operation": event["operation"],
                    "span_id": event["span_id"],
                    "tool": event.get("tool"),
                    "metadata": event.get("metadata", {})
                })

        return {
            "investigation_id": investigation_id,
            "agent_message_flow": {
                "agent_interactions": agent_interactions,
                "agent_executions": agent_executions,
                "summary": {
                    "total_messages": len(message_events),
                    "total_agent_executions": len(agent_executions),
                    "agents_involved": summary.get("agents_involved", []),
                    "tools_used": summary.get("tools_used", []),
                    "total_duration_ms": summary.get("total_duration_ms", 0)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
