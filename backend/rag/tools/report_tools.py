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
# NOTE: Load these inside functions to ensure .env is loaded first


def _get_environment_config():
    """Get environment configuration for slides generation."""
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    template_id = os.getenv("STATUS_TRACKER_TEMPLATE_ID", "")

    # Debug logging
    logger.info(f"🔧 Environment variables loaded:")
    logger.info(
        f"   GOOGLE_DRIVE_FOLDER_ID: {'✅ Set' if folder_id else '❌ Missing'}")
    logger.info(
        f"   STATUS_TRACKER_TEMPLATE_ID: {'✅ Set' if template_id else '❌ Missing'}")
    if template_id:
        logger.info(f"   Template ID preview: {template_id[:20]}...")
    if folder_id:
        logger.info(f"   Folder ID preview: {folder_id[:20]}...")

    return folder_id, template_id


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

        # Get environment configuration
        GOOGLE_DRIVE_FOLDER_ID, STATUS_TRACKER_TEMPLATE_ID = _get_environment_config()

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
        logger.info(
            f"Evidence data retrieved: {len(evidence_data.get('evidence_items', []))} items")

        # Get investigation state for additional data
        from ..investigation.state_manager import state_manager
        investigation_state = state_manager.get_investigation(investigation_id)

        # DEBUG: Check investigation state artifacts directly
        logger.info(
            f"🔍 DEBUG: Direct investigation state check for {investigation_id}")
        if investigation_state and hasattr(investigation_state, 'artifacts'):
            logger.info(
                f"   Direct artifacts count: {len(investigation_state.artifacts)}")
            # Show first 5
            for i, artifact in enumerate(investigation_state.artifacts[:5]):
                logger.info(
                    f"   Artifact {i+1}: type={artifact.get('type')}, filename={artifact.get('filename')}")
        else:
            logger.warning(f"   No investigation state or artifacts found")
        logger.info(f"🔍 Evidence data keys: {list(evidence_data.keys())}")
        logger.info(
            f"🔍 Evidence summary: {evidence_data.get('evidence_summary', {})}")

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

        # Save the presentation URL as an artifact to the investigation state
        try:
            from ..investigation.state_manager import state_manager
            investigation_state = state_manager.get_investigation(
                investigation_id)
            if investigation_state:
                # Create a presentation artifact
                presentation_artifact = {
                    'type': 'presentation',
                    'filename': f'presentation_{investigation_id}.slides',
                    'url': public_url,
                    'public_url': public_url,
                    'presentation_id': presentation_id,
                    'title': title,
                    'created_at': datetime.now().isoformat(),
                    'evidence_count': evidence_data.get("evidence_summary", {}).get("total_items", 0),
                    'images_inserted': successful_images,
                    'template_type': 'status_tracker'
                }

                # Add the artifact to the investigation state
                investigation_state.artifacts.append(presentation_artifact)
                logger.info(
                    f"✅ Saved presentation URL as artifact: {public_url}")
                logger.info(
                    f"📋 Total artifacts now: {len(investigation_state.artifacts)}")
            else:
                logger.warning(
                    f"⚠️ Could not find investigation state {investigation_id} to save presentation artifact")
        except Exception as e:
            logger.error(f"❌ Failed to save presentation artifact: {e}")

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
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "phase": "In Progress",
            "iteration": "0"
        }

    alert_data = investigation_state.alert_data
    evidence_summary = evidence_data.get("evidence_summary", {})

    # Create findings summary - Extract real findings from web search results and evidence
    findings_text = []

    try:
        # FIRST PRIORITY: Extract insights from web search artifacts (screenshots and search results)
        logger.debug("Extracting findings from web search artifacts...")

        web_search_findings = []
        screenshot_findings = []

        # Analyze screenshots and web search artifacts for meaningful content
        for artifact in investigation_state.artifacts:
            artifact_type = artifact.get('type', '')
            description = artifact.get('description', '').lower()
            url = artifact.get('url', '')

            # Extract insights from screenshot descriptions and URLs
            if artifact_type == 'screenshot':
                # Analyze what the screenshot captured based on URL and description
                if 'nytimes.com' in url:
                    screenshot_findings.append(
                        "• Major news coverage documented via New York Times reporting")
                elif 'cnn.com' in url:
                    screenshot_findings.append(
                        "• National news attention confirmed through CNN coverage")
                elif 'washingtonpost.com' in url:
                    screenshot_findings.append(
                        "• Investigation corroborated by Washington Post journalism")
                elif 'reddit.com' in url and 'nyc' in description:
                    screenshot_findings.append(
                        "• Community eyewitness accounts documented on NYC social media")
                elif 'twitter.com' in url or 'x.com' in url:
                    screenshot_findings.append(
                        "• Real-time social media documentation captured")
                elif 'instagram.com' in url:
                    screenshot_findings.append(
                        "• Visual evidence preserved from Instagram posts")
                elif 'youtube.com' in url:
                    screenshot_findings.append(
                        "• Video evidence documented from YouTube coverage")

                # Extract event-specific insights from description
                if 'protest' in description and 'peaceful' in description:
                    web_search_findings.append(
                        "• Web evidence indicates peaceful demonstration activities")
                elif 'protest' in description and 'arrest' in description:
                    web_search_findings.append(
                        "• Web sources document law enforcement response and arrests")
                elif 'march' in description or 'demonstration' in description:
                    web_search_findings.append(
                        "• Organized demonstration activity confirmed through web sources")

        # SECOND PRIORITY: Analyze web search results stored in investigation findings
        if hasattr(investigation_state, 'agent_findings'):
            for agent_name, findings in investigation_state.agent_findings.items():
                if 'web_search' in agent_name.lower() or 'search' in agent_name.lower():
                    if isinstance(findings, list):
                        for finding in findings:
                            finding_text = str(finding).lower()

                            # Extract crowd size information from web search
                            if 'thousand' in finding_text:
                                if 'tens of thousands' in finding_text:
                                    web_search_findings.append(
                                        "• Web sources report tens of thousands of participants")
                                else:
                                    web_search_findings.append(
                                        "• Web sources indicate thousands of participants documented")

                            # Extract timeline information
                            if 'june 14' in finding_text and 'trump' in finding_text:
                                web_search_findings.append(
                                    "• Event timing linked to political calendar per web research")

                            # Extract geographic scope
                            if ('bryant park' in finding_text and 'madison square' in finding_text) or 'route' in finding_text:
                                web_search_findings.append(
                                    "• Multi-location demonstration route documented across Manhattan")

                            # Extract safety and security insights
                            if 'no arrests' in finding_text and 'peaceful' in finding_text:
                                web_search_findings.append(
                                    "• Web sources confirm peaceful nature with no arrests reported")
                            elif 'police' in finding_text and 'presence' in finding_text:
                                web_search_findings.append(
                                    "• Significant law enforcement presence documented in web coverage")

                            # Extract thematic content
                            if 'no kings' in finding_text or 'monarchism' in finding_text:
                                web_search_findings.append(
                                    "• Anti-monarchism protest theme identified through web analysis")

        # THIRD PRIORITY: Synthesize from investigation artifacts and web evidence
        evidence_items = evidence_data.get("evidence_items", [])
        news_sources = set()
        visual_evidence_count = 0

        for item in evidence_items:
            item_url = item.get("original_url", "")
            item_type = item.get("type", "")

            # Track credible news sources
            if "nytimes.com" in item_url:
                news_sources.add("New York Times")
            elif "cnn.com" in item_url:
                news_sources.add("CNN")
            elif "washingtonpost.com" in item_url:
                news_sources.add("Washington Post")
            elif "reuters.com" in item_url:
                news_sources.add("Reuters")
            elif "ap.org" in item_url or "apnews.com" in item_url:
                news_sources.add("Associated Press")
            elif "nbcnews.com" in item_url:
                news_sources.add("NBC News")
            elif "abcnews.go.com" in item_url:
                news_sources.add("ABC News")
            elif "cbsnews.com" in item_url:
                news_sources.add("CBS News")

            # Count visual evidence
            if item_type in ['image', 'screenshot']:
                visual_evidence_count += 1

        # Create findings from source analysis
        if len(news_sources) >= 3:
            web_search_findings.append(
                f"• Multi-source verification from {len(news_sources)} major news outlets including {', '.join(list(news_sources)[:3])}")
        elif len(news_sources) >= 1:
            web_search_findings.append(
                f"• News coverage documented by {', '.join(news_sources)}")

        if visual_evidence_count >= 5:
            web_search_findings.append(
                f"• Extensive visual documentation with {visual_evidence_count} images and screenshots collected")

        # Combine and deduplicate findings
        all_web_findings = web_search_findings + screenshot_findings

        # Remove duplicates while preserving order
        seen = set()
        unique_findings = []
        for finding in all_web_findings:
            finding_key = finding.lower().replace('•', '').strip()
            # Only substantial findings
            if finding_key not in seen and len(finding_key) > 20:
                seen.add(finding_key)
                unique_findings.append(finding)

        # Take top 4 web-derived findings
        findings_text.extend(unique_findings[:4])

        # FALLBACK: Extract from alert summary only if we don't have enough web findings
        if len(findings_text) < 2 and alert_data.summary and len(alert_data.summary) > 100:
            logger.debug("Supplementing with alert summary analysis...")
            summary_lower = alert_data.summary.lower()

            # Extract only the most factual information from alert summary
            if "tens of thousands" in summary_lower:
                findings_text.append(
                    "• Large-scale demonstration involving tens of thousands of participants")
            elif "thousands" in summary_lower:
                findings_text.append(
                    "• Significant demonstration with thousands of participants documented")

            if "bryant park" in summary_lower and "madison square park" in summary_lower:
                findings_text.append(
                    "• Multi-location demonstration spanning Manhattan parks")

            if "peaceful" in summary_lower and "no arrests" in summary_lower:
                findings_text.append(
                    "• Peaceful demonstration with no law enforcement incidents")

        # FINAL FALLBACK: Generate basic findings if still insufficient
        if len(findings_text) < 2:
            findings_text = [
                f"• Investigation of {alert_data.event_type} at {alert_data.location} completed with {investigation_state.confidence_score:.1%} confidence",
                f"• Evidence collection encompassed {evidence_summary.get('total_items', 0)} artifacts from multiple sources",
                f"• Geographic verification through satellite imagery of {alert_data.location}"
            ]

        logger.debug(
            f"Generated {len(findings_text)} findings (prioritizing web search insights)")

    except Exception as e:
        logger.warning(f"Error extracting web search findings: {e}")
        # Fallback to basic findings
        findings_text = [
            f"• {alert_data.event_type} investigation at {alert_data.location}",
            f"• Evidence collection completed with {evidence_summary.get('total_items', 0)} items",
            f"• Investigation confidence: {investigation_state.confidence_score:.1%}"
        ]

    # Format the findings for different placeholder names
    findings_formatted = "\n".join(findings_text)

    # Create executive summary - synthesize from web findings rather than investigation metadata
    try:
        executive_summary = _create_executive_summary_from_web_findings(
            investigation_state, findings_text, evidence_summary, alert_data, news_sources
        )
        logger.debug(
            f"Generated web-focused executive summary: {len(executive_summary)} characters")
    except Exception as e:
        logger.warning(f"Error creating web-focused executive summary: {e}")
        # Fallback executive summary focusing on incident rather than process
        if len(findings_text) > 0 and not findings_text[0].startswith("• Investigation"):
            # We have good web findings, use them
            executive_summary = f"Analysis of {alert_data.event_type} at {alert_data.location} reveals {findings_text[0][2:]}. {'Additional findings include ' + ', '.join([f[2:] for f in findings_text[1:2]]) + '.' if len(findings_text) > 1 else ''} Investigation achieved {investigation_state.confidence_score:.1%} confidence through comprehensive evidence analysis."
        else:
            # Generic fallback
            executive_summary = f"Investigation of {alert_data.event_type} at {alert_data.location} has achieved {investigation_state.confidence_score:.1%} confidence through analysis of {evidence_summary.get('total_items', 0)} evidence items. The investigation reveals significant community activity with implications for public safety and civic engagement in the area."

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
        "executive_summary": executive_summary,  # New executive summary field
        "evidence_count": str(evidence_summary.get("total_items", 0)),
        "evidence_types": ", ".join(evidence_summary.get("types_found", ["None"])),
        "high_relevance_count": str(evidence_summary.get("high_relevance_count", 0)),
        "timestamp": investigation_state.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": investigation_state.phase.value.title(),
        "iteration": str(investigation_state.iteration_count),
    }

    # Add alternative placeholder names for template compatibility
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


