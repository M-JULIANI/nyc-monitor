"""
Real integration tests that make actual API calls.
These tests require real credentials and should be run sparingly.

Run with: pytest -m real_integration
Skip with: pytest -m "not real_integration"
"""

import pytest
import os
from datetime import datetime


@pytest.mark.real_integration
@pytest.mark.skipif(
    not os.getenv("GOOGLE_MAPS_API_KEY"), 
    reason="Requires GOOGLE_MAPS_API_KEY environment variable"
)
class TestRealAPIIntegration:
    """Test actual API integrations with real external services."""

    def test_real_map_generation(self):
        """Test actual Google Maps API integration."""
        from rag.tools.map_tools import generate_location_map_func
        
        # This will make a real API call
        result = generate_location_map_func(
            investigation_id="real-test-investigation",
            location="Washington Square Park, Manhattan",
            zoom_level=16,
            map_type="satellite"
        )
        
        # Assert real response structure
        assert result["success"] is True
        assert "filename" in result
        assert "signed_url" in result
        # Check that we got a real image URL
        assert result["signed_url"].startswith("https://")

    @pytest.mark.skipif(
        not os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY"), 
        reason="Requires GOOGLE_CUSTOM_SEARCH_API_KEY"
    )
    def test_real_web_search(self):
        """Test actual web search API integration."""
        from rag.tools.research_tools import web_search_func
        
        # This will make real API calls
        result = web_search_func(
            query="Washington Square Park protest",
            source_types="news",
            max_results=3
        )
        
        # Assert real response structure
        assert result["success"] is True
        assert "results" in result
        assert len(result["results"]) <= 3
        
        # Check that we got real search results
        for search_result in result["results"]:
            assert "title" in search_result
            assert "url" in search_result
            assert search_result["url"].startswith("http")

    @pytest.mark.skipif(
        not all([
            os.getenv("GOOGLE_DRIVE_FOLDER_ID"),
            os.getenv("STATUS_TRACKER_TEMPLATE_ID"),
            os.getenv("GOOGLE_SLIDES_SERVICE_ACCOUNT_KEY_BASE64")
        ]), 
        reason="Requires Google Slides API credentials"
    )
    def test_real_presentation_creation(self):
        """Test actual Google Slides API integration."""
        # First create some test investigation state
        from rag.investigation.state_manager import AlertData, state_manager
        
        alert_data = AlertData(
            alert_id="real-test-alert",
            event_type="integration_test",
            location="Test Location",
            severity=5,
            summary="Real integration test",
            sources=["test"],
            timestamp=datetime.now()
        )
        
        investigation_state = state_manager.create_investigation(alert_data)
        investigation_id = investigation_state.investigation_id
        
        try:
            from rag.tools.report_tools import create_slides_presentation_func
            
            # This will make real Google Slides API calls
            result = create_slides_presentation_func(
                investigation_id=investigation_id,
                title="Real Integration Test Presentation"
            )
            
            # Assert real response structure
            assert result["success"] is True
            assert "url" in result
            # Check that we got a real Google Slides URL
            assert "docs.google.com/presentation" in result["url"]
            
        finally:
            # Clean up test investigation
            state_manager.delete_investigation(investigation_id)


@pytest.mark.real_integration
class TestRealWorkflowIntegration:
    """Test real end-to-end workflows that use actual APIs."""

    @pytest.mark.skipif(
        not all([
            os.getenv("GOOGLE_MAPS_API_KEY"),
            os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY"),
            os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        ]), 
        reason="Requires multiple API credentials"
    )
    def test_real_investigation_workflow(self):
        """Test a complete investigation workflow with real APIs."""
        from rag.investigation.state_manager import AlertData
        from rag.investigation_service_simple import investigate_alert_simple
        
        # Create a real alert
        alert_data = AlertData(
            alert_id="real-workflow-test",
            event_type="integration_test",
            location="Washington Square Park, Manhattan",
            severity=3,
            summary="Integration test for real API workflow",
            sources=["test"],
            timestamp=datetime.now()
        )
        
        # This will make real API calls through the investigation service
        result, investigation_id = investigate_alert_simple(alert_data)
        
        # Assert that we got real results
        assert result is not None
        assert investigation_id is not None
        
        # Verify that real artifacts were created
        from rag.investigation.state_manager import state_manager
        investigation_state = state_manager.get_investigation(investigation_id)
        
        if investigation_state:
            # Should have real artifacts from API calls
            assert len(investigation_state.artifacts) > 0
            
            # Clean up
            state_manager.delete_investigation(investigation_id)


# Custom pytest configuration for real integration tests
pytestmark = pytest.mark.real_integration 