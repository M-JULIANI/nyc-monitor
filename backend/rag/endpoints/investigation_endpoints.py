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
        logger.info(f"Investigation endpoint called by user: {user}")
        logger.info(
            f"Starting investigation for alert {alert_request.alert_id}")
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

        # Update alert status to investigating in Firestore
        logger.info(
            f"🔄 Updating alert {alert_request.alert_id} status to investigating in Firestore")
        try:
            success = update_alert_status_to_investigating(
                alert_request.alert_id)
            if success:
                logger.info(
                    f"✅ Successfully updated alert {alert_request.alert_id} to investigating")
            else:
                logger.error(
                    f"❌ Failed to update alert {alert_request.alert_id} to investigating")
        except Exception as e:
            logger.warning(
                f"⚠️ Could not update alert status to investigating: {e}")

        # Choose investigation approach based on configuration
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

                # Extract the presentation URL from the artifacts if available
                report_url = None
                trace_id = None

                logger.info(
                    f"🔍 Looking for presentation URL in {len(investigation_state.artifacts)} artifacts")

                # Look for presentation URL in the agent response or artifacts
                for i, artifact in enumerate(investigation_state.artifacts):
                    logger.info(
                        f"📄 Artifact {i}: type={artifact.get('type')}, filename={artifact.get('filename')}, url={artifact.get('url')}, public_url={artifact.get('public_url')}")

                    # Check for presentation-type artifacts or URLs containing Google Slides
                    if (artifact.get('type') == 'presentation' or
                        'presentation' in artifact.get('filename', '').lower() or
                        'slides' in artifact.get('filename', '').lower() or
                        'docs.google.com/presentation' in str(artifact.get('url', '')) or
                            'docs.google.com/presentation' in str(artifact.get('public_url', ''))):

                        report_url = artifact.get(
                            'url') or artifact.get('public_url')
                        logger.info(
                            f"✅ Found presentation URL in artifact {i}: {report_url}")
                        break

                # Check if there are any function results in the investigation state
                if not report_url and hasattr(investigation_state, 'function_results'):
                    logger.info(
                        "🔍 Checking function results for presentation URL...")
                    for func_name, func_result in investigation_state.function_results.items():
                        if 'create_slides_presentation' in func_name:
                            if isinstance(func_result, dict) and func_result.get('url'):
                                report_url = func_result.get('url')
                                logger.info(
                                    f"✅ Found presentation URL in function result: {report_url}")
                                break

                # If no presentation URL found in artifacts, check if it's mentioned in the investigation result
                if not report_url and investigation_result:
                    logger.info(
                        f"🔍 No presentation URL in artifacts, searching investigation result text ({len(investigation_result)} characters)")
                    import re

                    # Enhanced Google Slides URL patterns - more comprehensive matching
                    slides_patterns = [
                        # Standard sharing URL with edit permissions
                        r'https://docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)/edit\?usp=sharing',
                        # Edit URL without sharing parameter
                        r'https://docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)/edit',
                        # Basic presentation URL
                        r'https://docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)',
                        # More flexible pattern for URL variations
                        r'docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)(?:/[^\\s]*)?'
                    ]

                    for pattern in slides_patterns:
                        match = re.search(pattern, investigation_result)
                        if match:
                            # Reconstruct the full sharing URL
                            presentation_id = match.group(1)
                            report_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit?usp=sharing"
                            logger.info(
                                f"✅ Found presentation URL in agent response with pattern '{pattern}': {report_url}")
                            break

                    if not report_url:
                        logger.warning(
                            f"⚠️ No Google Slides URL found in investigation result")
                        # Log a snippet of the investigation result for debugging
                        snippet = investigation_result[:1000] + "..." if len(
                            investigation_result) > 1000 else investigation_result
                        logger.info(
                            f"📝 Investigation result snippet: {snippet}")

                        # Look for any URLs in the response for debugging
                        url_pattern = r'https?://[^\s]+'
                        urls = re.findall(url_pattern, investigation_result)
                        if urls:
                            logger.info(
                                f"🔗 Found other URLs in response: {urls[:5]}")  # Limit to first 5 for brevity
                        else:
                            logger.warning(
                                f"⚠️ No URLs found at all in investigation result")
                else:
                    logger.info(f"📎 Report URL found: {report_url}")

                # Save agent trace to Firestore
                try:
                    trace_id = save_agent_trace_to_firestore(investigation_id)
                    if trace_id:
                        logger.info(f"✅ Saved agent trace: {trace_id}")
                    else:
                        logger.warning("⚠️ Could not save agent trace")
                except Exception as e:
                    logger.warning(f"⚠️ Error saving agent trace: {e}")

                # Update the alert in Firestore with investigation results
                try:
                    success = update_alert_with_investigation_results(
                        alert_id=alert_request.alert_id,
                        investigation_id=investigation_state.investigation_id,
                        report_url=report_url,
                        trace_id=trace_id
                    )
                    if success:
                        logger.info(
                            f"✅ Updated alert {alert_request.alert_id} in Firestore")
                    else:
                        logger.warning(
                            f"⚠️ Could not update alert {alert_request.alert_id} in Firestore")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Error updating alert in Firestore: {e}")

                return InvestigationResponse(
                    investigation_id=investigation_state.investigation_id,
                    status="completed",
                    findings=investigation_result,
                    artifacts=[artifact.get('filename', artifact.get('file', str(
                        artifact))) for artifact in investigation_state.artifacts] if investigation_state.artifacts else [],
                    confidence_score=investigation_state.confidence_score,
                    report_url=report_url,  # Use URL from agent artifacts
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
        progress = progress_tracker.get_progress(investigation_id)
        if not progress:
            raise HTTPException(
                status_code=404, detail="Investigation not found")

        return {
            "investigation_id": investigation_id,
            "progress": progress,
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
            yield f"data: {{'status': 'connected', 'investigation_id': '{investigation_id}'}}\n\n"

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
        trace_data = tracer.export_trace(investigation_id)

        if not trace_data:
            raise HTTPException(status_code=404, detail="Trace data not found")

        return {
            "investigation_id": investigation_id,
            "trace_data": trace_data,
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
        "investigation_approach": "simple",
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
            "multi_agent": False
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
        }

        # Save to Firestore
        doc_ref = db.collection('agent_traces').add(trace_doc)
        trace_id = doc_ref[1].id

        logger.info(f"✅ Saved agent trace to Firestore: {trace_id}")
        return trace_id

    except Exception as e:
        logger.error(f"❌ Failed to save agent trace: {e}")
        return None


def update_alert_status_to_investigating(alert_id: str) -> bool:
    """Update the alert status to 'investigating' when investigation starts.

    Args:
        alert_id: The alert ID to update

    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Initialize Firestore
        db = firestore.Client()

        # Update the alert document status
        alert_ref = db.collection('nyc_monitor_alerts').document(alert_id)

        # Check if document exists first
        doc = alert_ref.get()
        if not doc.exists:
            logger.error(
                f"❌ Alert document {alert_id} does not exist in Firestore")
            return False

        logger.info(f"📋 Current alert {alert_id} data: {doc.to_dict()}")

        # Update data
        update_data = {
            'status': 'investigating',
            'updated_at': datetime.utcnow(),
        }

        # Update the document
        alert_ref.update(update_data)

        # Verify the update
        updated_doc = alert_ref.get()
        logger.info(f"✅ Updated alert {alert_id} status to investigating")
        logger.info(f"📋 New alert {alert_id} data: {updated_doc.to_dict()}")
        return True

    except Exception as e:
        logger.error(
            f"❌ Failed to update alert {alert_id} status to investigating: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False


def update_alert_with_investigation_results(alert_id: str, investigation_id: str, report_url: str = None, trace_id: str = None) -> bool:
    """Update the alert in Firestore with investigation results.

    Args:
        alert_id: The alert ID to update
        investigation_id: The investigation ID that was run
        report_url: URL to the generated report/presentation
        trace_id: ID of the saved trace in Firestore

    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Initialize Firestore
        db = firestore.Client()

        # Update the alert document with investigation results
        alert_ref = db.collection('nyc_monitor_alerts').document(alert_id)

        # Check if document exists first
        doc = alert_ref.get()
        if not doc.exists:
            logger.error(
                f"❌ Alert document {alert_id} does not exist in Firestore")
            return False

        logger.info(
            f"📋 Current alert {alert_id} data before final update: {doc.to_dict()}")

        # Prepare update data
        update_data = {
            'status': 'resolved',  # Update status to resolved when investigation completes
            'investigation_id': investigation_id,
            'updated_at': datetime.utcnow(),
        }

        # Add optional fields if provided
        if report_url:
            update_data['report_url'] = report_url
            logger.info(f"📎 Adding report_url to update: {report_url}")
        else:
            logger.warning(f"⚠️ No report_url provided for alert {alert_id}")

        if trace_id:
            update_data['trace_id'] = trace_id
            logger.info(f"📋 Adding trace_id to update: {trace_id}")

        logger.info(f"📝 Final update data for alert {alert_id}: {update_data}")

        # Update the document
        alert_ref.update(update_data)

        # Verify the update
        updated_doc = alert_ref.get()
        logger.info(f"✅ Updated alert {alert_id} with investigation results")
        logger.info(f"📋 Final alert {alert_id} data: {updated_doc.to_dict()}")
        logger.info(f"   - Investigation ID: {investigation_id}")
        logger.info(f"   - Report URL: {report_url}")
        logger.info(f"   - Trace ID: {trace_id}")

        return True

    except Exception as e:
        logger.error(
            f"❌ Failed to update alert {alert_id} with investigation results: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False


@investigation_router.get("/debug/{alert_id}")
async def debug_alert_status(
    alert_id: str,
    user=Depends(verify_google_token)
):
    """Debug endpoint to check alert status in Firestore and test updates."""
    try:
        from google.cloud import firestore

        # Initialize Firestore
        db = firestore.Client()

        # Get the alert document
        alert_ref = db.collection('nyc_monitor_alerts').document(alert_id)
        doc = alert_ref.get()

        if not doc.exists:
            return {
                "alert_id": alert_id,
                "exists": False,
                "error": "Alert document does not exist"
            }

        alert_data = doc.to_dict()

        return {
            "alert_id": alert_id,
            "exists": True,
            "current_data": alert_data,
            "status": alert_data.get('status'),
            "report_url": alert_data.get('report_url'),
            "investigation_id": alert_data.get('investigation_id'),
            "trace_id": alert_data.get('trace_id'),
            "updated_at": alert_data.get('updated_at')
        }

    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return {
            "alert_id": alert_id,
            "error": str(e)
        }


@investigation_router.post("/debug/{alert_id}/test-update")
async def test_alert_update(
    alert_id: str,
    user=Depends(verify_google_token)
):
    """Test endpoint to manually trigger alert status updates."""
    try:
        # Test updating to investigating
        logger.info(f"🧪 Testing update alert {alert_id} to investigating")
        success1 = update_alert_status_to_investigating(alert_id)

        # Test updating to resolved with dummy data
        logger.info(f"🧪 Testing update alert {alert_id} to resolved")
        success2 = update_alert_with_investigation_results(
            alert_id=alert_id,
            investigation_id="test_investigation_123",
            report_url="https://docs.google.com/presentation/d/test_presentation_id/edit",
            trace_id="test_trace_123"
        )

        return {
            "alert_id": alert_id,
            "investigating_update": success1,
            "resolved_update": success2,
            "message": "Check logs for detailed output"
        }

    except Exception as e:
        logger.error(f"Test update error: {e}")
        return {
            "alert_id": alert_id,
            "error": str(e)
        }
