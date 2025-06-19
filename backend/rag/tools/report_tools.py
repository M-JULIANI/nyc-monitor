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

            try:
                # Try to copy from template
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
                logger.info(
                    f"✅ Created presentation from template: {presentation_id}")

            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to copy from template {template_id}: {e}")
                logger.info("🔄 Falling back to blank presentation...")

                # Fall back to blank presentation
                presentation_body = {
                    'title': title
                }
                presentation = slides_service.presentations().create(
                    body=presentation_body).execute()
                presentation_id = presentation['presentationId']
                logger.info(
                    f"✅ Created blank presentation as fallback: {presentation_id}")
        else:
            # Create blank presentation if no template available
            logger.info(
                "📝 Creating blank presentation (no template specified)")
            presentation_body = {
                'title': title
            }
            presentation = slides_service.presentations().create(
                body=presentation_body).execute()
            presentation_id = presentation['presentationId']
            logger.info(f"✅ Created blank presentation: {presentation_id}")

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
        logger.info(
            f"🔧 Starting presentation population for investigation: {investigation_id}")

        # Get investigation evidence
        from .research_tools import get_investigation_evidence_func
        evidence_data = get_investigation_evidence_func(
            investigation_id, evidence_types)
        logger.debug(
            f"Evidence data retrieved: {len(evidence_data.get('evidence_items', []))} items")

        # Get investigation state for additional data
        from ..investigation.state_manager import state_manager
        investigation_state = state_manager.get_investigation(investigation_id)

        if not investigation_state:
            logger.error(
                f"❌ No investigation state found for ID: {investigation_id}")
            return {
                "success": False,
                "error": "Investigation state not found",
                "presentation_id": presentation_id,
                "summary": "Failed to find investigation data"
            }

        logger.info(
            f"✅ Investigation state found: Phase={investigation_state.phase}, Confidence={investigation_state.confidence_score}")
        logger.debug(
            f"Investigation findings count: {len(investigation_state.findings)}")

        # Prepare replacement data
        replacements = _prepare_replacement_data(
            investigation_state, evidence_data)

        logger.info(f"🎯 Prepared {len(replacements)} replacement mappings")
        logger.debug("Replacement data preview:")
        # Show first 10 for debugging
        for key, value in list(replacements.items())[:10]:
            logger.debug(
                f"   {key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")

        # Batch update presentation with text replacements
        requests = []

        # Replace text placeholders
        for placeholder, replacement_text in replacements.items():
            placeholder_pattern = f'{{{{{placeholder}}}}}'
            request = {
                'replaceAllText': {
                    'containsText': {
                        'text': placeholder_pattern
                    },
                    'replaceText': str(replacement_text)
                }
            }
            requests.append(request)
            logger.debug(
                f"Added replacement: {placeholder_pattern} -> {str(replacement_text)[:50]}{'...' if len(str(replacement_text)) > 50 else ''}")

        # Execute batch update
        if requests:
            logger.info(
                f"📤 Sending {len(requests)} replacement requests to Google Slides API")
            try:
                batch_result = slides_service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': requests}
                ).execute()

                replies = batch_result.get('replies', [])
                logger.info(
                    f"✅ Batch update completed successfully with {len(replies)} replies")

                # Check for any errors in replies
                for i, reply in enumerate(replies):
                    if 'error' in reply:
                        logger.error(
                            f"❌ Replacement {i} failed: {reply['error']}")
                    else:
                        logger.debug(f"✅ Replacement {i} successful")

            except Exception as e:
                logger.error(f"❌ Google Slides API batch update failed: {e}")
                return {
                    "success": False,
                    "error": f"Google Slides API error: {str(e)}",
                    "presentation_id": presentation_id,
                    "summary": "Failed to update presentation placeholders"
                }
        else:
            logger.warning("⚠️ No replacement requests generated")

        # Add evidence images (non-blocking - don't fail presentation if images fail)
        logger.info("🖼️ Adding evidence images...")
        evidence_requests = _create_evidence_image_requests(
            evidence_data, slides_service, presentation_id)

        image_insertion_success = False
        successful_images = 0
        failed_images = 0

        if evidence_requests:
            # Try to insert images individually to avoid one failure blocking all
            successful_requests = []

            # Group requests by image (each image has 4 requests: image + 3 caption parts)
            image_groups = []
            for i in range(0, len(evidence_requests), 4):
                group = evidence_requests[i:i+4]
                image_groups.append(group)

            logger.info(
                f"🎯 Attempting to insert {len(image_groups)} images individually...")

            for i, image_group in enumerate(image_groups):
                try:
                    # Try to insert this image group
                    slides_service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={'requests': image_group}
                    ).execute()
                    successful_requests.extend(image_group)
                    successful_images += 1
                    logger.info(f"✅ Successfully inserted image {i+1}")
                except Exception as e:
                    failed_images += 1
                    logger.warning(f"⚠️ Failed to insert image {i+1}: {e}")
                    # Continue with next image - don't let one failure block others
                    continue

            if successful_images > 0:
                image_insertion_success = True
                logger.info(
                    f"✅ Successfully inserted {successful_images}/{len(image_groups)} images")
            else:
                logger.warning(
                    f"❌ Failed to insert all {len(image_groups)} images")
        else:
            logger.info("📝 No evidence images to add")

        # ALWAYS continue to share presentation - don't let image failures block this
        logger.info("🌐 Sharing presentation publicly...")
        try:
            _share_presentation_publicly(drive_service, presentation_id)
            logger.info("✅ Successfully shared presentation publicly")
        except Exception as e:
            logger.warning(f"⚠️ Failed to share presentation publicly: {e}")
            # Continue anyway - presentation still exists

        # Generate public viewing URL
        public_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit?usp=sharing"

        logger.info(f"🎉 Presentation creation completed!")
        logger.info(f"   URL: {public_url}")
        logger.info(f"   Text replacements: {len(requests)} applied")
        logger.info(
            f"   Images: {successful_images} successful, {failed_images} failed")

        return {
            "success": True,
            "presentation_id": presentation_id,
            "title": title,
            "url": public_url,
            "investigation_id": investigation_id,
            "evidence_count": evidence_data.get("evidence_summary", {}).get("total_items", 0),
            "template_type": "status_tracker",
            "replacements_applied": len(requests),
            "images_inserted": successful_images,
            "images_failed": failed_images,
            "image_insertion_success": image_insertion_success,
            "summary": f"Successfully created presentation '{title}' with {len(requests)} placeholder replacements, {successful_images} images inserted ({failed_images} failed)"
        }

    except Exception as e:
        logger.error(f"❌ Failed to populate presentation: {e}")
        logger.exception("Full error details:")
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

    # Format the findings for different placeholder names
    findings_formatted = "\n".join(findings_text)

    # Prepare base replacements
    replacements = {
        "investigation_title": f"{alert_data.event_type} Investigation - {alert_data.location}",
        "investigation_id": investigation_state.investigation_id,
        "alert_location": alert_data.location,
        "alert_severity": f"{alert_data.severity}/10",
        "alert_summary": alert_data.summary,
        "status": investigation_state.phase.value.title(),
        "confidence_score": f"{investigation_state.confidence_score:.1%}",
        "findings_summary": findings_formatted,
        "evidence_count": str(evidence_summary.get("total_items", 0)),
        "evidence_types": ", ".join(evidence_summary.get("types_found", ["None"])),
        "high_relevance_count": str(evidence_summary.get("high_relevance_count", 0)),
        "timestamp": investigation_state.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": investigation_state.phase.value.title(),
        "iteration": str(investigation_state.iteration_count),
        # Image placeholder URLs (to be replaced with actual image insertions)
        "evidence_image_1": "{{EVIDENCE_IMAGE_1}}",
        "evidence_image_2": "{{EVIDENCE_IMAGE_2}}",
        "evidence_image_3": "{{EVIDENCE_IMAGE_3}}",
        "evidence_screenshot_1": "{{EVIDENCE_SCREENSHOT_1}}",
        "evidence_screenshot_2": "{{EVIDENCE_SCREENSHOT_2}}",
        "map_location": "{{MAP_LOCATION}}",
        "timeline_chart": "{{TIMELINE_CHART}}"
    }

    # Add alternative placeholder names for template compatibility
    # Based on the user's template export, these are the missing placeholders:
    replacements.update({
        # Template uses {{key_findings}} but we provide {{findings_summary}}
        "key_findings": findings_formatted,
        # Template uses {{stats}} but we provide {{status}}
        "stats": investigation_state.phase.value.title(),
        # Template uses {{iteration}} but we provide {{iteration_count}}
        "iteration": str(investigation_state.iteration_count),
        # Also provide iteration_count for backwards compatibility
        "iteration_count": str(investigation_state.iteration_count)
    })

    logger.debug(f"Prepared {len(replacements)} placeholder replacements")
    logger.debug(f"Replacement keys: {list(replacements.keys())}")

    return replacements


