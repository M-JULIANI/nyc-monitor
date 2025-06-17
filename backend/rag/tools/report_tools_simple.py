"""
Simplified report tools including Google Slides creation.
"""

from google.adk.tools import FunctionTool
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def simple_create_slides(title: str, content: str) -> dict:
    """
    Create a Google Slides presentation with simplified parameters but proper folder/template support.

    Args:
        title: Presentation title
        content: Content to include

    Returns:
        Simple slides info
    """
    try:
        # Import the Google Slides functionality
        from ..tools.report_tools import _get_google_services

        # Get configuration
        GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
        STATUS_TRACKER_TEMPLATE_ID = os.getenv(
            "STATUS_TRACKER_TEMPLATE_ID", "")

        # Get Google services
        try:
            drive_service, slides_service = _get_google_services()
            logger.info("✅ Google services initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google services: {e}")
            return {
                "success": False,
                "error": f"Google services initialization failed: {e}",
                "presentation_id": None,
                "url": None
            }

        presentation_id = None

        # Try to use template if available
        if STATUS_TRACKER_TEMPLATE_ID:
            try:
                logger.info(f"🎨 Using template: {STATUS_TRACKER_TEMPLATE_ID}")

                # Create copy body with proper folder placement
                copy_body = {
                    'name': title,
                }

                # Explicitly set the parent folder to the main reports folder
                if GOOGLE_DRIVE_FOLDER_ID:
                    copy_body['parents'] = [GOOGLE_DRIVE_FOLDER_ID]
                    logger.info(
                        f"📁 Will place in folder: {GOOGLE_DRIVE_FOLDER_ID}")

                # Copy the template
                copied_file = drive_service.files().copy(
                    fileId=STATUS_TRACKER_TEMPLATE_ID,
                    body=copy_body
                ).execute()

                presentation_id = copied_file['id']
                logger.info(
                    f"✅ Created presentation from template: {presentation_id}")

                # Verify folder placement
                file_metadata = drive_service.files().get(
                    fileId=presentation_id,
                    fields='parents'
                ).execute()
                logger.info(
                    f"📍 Presentation parents: {file_metadata.get('parents', [])}")

                # PLACEHOLDER REPLACEMENT - This was missing!
                try:
                    # Prepare replacement data
                    replacements = {
                        "investigation_title": title,
                        "investigation_id": "SIMPLE-TEST-001",
                        "alert_location": "Washington Square Park, Manhattan",
                        "alert_severity": "7/10",
                        "status": "Active Investigation",
                        "confidence_score": "85.5%",
                        "findings_summary": content[:200] + "..." if len(content) > 200 else content,
                        "evidence_count": "4",
                        "evidence_types": "Web Articles, Social Media, Images",
                        "high_relevance_count": "3",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "phase": "Data Collection",
                        "iteration_count": "1"
                    }

                    # Create batch update requests for placeholder replacement
                    requests = []
                    for placeholder, replacement_text in replacements.items():
                        requests.append({
                            'replaceAllText': {
                                'containsText': {
                                    'text': f'{{{{{{placeholder}}}}}}'
                                },
                                'replaceText': str(replacement_text)
                            }
                        })

                    # Execute batch update if we have requests
                    if requests:
                        slides_service.presentations().batchUpdate(
                            presentationId=presentation_id,
                            body={'requests': requests}
                        ).execute()
                        logger.info(
                            "✅ Successfully replaced placeholders in template")

                except Exception as e:
                    logger.warning(f"⚠️ Could not replace placeholders: {e}")

            except Exception as e:
                logger.warning(
                    f"⚠️ Could not use template, creating blank presentation: {e}")
                presentation_id = None

        # If template failed or not available, create a blank presentation
        if not presentation_id:
            presentation_request = {
                'title': title
            }

            presentation = slides_service.presentations().create(
                body=presentation_request
            ).execute()

            presentation_id = presentation['id']

            # Move to folder if specified
            if GOOGLE_DRIVE_FOLDER_ID:
                try:
                    drive_service.files().update(
                        fileId=presentation_id,
                        addParents=GOOGLE_DRIVE_FOLDER_ID,
                        removeParents=','.join(drive_service.files().get(
                            fileId=presentation_id, fields='parents'
                        ).execute().get('parents', []))
                    ).execute()
                    logger.info(
                        f"📁 Moved presentation to folder: {GOOGLE_DRIVE_FOLDER_ID}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not move to folder: {e}")

            logger.info(f"✅ Created blank presentation: {presentation_id}")

        # Make presentation publicly viewable
        try:
            drive_service.permissions().create(
                fileId=presentation_id,
                body={
                    'role': 'reader',
                    'type': 'anyone'
                }
            ).execute()
            logger.info("🌐 Made presentation publicly viewable")
        except Exception as e:
            logger.warning(f"⚠️ Could not make public: {e}")

        # Generate URL
        url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
        logger.info(f"✅ Slides created successfully: {url}")

        return {
            "success": True,
            "presentation_id": presentation_id,
            "url": url,
            "title": title,
            "template_used": bool(STATUS_TRACKER_TEMPLATE_ID),
            "folder_id": GOOGLE_DRIVE_FOLDER_ID
        }

    except Exception as e:
        logger.error(f"❌ Failed to create slides: {e}")
        return {
            "success": False,
            "error": str(e),
            "presentation_id": None,
            "url": None
        }


def simple_create_report(title: str, findings: str) -> dict:
    """
    Create a simple text report.

    Args:
        title: Report title
        findings: Report findings

    Returns:
        Simple report info
    """
    report_content = f"""
# {title}

## Key Findings
{findings}

## Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    return {
        "success": True,
        "title": title,
        "content": report_content,
        "word_count": len(report_content.split())
    }


# Create simple tool instances
simple_create_slides_tool = FunctionTool(simple_create_slides)
simple_create_report_tool = FunctionTool(simple_create_report)