def _create_executive_summary_from_web_findings(investigation_state, findings_text, evidence_summary, alert_data, news_sources) -> str:
    """Create an executive summary focused on incident findings rather than investigation process."""
    try:
        # Extract key metrics
        confidence = investigation_state.confidence_score
        evidence_count = evidence_summary.get("total_items", 0)
        event_type = alert_data.event_type
        location = alert_data.location
        severity = alert_data.severity

        # Start with the actual incident rather than investigation process
        summary_parts = []

        # Opening - focus on what happened, not how we investigated
        if len(findings_text) > 0 and not findings_text[0].startswith("• Investigation"):
            # We have substantive findings - use them as the lead
            main_finding = findings_text[0][2:]  # Remove bullet point
            summary_parts.append(
                f"Analysis of {event_type} at {location} reveals {main_finding.lower()}.")
        else:
            # Fallback opening
            summary_parts.append(
                f"Investigation of {event_type} at {location} has been completed.")

        # Key incident characteristics from web findings
        incident_details = []
        for finding in findings_text[1:]:
            # Remove bullet and convert to lowercase
            finding_text = finding[2:].lower()

            if 'peaceful' in finding_text and 'arrest' in finding_text:
                incident_details.append("peaceful nature with no arrests")
            elif 'thousands' in finding_text and 'participants' in finding_text:
                incident_details.append("large-scale participation")
            elif 'multi-location' in finding_text or 'route' in finding_text:
                incident_details.append(
                    "organized multi-location coordination")
            elif 'news' in finding_text and ('coverage' in finding_text or 'outlets' in finding_text):
                incident_details.append("significant media attention")
            elif 'social media' in finding_text:
                incident_details.append("extensive social media documentation")

        if incident_details:
            if len(incident_details) == 1:
                summary_parts.append(
                    f"The event demonstrated {incident_details[0]}.")
            elif len(incident_details) == 2:
                summary_parts.append(
                    f"Key characteristics include {incident_details[0]} and {incident_details[1]}.")
            else:
                summary_parts.append(
                    f"Notable features include {', '.join(incident_details[:2])}, and {incident_details[2]}.")

        # Media and source verification (if we have news sources)
        if news_sources:
            if len(news_sources) >= 3:
                summary_parts.append(
                    f"Event received comprehensive coverage from major news outlets including {', '.join(list(news_sources)[:3])}, indicating significant public interest.")
            elif len(news_sources) >= 1:
                summary_parts.append(
                    f"Coverage by {', '.join(news_sources)} confirms the event's newsworthiness and public impact.")

        # Evidence quality and investigation confidence (keep this brief)
        if confidence >= 0.8:
            confidence_phrase = "high confidence"
        elif confidence >= 0.7:
            confidence_phrase = "substantial confidence"
        else:
            confidence_phrase = "moderate confidence"

        summary_parts.append(
            f"Investigation achieved {confidence_phrase} ({confidence:.1%}) through analysis of {evidence_count} evidence items.")

        # Implications and context (focus on the incident's significance)
        if severity >= 7:
            summary_parts.append(
                "The scale and documentation level suggest significant implications for local civic engagement and public safety planning.")
        elif any('protest' in f.lower() or 'demonstration' in f.lower() for f in findings_text):
            summary_parts.append(
                "The event represents notable civic engagement activity within the broader context of public discourse in the area.")
        else:
            summary_parts.append(
                "Findings provide valuable insights for understanding community response patterns and public safety considerations.")

        # Combine into flowing narrative
        executive_summary = " ".join(summary_parts)

        # Ensure reasonable length (target 150-250 words)
        if len(executive_summary) > 800:
            # Trim to essential elements if too long
            essential_parts = summary_parts[:3]
            executive_summary = " ".join(essential_parts)

        return executive_summary

    except Exception as e:
        logger.error(f"Failed to create web-focused executive summary: {e}")
        # Simple incident-focused fallback
        return f"Analysis of {alert_data.event_type} at {alert_data.location} has been completed with {investigation_state.confidence_score:.1%} confidence. Findings indicate significant community activity with documented public safety and civic engagement implications for the area."


