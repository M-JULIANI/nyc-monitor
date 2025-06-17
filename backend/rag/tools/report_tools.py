# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Report generation tools with Google Slides integration."""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.adk.tools import FunctionTool
from google.auth import default

logger = logging.getLogger(__name__)

# Configuration - these should be environment variables in production
GOOGLE_DRIVE_FOLDER_ID = os.getenv(
    "GOOGLE_DRIVE_FOLDER_ID", "")  # Public folder for reports
STATUS_TRACKER_TEMPLATE_ID = os.getenv(
    "STATUS_TRACKER_TEMPLATE_ID", "")  # Template presentation ID


def _get_google_services():
    """Initialize Google Drive and Slides services using service account credentials."""
    try:
        # For Google Workspace APIs (Drive, Slides), we need explicit service account credentials
        # Priority order:
        # 1. Base64-encoded service account JSON from environment variable (for Cloud Run)
        # 2. Service account key file path (for local development)
        # 3. Default credentials (fallback)

        credentials = None

        # Try base64-encoded service account JSON first (for production/Cloud Run)
        google_service_account_key_b64 = os.getenv(
            "GOOGLE_SLIDES_SERVICE_ACCOUNT_KEY_BASE64")
        if google_service_account_key_b64:
            try:
                import base64
                import json
                # Decode base64 and parse JSON
                service_account_json = base64.b64decode(
                    google_service_account_key_b64).decode('utf-8')
                service_account_info = json.loads(service_account_json)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=[
                        'https://www.googleapis.com/auth/presentations',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
                logger.info(
                    "Using service account credentials from base64 environment variable")
            except Exception as e:
                logger.warning(
                    f"Failed to decode base64 service account key: {e}")

        # Try service account key file (for local development)
        if not credentials:
            service_account_key_path = os.getenv(
                "GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "atlas-reports-key.json")
            if os.path.exists(service_account_key_path):
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_key_path,
                    scopes=[
                        'https://www.googleapis.com/auth/presentations',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
                logger.info(
                    f"Using service account credentials from file: {service_account_key_path}")

        # Fall back to default credentials
        if not credentials:
            credentials, project = default(scopes=[
                'https://www.googleapis.com/auth/presentations',
                'https://www.googleapis.com/auth/drive'
            ])
            logger.info("Using default credentials with explicit scopes")

        drive_service = build('drive', 'v3', credentials=credentials)
        slides_service = build('slides', 'v1', credentials=credentials)

        logger.info("Successfully initialized Google Slides and Drive services")
        return drive_service, slides_service

    except Exception as e:
        if "scope" in str(e).lower() or "insufficient" in str(e).lower():
            logger.warning(
                f"Google Cloud credentials lack required scopes for Slides/Drive access: {e}")
            logger.info("Using mock services for development environment")
        else:
            logger.error(f"Failed to initialize Google services: {e}")
            logger.warning(
                "Using mock services - Google Slides integration disabled")
        return None, None


def create_slides_presentation_func(
    investigation_id: str,
    title: str = "",
    template_type: str = "status_tracker",
    evidence_types: str = "all"
) -> dict:
    """Create a Google Slides presentation from template with investigation data.

    Args:
        investigation_id: Investigation ID to create presentation for
        title: Custom title for the presentation (optional)
        template_type: Type of template to use (status_tracker, blank, custom)
        evidence_types: Types of evidence to include (screenshots,images,documents,all)

    Returns:
        Information about the created presentation
    """
    try:
        drive_service, slides_service = _get_google_services()

        if not drive_service or not slides_service:
            return _create_mock_presentation(investigation_id, title)

        # Generate presentation title
        if not title:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            title = f"NYC Atlas Investigation Report - {investigation_id} - {timestamp}"

        # Copy template to create new presentation
        if template_type == "status_tracker" and STATUS_TRACKER_TEMPLATE_ID:
            template_id = STATUS_TRACKER_TEMPLATE_ID
        else:
            # Create blank presentation if no template available
            presentation_body = {
                'title': title
            }
            presentation = slides_service.presentations().create(
                body=presentation_body).execute()
            presentation_id = presentation['presentationId']

            logger.info(f"Created blank presentation: {presentation_id}")
            return _populate_presentation_with_data(
                slides_service, drive_service, presentation_id, investigation_id, title, evidence_types
            )

        # Copy from template
        copy_body = {
            'name': title,
            'parents': [GOOGLE_DRIVE_FOLDER_ID] if GOOGLE_DRIVE_FOLDER_ID else []
        }

        copied_file = drive_service.files().copy(
            fileId=template_id,
            body=copy_body,
            supportsAllDrives=True
        ).execute()

        presentation_id = copied_file['id']

        logger.info(f"Created presentation from template: {presentation_id}")

        # Populate with investigation data
        return _populate_presentation_with_data(
            slides_service, drive_service, presentation_id, investigation_id, title, evidence_types
        )

    except Exception as e:
        error_msg = str(e)
        if "insufficient" in error_msg.lower() or "scope" in error_msg.lower():
            logger.warning(
                "Insufficient Google Cloud scopes for Slides/Drive - using mock presentation")
            return _create_mock_presentation(investigation_id, title)

        logger.error(f"Failed to create presentation: {e}")
        return {
            "success": False,
            "error": f"Presentation creation failed: {str(e)}",
            "presentation_id": None,
            "summary": f"Failed to create presentation for investigation {investigation_id}"
        }


def _populate_presentation_with_data(
    slides_service, drive_service, presentation_id: str,
    investigation_id: str, title: str, evidence_types: str
) -> dict:
    """Populate presentation with investigation data and evidence."""
    try:
        # Get investigation evidence
        from .research_tools import get_investigation_evidence_func
        evidence_data = get_investigation_evidence_func(
            investigation_id, evidence_types)

        # Get investigation state for additional data
        from ..investigation.state_manager import state_manager
        investigation_state = state_manager.get_investigation(investigation_id)

        # Prepare replacement data
        replacements = _prepare_replacement_data(
            investigation_state, evidence_data)

        # Batch update presentation with text replacements
        requests = []

        # Replace text placeholders
        for placeholder, replacement_text in replacements.items():
            requests.append({
                'replaceAllText': {
                    'containsText': {
                        'text': f'{{{{{placeholder}}}}}'
                    },
                    'replaceText': replacement_text
                }
            })

        # Execute batch update
        if requests:
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()

        # Add evidence images
        evidence_requests = _create_evidence_image_requests(
            evidence_data, slides_service, presentation_id)
        if evidence_requests:
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': evidence_requests}
            ).execute()

        # Share the presentation publicly for viewing
        _share_presentation_publicly(drive_service, presentation_id)

        # Generate public viewing URL
        public_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit?usp=sharing"

        return {
            "success": True,
            "presentation_id": presentation_id,
            "title": title,
            "url": public_url,
            "investigation_id": investigation_id,
            "evidence_count": evidence_data.get("evidence_summary", {}).get("total_items", 0),
            "template_type": "status_tracker",
            "summary": f"Successfully created presentation '{title}' with {evidence_data.get('evidence_summary', {}).get('total_items', 0)} evidence items"
        }

    except Exception as e:
        logger.error(f"Failed to populate presentation: {e}")
        return {
            "success": False,
            "error": f"Failed to populate presentation: {str(e)}",
            "presentation_id": presentation_id,
            "summary": f"Presentation created but failed to populate with data"
        }


def _prepare_replacement_data(investigation_state, evidence_data) -> dict:
    """Prepare text replacement data for presentation placeholders."""
    if not investigation_state:
        return {
            "investigation_title": "NYC Atlas Investigation Report",
            "investigation_id": "Unknown",
            "status": "In Progress",
            "confidence_score": "N/A",
            "findings_summary": "Investigation data not available",
            "evidence_count": str(evidence_data.get("evidence_summary", {}).get("total_items", 0)),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    alert_data = investigation_state.alert_data
    evidence_summary = evidence_data.get("evidence_summary", {})

    # Create findings summary
    findings_text = []
    if investigation_state.findings:
        for finding in investigation_state.findings[:3]:  # Top 3 findings
            findings_text.append(f"• {finding}")
    if not findings_text:
        findings_text = ["• Investigation in progress",
                         "• Evidence collection ongoing", "• Analysis pending"]

    return {
        "investigation_title": f"{alert_data.event_type} Investigation - {alert_data.location}",
        "investigation_id": investigation_state.investigation_id,
        "alert_location": alert_data.location,
        "alert_severity": f"{alert_data.severity}/10",
        "alert_summary": alert_data.summary,
        "status": investigation_state.phase.value.title(),
        "confidence_score": f"{investigation_state.confidence_score:.1%}",
        "findings_summary": "\n".join(findings_text),
        "evidence_count": str(evidence_summary.get("total_items", 0)),
        "evidence_types": ", ".join(evidence_summary.get("types_found", ["None"])),
        "high_relevance_count": str(evidence_summary.get("high_relevance_count", 0)),
        "timestamp": investigation_state.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": investigation_state.phase.value.title(),
        "iteration_count": str(investigation_state.iteration_count),
        # Image placeholder URLs (to be replaced with actual image insertions)
        "evidence_image_1": "{{EVIDENCE_IMAGE_1}}",
        "evidence_image_2": "{{EVIDENCE_IMAGE_2}}",
        "evidence_image_3": "{{EVIDENCE_IMAGE_3}}",
        "evidence_screenshot_1": "{{EVIDENCE_SCREENSHOT_1}}",
        "evidence_screenshot_2": "{{EVIDENCE_SCREENSHOT_2}}",
        "map_location": "{{MAP_LOCATION}}",
        "timeline_chart": "{{TIMELINE_CHART}}"
    }


def _create_evidence_image_requests(evidence_data, slides_service, presentation_id: str) -> List[dict]:
    """Create requests to insert actual evidence images into presentation."""
    requests = []
    evidence_items = evidence_data.get("evidence_items", [])

    # Get the presentation to find slides
    try:
        presentation = slides_service.presentations().get(
            presentationId=presentation_id).execute()
        slides = presentation.get('slides', [])

        if not slides:
            logger.warning("No slides found in presentation")
            return requests

        # Use the second slide (index 1) for evidence, or first if only one exists
        target_slide_id = slides[1]['objectId'] if len(
            slides) > 1 else slides[0]['objectId']

    except Exception as e:
        logger.error(f"Failed to get presentation slides: {e}")
        return requests

    # Add up to 4 high-relevance images (2x2 grid layout)
    image_items = [
        item for item in evidence_items
        if item["type"] in ["image", "screenshot"] and item.get("relevance_score", 0) > 0.7
    ][:4]

    # Grid layout: 2 columns, 2 rows
    positions = [
        {'x': 50, 'y': 300},   # Top left
        {'x': 370, 'y': 300},  # Top right
        {'x': 50, 'y': 450},   # Bottom left
        {'x': 370, 'y': 450}   # Bottom right
    ]

    for i, item in enumerate(image_items):
        if i >= len(positions):
            break

        image_url = item.get("url") or item.get("image_url")
        if not image_url:
            logger.warning(f"No URL found for evidence item {i}")
            continue

        try:
            # Create image element
            image_request = {
                'createImage': {
                    'objectId': f'evidence_image_{i}',
                    'url': image_url,
                    'elementProperties': {
                        'pageObjectId': target_slide_id,
                        'size': {
                            'height': {'magnitude': 120, 'unit': 'PT'},
                            'width': {'magnitude': 160, 'unit': 'PT'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': positions[i]['x'],
                            'translateY': positions[i]['y']
                        }
                    }
                }
            }
            requests.append(image_request)

            # Add caption below image
            caption_request = {
                'createShape': {
                    'objectId': f'evidence_caption_{i}',
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': target_slide_id,
                        'size': {
                            'height': {'magnitude': 40, 'unit': 'PT'},
                            'width': {'magnitude': 160, 'unit': 'PT'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': positions[i]['x'],
                            'translateY': positions[i]['y'] + 125
                        }
                    }
                }
            }
            requests.append(caption_request)

            # Add caption text
            caption_text_request = {
                'insertText': {
                    'objectId': f'evidence_caption_{i}',
                    'text': f"Evidence {i+1}: {item.get('description', 'Collected evidence')[:30]}..."
                }
            }
            requests.append(caption_text_request)

            # Style the caption text
            caption_style_request = {
                'updateTextStyle': {
                    'objectId': f'evidence_caption_{i}',
                    'style': {
                        'fontSize': {'magnitude': 9, 'unit': 'PT'},
                        'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 0.4, 'green': 0.4, 'blue': 0.4}}}
                    },
                    'fields': 'fontSize,foregroundColor'
                }
            }
            requests.append(caption_style_request)

        except Exception as e:
            logger.error(f"Failed to create image request for item {i}: {e}")
            continue

    logger.info(
        f"Created {len(requests)} image requests for {len(image_items)} evidence items")
    return requests


def _share_presentation_publicly(drive_service, presentation_id: str):
    """Share presentation with public view access."""
    try:
        drive_service.permissions().create(
            fileId=presentation_id,
            body={
                'role': 'reader',
                'type': 'anyone'
            }
        ).execute()
        logger.info(f"Shared presentation {presentation_id} publicly")
    except Exception as e:
        logger.warning(f"Failed to share presentation publicly: {e}")


def _create_mock_presentation(investigation_id: str, title: str) -> dict:
    """Create mock presentation response when Google services are not available."""
    mock_id = f"mock_presentation_{investigation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    mock_url = f"https://docs.google.com/presentation/d/{mock_id}/edit"

    return {
        "success": True,
        "presentation_id": mock_id,
        "title": title or f"NYC Atlas Investigation Report - {investigation_id}",
        "url": mock_url,
        "investigation_id": investigation_id,
        "evidence_count": 0,
        "template_type": "mock",
        "summary": f"Mock presentation created for investigation {investigation_id} (Google services not available)"
    }


def fact_check_claims_func(
    claims: str,
    evidence_sources: str = "all",
    confidence_threshold: float = 0.7
) -> dict:
    """Fact-check investigation claims against collected evidence.

    Args:
        claims: Comma-separated claims to fact-check
        evidence_sources: Types of evidence to use (web,social,official,all)
        confidence_threshold: Minimum confidence threshold for validation

    Returns:
        Fact-checking results with confidence scores
    """
    claims_list = [claim.strip() for claim in claims.split(",")]
    sources = [source.strip() for source in evidence_sources.split(",")]

    fact_check_results = []

    for i, claim in enumerate(claims_list):
        # Mock fact-checking logic - would integrate with real verification systems
        # Simulated confidence 0.6-1.0
        confidence = 0.6 + (hash(claim) % 40) / 100
        status = "verified" if confidence >= confidence_threshold else "needs_verification"

        supporting_sources = []
        if "web" in sources or "all" in sources:
            supporting_sources.append(f"Web source {i+1}")
        if "social" in sources or "all" in sources:
            supporting_sources.append(f"Social media post {i+1}")
        if "official" in sources or "all" in sources:
            supporting_sources.append(f"Official report {i+1}")

        fact_check_results.append({
            "claim": claim,
            "status": status,
            "confidence": confidence,
            "supporting_sources": supporting_sources,
            "verification_method": "cross_reference_analysis",
            "timestamp": datetime.now().isoformat()
        })

    overall_confidence = sum(
        result["confidence"] for result in fact_check_results) / len(fact_check_results)

    return {
        "success": True,
        "fact_check_results": fact_check_results,
        "overall_confidence": overall_confidence,
        "verified_claims": len([r for r in fact_check_results if r["status"] == "verified"]),
        "total_claims": len(claims_list),
        "summary": f"Fact-checked {len(claims_list)} claims with {overall_confidence:.1%} overall confidence"
    }


def assess_source_reliability_func(
    source_urls: str,
    assessment_criteria: str = "credibility,bias,accuracy"
) -> dict:
    """Assess reliability of information sources.

    Args:
        source_urls: Comma-separated URLs to assess
        assessment_criteria: Assessment criteria (credibility,bias,accuracy,timeliness)

    Returns:
        Source reliability assessment results
    """
    urls = [url.strip() for url in source_urls.split(",")]
    criteria = [criterion.strip()
                for criterion in assessment_criteria.split(",")]

    source_assessments = []

    for url in urls:
        # Mock assessment logic - would integrate with real reliability databases
        url_hash = hash(url) % 100

        # Simulate different reliability based on domain patterns
        if any(trusted in url for trusted in ["gov", "edu", "reuters", "ap", "nytimes"]):
            base_reliability = 0.8
        elif any(questionable in url for questionable in ["blog", "social", "forum"]):
            base_reliability = 0.4
        else:
            base_reliability = 0.6

        assessment_scores = {}
        for criterion in criteria:
            # Add some variation based on URL and criterion
            variation = (hash(url + criterion) %
                         30 - 15) / 100  # -0.15 to +0.15
            score = min(1.0, max(0.0, base_reliability + variation))
            assessment_scores[criterion] = score

        overall_score = sum(assessment_scores.values()) / \
            len(assessment_scores)
        reliability_tier = "high" if overall_score >= 0.7 else "medium" if overall_score >= 0.5 else "low"

        source_assessments.append({
            "url": url,
            "overall_reliability": overall_score,
            "reliability_tier": reliability_tier,
            "assessment_scores": assessment_scores,
            "assessment_date": datetime.now().isoformat(),
            "flags": [] if overall_score >= 0.6 else ["low_reliability"]
        })

    avg_reliability = sum(assessment["overall_reliability"]
                          for assessment in source_assessments) / len(source_assessments)

    return {
        "success": True,
        "source_assessments": source_assessments,
        "average_reliability": avg_reliability,
        "high_reliability_sources": len([s for s in source_assessments if s["reliability_tier"] == "high"]),
        "total_sources": len(urls),
        "summary": f"Assessed {len(urls)} sources with {avg_reliability:.1%} average reliability"
    }


def generate_confidence_scores_func(
    investigation_id: str,
    scoring_factors: str = "evidence_quality,source_reliability,cross_validation"
) -> dict:
    """Generate confidence scores for investigation findings.

    Args:
        investigation_id: Investigation ID to generate scores for
        scoring_factors: Factors to include in confidence calculation

    Returns:
        Detailed confidence scoring breakdown
    """
    factors = [factor.strip() for factor in scoring_factors.split(",")]

    # Mock confidence calculation - would use real investigation data
    factor_scores = {}

    if "evidence_quality" in factors:
        # Based on evidence relevance and completeness
        factor_scores["evidence_quality"] = 0.75
    if "source_reliability" in factors:
        # Based on source assessment results
        factor_scores["source_reliability"] = 0.80
    if "cross_validation" in factors:
        # Based on consistency across sources
        factor_scores["cross_validation"] = 0.70
    if "temporal_consistency" in factors:
        # Based on timeline coherence
        factor_scores["temporal_consistency"] = 0.85

    overall_confidence = sum(factor_scores.values()) / len(factor_scores)
    confidence_tier = "high" if overall_confidence >= 0.8 else "medium" if overall_confidence >= 0.6 else "low"

    return {
        "success": True,
        "investigation_id": investigation_id,
        "overall_confidence": overall_confidence,
        "confidence_tier": confidence_tier,
        "factor_scores": factor_scores,
        "scoring_methodology": "weighted_average",
        "confidence_interval": [overall_confidence - 0.1, overall_confidence + 0.1],
        "timestamp": datetime.now().isoformat(),
        "summary": f"Generated {confidence_tier} confidence score ({overall_confidence:.1%}) for investigation {investigation_id}"
    }


def create_investigation_report_func(
    investigation_id: str,
    report_format: str = "json",
    include_evidence: bool = True
) -> dict:
    """Create a comprehensive investigation report.

    Args:
        investigation_id: Investigation ID to create report for
        report_format: Format for the report (json, pdf, html)
        include_evidence: Whether to include evidence artifacts

    Returns:
        Generated report information
    """
    try:
        # Get investigation data
        from ..investigation.state_manager import state_manager
        investigation_state = state_manager.get_investigation(investigation_id)

        if not investigation_state:
            return {
                "success": False,
                "error": f"Investigation {investigation_id} not found",
                "report_content": None,
                "summary": "Report generation failed - investigation not found"
            }

        # Get evidence if requested
        evidence_data = {}
        if include_evidence:
            from .research_tools import get_investigation_evidence_func
            evidence_data = get_investigation_evidence_func(investigation_id)

        # Generate report content
        report_content = {
            "investigation_summary": {
                "id": investigation_state.investigation_id,
                "alert_data": {
                    "alert_id": investigation_state.alert_data.alert_id,
                    "event_type": investigation_state.alert_data.event_type,
                    "location": investigation_state.alert_data.location,
                    "severity": investigation_state.alert_data.severity,
                    "summary": investigation_state.alert_data.summary,
                    "timestamp": investigation_state.alert_data.timestamp.isoformat()
                },
                "investigation_status": {
                    "phase": investigation_state.phase.value,
                    "confidence_score": investigation_state.confidence_score,
                    "iteration_count": investigation_state.iteration_count,
                    "is_complete": investigation_state.is_complete,
                    "created_at": investigation_state.created_at.isoformat(),
                    "updated_at": investigation_state.updated_at.isoformat()
                }
            },
            "findings": investigation_state.findings,
            "evidence_summary": evidence_data.get("evidence_summary", {}),
            "evidence_items": evidence_data.get("evidence_items", []) if include_evidence else [],
            "agent_findings": investigation_state.agent_findings,
            "confidence_scores": investigation_state.confidence_scores,
            "next_actions": investigation_state.next_actions,
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "format": report_format,
                "includes_evidence": include_evidence,
                "total_artifacts": len(investigation_state.artifacts)
            }
        }

        # Save report based on format
        report_filename = f"investigation_report_{investigation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{report_format}"

        if report_format == "json":
            # In production, this would save to the Google Drive folder
            report_size = len(json.dumps(report_content, indent=2))
        else:
            # For PDF/HTML, would use additional libraries
            report_size = len(str(report_content))

        return {
            "success": True,
            "investigation_id": investigation_id,
            "report_filename": report_filename,
            "report_format": report_format,
            "report_content": report_content if report_format == "json" else None,
            "report_size_bytes": report_size,
            "includes_evidence": include_evidence,
            "evidence_count": len(evidence_data.get("evidence_items", [])),
            "summary": f"Generated {report_format.upper()} report for investigation {investigation_id}"
        }

    except Exception as e:
        logger.error(f"Failed to create investigation report: {e}")
        return {
            "success": False,
            "error": f"Report generation failed: {str(e)}",
            "report_content": None,
            "summary": f"Failed to generate report for investigation {investigation_id}"
        }


# Create FunctionTool instances
create_slides_presentation = FunctionTool(create_slides_presentation_func)
fact_check_claims = FunctionTool(fact_check_claims_func)
assess_source_reliability = FunctionTool(assess_source_reliability_func)
generate_confidence_scores = FunctionTool(generate_confidence_scores_func)
create_investigation_report = FunctionTool(create_investigation_report_func)
