#!/usr/bin/env python3
"""
Standalone verification script for Google Slides placeholder replacement.
This helps debug placeholder issues without running the full investigation workflow.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
env_file_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_file_path):
    load_dotenv(env_file_path)
    print(f"✅ Loaded environment variables from {env_file_path}")
else:
    print(f"❌ .env file not found at {env_file_path}")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_template_placeholders():
    """Check what placeholders are in the template."""
    print("\n🔍 CHECKING TEMPLATE PLACEHOLDERS")
    print("=" * 50)

    try:
        from rag.tools.report_tools import _get_google_services

        # Get Google services
        drive_service, slides_service = _get_google_services()
        if not drive_service or not slides_service:
            print("❌ Google services not available")
            return False

        # Get template ID
        template_id = os.getenv("STATUS_TRACKER_TEMPLATE_ID", "")
        if not template_id:
            print("❌ STATUS_TRACKER_TEMPLATE_ID not set")
            return False

        print(f"📋 Using template: {template_id}")

        # Get the template presentation
        template = slides_service.presentations().get(
            presentationId=template_id).execute()

        print(f"✅ Template found: {template.get('title', 'Unknown Title')}")

        # Extract all text from slides to find placeholders
        slides = template.get('slides', [])
        print(f"📄 Template has {len(slides)} slides")

        all_placeholders = set()

        for i, slide in enumerate(slides):
            print(f"\n🔍 Slide {i+1}:")

            # Check all page elements
            page_elements = slide.get('pageElements', [])
            for element in page_elements:
                if 'shape' in element and 'text' in element['shape']:
                    text_runs = element['shape']['text'].get(
                        'textElements', [])
                    for text_run in text_runs:
                        if 'textRun' in text_run:
                            text_content = text_run['textRun'].get(
                                'content', '')

                            # Find placeholders (text between double curly braces)
                            import re
                            placeholders = re.findall(
                                r'\{\{([^}]+)\}\}', text_content)
                            for placeholder in placeholders:
                                all_placeholders.add(placeholder)
                                print(
                                    f"   Found placeholder: {{{{{placeholder}}}}}")

                            # Also show some context
                            if '{{' in text_content:
                                print(
                                    f"   Context: {text_content.strip()[:100]}...")

        print(f"\n📊 SUMMARY:")
        print(f"   Total unique placeholders found: {len(all_placeholders)}")
        print(f"   Placeholders: {sorted(all_placeholders)}")

        return list(all_placeholders)

    except Exception as e:
        print(f"❌ Failed to check template: {e}")
        return False


def test_placeholder_replacement():
    """Test actual placeholder replacement with mock data."""
    print("\n🔧 TESTING PLACEHOLDER REPLACEMENT")
    print("=" * 50)

    try:
        from rag.tools.report_tools import _get_google_services

        # Get Google services
        drive_service, slides_service = _get_google_services()
        if not drive_service or not slides_service:
            print("❌ Google services not available")
            return False

        # Get configuration
        template_id = os.getenv("STATUS_TRACKER_TEMPLATE_ID", "")
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

        if not template_id:
            print("❌ STATUS_TRACKER_TEMPLATE_ID not set")
            return False

        print(f"📋 Creating test presentation from template: {template_id}")

        # Create a copy of the template
        copy_body = {
            'name': f'VERIFICATION TEST - {datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'parents': [folder_id] if folder_id else []
        }

        copied_file = drive_service.files().copy(
            fileId=template_id,
            body=copy_body
        ).execute()

        test_presentation_id = copied_file['id']
        print(f"✅ Created test presentation: {test_presentation_id}")

        # Prepare comprehensive test data
        test_replacements = {
            # Standard investigation data
            "investigation_title": "VERIFICATION TEST: Community Protest Investigation - Washington Square Park",
            "investigation_id": "VERIFY-TEST-001",
            "alert_location": "Washington Square Park, Manhattan",
            "alert_severity": "7/10",
            "alert_summary": "Test alert for verification of placeholder replacement system",
            "status": "Complete",
            "confidence_score": "92.5%",
            "findings_summary": "• Verification test finding 1\n• Verification test finding 2\n• Verification test finding 3",
            "evidence_count": "15",
            "evidence_types": "screenshots, social media, news articles",
            "high_relevance_count": "12",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "phase": "Complete",
            "iteration_count": "2",

            # Template-specific placeholders (based on user's export)
            "key_findings": "• Housing concerns driving community action\n• Social media organizing detected\n• Community board involvement confirmed",
            "stats": "Investigation Complete",
            "iteration": "2"
        }

        print(f"📝 Preparing {len(test_replacements)} test replacements:")
        for key, value in test_replacements.items():
            print(
                f"   {key}: {str(value)[:60]}{'...' if len(str(value)) > 60 else ''}")

        # Create replacement requests
        requests = []
        for placeholder, replacement_text in test_replacements.items():
            placeholder_pattern = f"{{{{{placeholder}}}}}"
            request = {
                'replaceAllText': {
                    'containsText': {
                        'text': placeholder_pattern
                    },
                    'replaceText': str(replacement_text)
                }
            }
            requests.append(request)
            print(f"   Will replace: {placeholder_pattern}")

        # Execute replacements
        print(
            f"\n📤 Sending {len(requests)} replacement requests to Google Slides API...")
        batch_result = slides_service.presentations().batchUpdate(
            presentationId=test_presentation_id,
            body={'requests': requests}
        ).execute()

        replies = batch_result.get('replies', [])
        print(f"✅ Batch update completed with {len(replies)} replies")

        # Check for errors
        errors = 0
        for i, reply in enumerate(replies):
            if 'error' in reply:
                print(f"❌ Replacement {i} failed: {reply['error']}")
                errors += 1

        if errors == 0:
            print(f"🎉 All {len(replies)} replacements successful!")
        else:
            print(f"⚠️ {errors} replacements failed out of {len(replies)}")

        # Make it publicly viewable
        try:
            drive_service.permissions().create(
                fileId=test_presentation_id,
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()
        except Exception as e:
            print(f"⚠️ Could not make public: {e}")

        # Generate URL
        test_url = f"https://docs.google.com/presentation/d/{test_presentation_id}/edit"
        print(f"\n🎯 VERIFICATION PRESENTATION URL:")
        print(f"   {test_url}")
        print(f"\n📋 ACTION ITEMS:")
        print(f"   1. Open the URL above")
        print(f"   2. Check if placeholders were replaced with test data")
        print(f"   3. Compare with original template to see what's missing")
        print(f"   4. Delete the test presentation when done")

        return test_url

    except Exception as e:
        print(f"❌ Placeholder replacement test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main verification function."""
    print("🔍 GOOGLE SLIDES PLACEHOLDER VERIFICATION")
    print("=" * 60)
    print("This script helps debug placeholder replacement issues by:")
    print("  1. Checking what placeholders exist in your template")
    print("  2. Testing direct replacement with mock data")
    print("  3. Creating a test presentation you can inspect")
    print("=" * 60)

    # Step 1: Check template placeholders
    template_placeholders = check_template_placeholders()

    # Step 2: Test replacement
    if template_placeholders:
        test_url = test_placeholder_replacement()

        if test_url:
            print("\n" + "=" * 60)
            print("✅ VERIFICATION COMPLETE!")
            print(
                f"📋 Template placeholders found: {len(template_placeholders)}")
            print(f"🔗 Test presentation: {test_url}")
            print("\n💡 Next steps:")
            print("   • Compare the test presentation with original template")
            print("   • Identify which placeholders are still not replaced")
            print("   • Update the _prepare_replacement_data function accordingly")
        else:
            print("\n❌ VERIFICATION FAILED!")
            print("Check the error messages above for details.")
    else:
        print("\n❌ Could not check template placeholders")

    print("=" * 60)


if __name__ == "__main__":
    main()