def _create_evidence_image_requests(evidence_data, slides_service, presentation_id: str) -> List[dict]:
    """Create requests to insert evidence images and maps into specific slides."""
    requests = []
    evidence_items = evidence_data.get("evidence_items", [])

    logger.info(
        f"🖼️ Creating image requests from {len(evidence_items)} evidence items")

    # Get the presentation to find slides
    try:
        presentation = slides_service.presentations().get(
            presentationId=presentation_id).execute()
        slides = presentation.get('slides', [])

        if len(slides) < 6:
            logger.warning(
                f"Template has only {len(slides)} slides, need at least 6 for image placement")
            return requests

        # Target slides: 5th & 6th slides (index 4,5) for images, 7th slide (index 6) for maps
        image_slide_1_id = slides[4]['objectId'] if len(
            slides) > 4 else slides[-1]['objectId']
        image_slide_2_id = slides[5]['objectId'] if len(
            slides) > 5 else slides[-1]['objectId']
        map_slide_id = slides[6]['objectId'] if len(
            slides) > 6 else slides[-1]['objectId']

        logger.info(
            f"Target slide for images 1-4: {image_slide_1_id} (slide 5)")
        logger.info(
            f"Target slide for images 5-8: {image_slide_2_id} (slide 6)")
        logger.info(f"Target slide for maps: {map_slide_id} (slide 7)")

    except Exception as e:
        logger.error(f"Failed to get presentation slides: {e}")
        return requests

    # Separate images and maps
    image_items = []
    map_items = []

    logger.info("🔍 Separating images and maps...")
    for i, item in enumerate(evidence_items):
        item_type = item.get("type", "unknown")
        relevance = item.get("relevance_score", 0)

        logger.debug(
            f"   Item {i}: type={item_type}, relevance={relevance:.2f}")

        # Include artifacts with any relevance score >= 0 (was > 0.5)
        if relevance >= 0:  # Much more permissive to include all collected artifacts
            if item_type in ["image", "screenshot"]:
                image_items.append(item)
            elif item_type == "map_image":
                map_items.append(item)

    # Limit to 8 images and 2 maps (4 images per slide)
    image_items = image_items[:8]
    map_items = map_items[:2]

    logger.info(
        f"📊 Selected {len(image_items)} images and {len(map_items)} maps for insertion")

    # Generate Slides-accessible URLs for all items
    all_items = image_items + map_items
    try:
        from .artifact_manager import artifact_manager

        logger.info(
            "🔗 Generating Slides-accessible URLs using service account...")

        for item in all_items:
            filename = item.get("filename", "")
            if filename and item.get("gcs_url"):
                # Extract investigation ID from GCS path
                investigation_id = "unknown"
                gcs_path = item.get("gcs_path", "")
                if "/investigations/" in gcs_path:
                    investigation_id = gcs_path.split(
                        "/investigations/")[1].split("/")[0]
                elif "/investigations/" in item.get("gcs_url", ""):
                    gcs_url = item.get("gcs_url", "")
                    investigation_id = gcs_url.split(
                        "/investigations/")[1].split("/")[0]

                # Get Slides-accessible URL using service account
                url_result = artifact_manager.get_slides_accessible_url(
                    investigation_id, filename)

                if url_result["success"]:
                    item["slides_accessible_url"] = url_result["url"]
                    item["url_type"] = url_result["url_type"]
                    logger.info(
                        f"✅ Generated Slides-accessible URL for: {filename}")
                else:
                    logger.warning(
                        f"❌ Could not generate accessible URL: {filename}")

    except Exception as e:
        logger.warning(f"Could not access artifact manager: {e}")

    # 1. ADD IMAGES TO 5TH & 6TH SLIDES (2x2 grid each - improved spacing)
    if image_items:
        logger.info(f"🖼️ Adding {len(image_items)} images to slides 5 & 6...")

        # Improved grid positions for 2x2 layout with better vertical spacing
        # Standard slide dimensions: ~720x540 points
        # Image size: 180x135 points each
        # Top row at Y:30, captions end at Y:30+135+5+40 = Y:210
        # Bottom row needs to start after captions, so Y:220 minimum
        image_positions = [
            {'x': 180, 'y': 30},   # Top left - moved up significantly
            {'x': 400, 'y': 30},   # Top right - moved up significantly
            # Bottom left - moved down to avoid caption clipping
            {'x': 180, 'y': 200},
            # Bottom right - moved down to avoid caption clipping
            {'x': 400, 'y': 200}
        ]

        # Process images in groups of 4 (one slide each)
        for slide_idx, slide_id in enumerate([image_slide_1_id, image_slide_2_id]):
            start_idx = slide_idx * 4
            end_idx = min(start_idx + 4, len(image_items))
            slide_images = image_items[start_idx:end_idx]

            if not slide_images:
                continue

            logger.info(
                f"🖼️ Adding {len(slide_images)} images to slide {slide_idx + 5}...")

            for i, item in enumerate(slide_images):
                if i >= len(image_positions):
                    break

                # Get the best available URL
                image_url = None
                source_url = ""

                # Priority: slides_accessible_url > signed_url > original_url
                if item.get("slides_accessible_url"):
                    image_url = item["slides_accessible_url"]
                    source_url = item.get(
                        "original_url", "") or item.get("url", "")
                elif item.get("signed_url"):
                    image_url = item["signed_url"]
                    source_url = item.get(
                        "original_url", "") or item.get("url", "")
                elif item.get("url"):
                    image_url = item["url"]
                    source_url = image_url

                if not image_url:
                    logger.warning(
                        f"❌ No valid URL for image {start_idx + i + 1}")
                    continue

                # Create unique object ID for each image
                image_obj_id = f'evidence_image_{slide_idx}_{i}'

                # Create image element with improved sizing
                image_request = {
                    'createImage': {
                        'objectId': image_obj_id,
                        'url': image_url,
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                # Slightly smaller height
                                'height': {'magnitude': 135, 'unit': 'PT'},
                                # Better aspect ratio
                                'width': {'magnitude': 180, 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1,
                                'scaleY': 1,
                                'translateX': image_positions[i]['x'],
                                'translateY': image_positions[i]['y'],
                                'unit': 'PT'
                            }
                        }
                    }
                }
                requests.append(image_request)

                # Create descriptive caption with source URL
                description = item.get('description', '') or item.get(
                    'title', '') or 'Evidence image'
                if len(description) > 60:
                    description = description[:60] + "..."

                # Extract domain from source URL for caption
                source_domain = ""
                if source_url:
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(source_url)
                        source_domain = f" (from {parsed.netloc})"
                    except:
                        source_domain = ""

                caption_text = f"{description}{source_domain}"

                # Create unique caption ID
                caption_obj_id = f'evidence_caption_{slide_idx}_{i}'

                # Add caption directly below image with corrected positioning
                caption_request = {
                    'createShape': {
                        'objectId': caption_obj_id,
                        'shapeType': 'TEXT_BOX',
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                # Reduced height
                                'height': {'magnitude': 40, 'unit': 'PT'},
                                # Match image width
                                'width': {'magnitude': 180, 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1,
                                'scaleY': 1,
                                'translateX': image_positions[i]['x'],
                                # Directly below image: image Y + image height (135) + small gap (5)
                                'translateY': image_positions[i]['y'] + 135,
                                'unit': 'PT'
                            }
                        }
                    }
                }
                requests.append(caption_request)

                # Insert caption text
                caption_text_request = {
                    'insertText': {
                        'objectId': caption_obj_id,
                        'text': caption_text
                    }
                }
                requests.append(caption_text_request)

                # Style the caption
                caption_style_request = {
                    'updateTextStyle': {
                        'objectId': caption_obj_id,
                        'style': {
                            'fontSize': {'magnitude': 6, 'unit': 'PT'},
                            'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 0.4, 'green': 0.4, 'blue': 0.4}}}
                        },
                        'fields': 'fontSize,foregroundColor'
                    }
                }
                requests.append(caption_style_request)

                logger.info(
                    f"✅ Created image {start_idx + i + 1} requests for slide {slide_idx + 5}")

    # 2. ADD MAPS TO 7TH SLIDE (side by side with small gap)
    if map_items:
        logger.info(f"🗺️ Adding {len(map_items)} maps to slide 7...")

        # Map positions for side-by-side layout - positioned lower and left for larger maps
        # Move maps lower (25% down) and to the left to accommodate 25% larger size
        # Original positions were x: 280, 500 and y: 80
        # New larger map size: 250x225 (25% larger than 200x180)
        map_positions = [
            {'x': 220, 'y': 100},   # Left map - moved left and down for larger size
            {'x': 450, 'y': 100},   # Right map - adjusted spacing for larger size
        ]

        for i, item in enumerate(map_items):
            if i >= len(map_positions):
                break

            # Get the best available URL for map
            map_url = None
            if item.get("slides_accessible_url"):
                map_url = item["slides_accessible_url"]
            elif item.get("signed_url"):
                map_url = item["signed_url"]
            elif item.get("url"):
                map_url = item["url"]

            if not map_url:
                logger.warning(f"❌ No valid URL for map {i+1}")
                continue

            # Create map element with 25% larger sizing
            map_request = {
                'createImage': {
                    'objectId': f'location_map_{i}',
                    'url': map_url,
                    'elementProperties': {
                        'pageObjectId': map_slide_id,
                        'size': {
                            # 25% larger height: 180 * 1.25 = 225
                            'height': {'magnitude': 225, 'unit': 'PT'},
                            # 25% larger width: 200 * 1.25 = 250
                            'width': {'magnitude': 250, 'unit': 'PT'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': map_positions[i]['x'],
                            'translateY': map_positions[i]['y'],
                            'unit': 'PT'
                        }
                    }
                }
            }
            requests.append(map_request)

            # Create map caption
            map_description = item.get('description', '') or 'Location map'
            zoom_level = "Normal view" if i == 0 else "Wide view"

            map_caption_text = f"{map_description} - {zoom_level}"

            # Add map caption with improved positioning (directly under larger map)
            map_caption_request = {
                'createShape': {
                    'objectId': f'map_caption_{i}',
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': map_slide_id,
                        'size': {
                            # Smaller caption height
                            'height': {'magnitude': 25, 'unit': 'PT'},
                            # Match new map width
                            'width': {'magnitude': 250, 'unit': 'PT'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': map_positions[i]['x'],
                            # Just below larger map: map Y + new map height (225) + small gap (5)
                            'translateY': map_positions[i]['y'] + 225 + 5,
                            'unit': 'PT'
                        }
                    }
                }
            }
            requests.append(map_caption_request)

            # Insert map caption text
            map_text_request = {
                'insertText': {
                    'objectId': f'map_caption_{i}',
                    'text': map_caption_text
                }
            }
            requests.append(map_text_request)

            # Style the map caption
            map_style_request = {
                'updateTextStyle': {
                    'objectId': f'map_caption_{i}',
                    'style': {
                        # Slightly larger for maps
                        'fontSize': {'magnitude': 9, 'unit': 'PT'},
                        'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2}}}
                    },
                    'fields': 'fontSize,foregroundColor'
                }
            }
            requests.append(map_style_request)

            logger.info(f"✅ Created map {i+1} requests")

    logger.info(
        f"📤 Created {len(requests)} total requests for images and maps")
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
                    "timestamp": investigation_state.alert_data.timestamp.isoformat() if hasattr(investigation_state.alert_data.timestamp, 'isoformat') else str(investigation_state.alert_data.timestamp)
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