def _create_evidence_image_requests(evidence_data, slides_service, presentation_id: str) -> List[dict]:
    """Create requests to insert actual evidence images into presentation."""
    requests = []
    evidence_items = evidence_data.get("evidence_items", [])
    public_artifacts_to_cleanup = []  # Track artifacts made public for cleanup

    logger.info(
        f"🖼️ Creating image requests from {len(evidence_items)} evidence items")

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
        logger.info(f"Target slide for images: {target_slide_id}")

    except Exception as e:
        logger.error(f"Failed to get presentation slides: {e}")
        return requests

    # Add up to 4 high-relevance images (2x2 grid layout)
    # Prioritize images that have been saved to GCS with signed URLs
    image_items = []

    logger.info("🔍 Filtering evidence items for images...")
    for i, item in enumerate(evidence_items):
        item_type = item.get("type", "unknown")
        relevance = item.get("relevance_score", 0)

        logger.debug(
            f"   Item {i}: type={item_type}, relevance={relevance:.2f}")

        if item_type in ["image", "screenshot", "map_image"] and relevance > 0.7:
            # Log available URLs for debugging
            gcs_url = item.get("gcs_url", "")
            signed_url = item.get("signed_url", "")
            original_url = item.get("url", "") or item.get(
                "image_url", "") or item.get("original_url", "")
            saved_to_gcs = item.get("saved_to_gcs", False)

            logger.debug(f"      GCS URL: {gcs_url}")
            logger.debug(f"      Signed URL: {signed_url}")
            logger.debug(f"      Original URL: {original_url}")
            logger.debug(f"      Saved to GCS: {saved_to_gcs}")

            # Add all suitable items - we'll make them accessible later
            image_items.append(item)

    # Take top 4 images
    image_items = image_items[:4]
    logger.info(f"📊 Selected {len(image_items)} images for insertion")

    # Generate Slides-accessible URLs using service account credentials
    try:
        from .artifact_manager import artifact_manager

        logger.info(
            "🔗 Generating Slides-accessible URLs using service account...")

        for item in image_items:
            filename = item.get("filename", "")
            if filename and item.get("gcs_url"):
                # Extract investigation ID from item or GCS path
                investigation_id = "unknown"
                gcs_path = item.get("gcs_path", "")
                if "/investigations/" in gcs_path:
                    # Parse: artifacts/investigations/DEBUG-SLIDESHOW-001_20250619_211306/images/filename
                    investigation_id = gcs_path.split(
                        "/investigations/")[1].split("/")[0]
                elif "/investigations/" in item.get("gcs_url", ""):
                    # Try GCS URL: gs://bucket/artifacts/investigations/ID/type/filename
                    gcs_url = item.get("gcs_url", "")
                    investigation_id = gcs_url.split(
                        "/investigations/")[1].split("/")[0]

                logger.debug(
                    f"   Extracted investigation ID: {investigation_id} from {gcs_path or item.get('gcs_url', 'no-path')}")

                # Get Slides-accessible URL using service account
                url_result = artifact_manager.get_slides_accessible_url(
                    investigation_id, filename)

                if url_result["success"]:
                    # Update item with Slides-accessible URL
                    item["slides_accessible_url"] = url_result["url"]
                    item["url_type"] = url_result["url_type"]
                    logger.info(
                        f"✅ Generated Slides-accessible URL for: {filename} ({url_result['url_type']})")
                else:
                    logger.warning(
                        f"❌ Could not generate accessible URL: {filename} - {url_result.get('error')}")

    except Exception as e:
        logger.warning(f"Could not access artifact manager: {e}")

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

        # Determine which URL to use (prefer Slides-accessible URLs from service account)
        image_url = None
        url_type = "unknown"

        # Helper function to validate URL accessibility
        def validate_image_url(url, url_type_name):
            if not url or not url.startswith("http"):
                return False, f"Invalid URL format: {url}"

            try:
                import requests
                # Quick HEAD request to check accessibility
                response = requests.head(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    # Check content type if available
                    content_type = response.headers.get(
                        'content-type', '').lower()
                    if any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
                        return True, f"Valid {url_type_name} (HTTP {response.status_code})"
                    else:
                        return True, f"Valid {url_type_name} (HTTP {response.status_code}, content-type: {content_type})"
                else:
                    return False, f"HTTP {response.status_code} from {url_type_name}"
            except Exception as e:
                return False, f"Failed to validate {url_type_name}: {str(e)}"

        # Priority order: slides_accessible_url > signed_url > original_url
        candidate_urls = [
            (item.get("slides_accessible_url"), "slides_accessible_url",
             item.get("url_type", "slides_accessible_url")),
            (item.get("signed_url"), "signed_url", "GCS signed URL"),
            (item.get("url"), "url", "external URL"),
            (item.get("image_url"), "image_url", "image URL"),
            (item.get("original_url"), "original_url", "original URL")
        ]

        for candidate_url, field_name, type_name in candidate_urls:
            if candidate_url:
                is_valid, validation_msg = validate_image_url(
                    candidate_url, type_name)
                if is_valid:
                    image_url = candidate_url
                    url_type = type_name
                    logger.info(
                        f"✅ Using {type_name} for image {i+1}: {item.get('filename', 'unknown')} - {validation_msg}")
                    break
                else:
                    logger.warning(
                        f"❌ {type_name} failed validation for image {i+1}: {validation_msg}")

        if not image_url:
            logger.warning(
                f"❌ No valid URL found for evidence item {i+1} ({item.get('filename', 'unknown')})")
            # Skip this image but continue with others
            continue

        logger.info(
            f"🎯 Image {i+1}: {url_type} = {image_url[:100]}{'...' if len(image_url) > 100 else ''}")

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
                            'translateY': positions[i]['y'],
                            'unit': 'PT'
                        }
                    }
                }
            }
            requests.append(image_request)

            # Add caption below image
            caption_text = f"Evidence {i+1}: {item.get('description', item.get('title', 'Collected evidence'))[:30]}..."
            if item.get("saved_to_gcs"):
                caption_text += " [GCS]"

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
                            'translateY': positions[i]['y'] + 125,
                            'unit': 'PT'
                        }
                    }
                }
            }
            requests.append(caption_request)

            # Add caption text
            caption_text_request = {
                'insertText': {
                    'objectId': f'evidence_caption_{i}',
                    'text': caption_text
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

            logger.info(
                f"✅ Created 4 requests for image {i+1} using {url_type}")

        except Exception as e:
            logger.error(
                f"❌ Failed to create image request for item {i+1}: {e}")
            # Don't add this image's requests, but continue with others
            continue

    # Store cleanup info for later use
    if public_artifacts_to_cleanup:
        logger.info(
            f"📝 Will cleanup {len(public_artifacts_to_cleanup)} public artifacts after presentation creation")
        # You could store this in the presentation metadata or investigation state for later cleanup

    logger.info(
        f"📤 Created {len(requests)} total image requests for {len(image_items)} evidence items")
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
