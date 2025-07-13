"""
Integration tests for the RAG backend system.
These tests verify end-to-end workflows and tool integrations.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Dict, Any


class TestToolIntegration:
    """Test individual tool integrations."""

    @pytest.mark.integration
    @patch('rag.tools.map_tools.generate_location_map_func')
    def test_map_generation_integration(self, mock_map_func):
        """Test map generation tool integration."""
        # Arrange
        mock_map_func.return_value = {
            "success": True,
            "filename": "test_map.png",
            "signed_url": "https://example.com/test_map.png"
        }
        
        from rag.tools.map_tools import generate_location_map_func
        
        # Act
        result = generate_location_map_func(
            investigation_id="test-investigation",
            location="Washington Square Park, Manhattan",
            zoom_level=16,
            map_type="satellite"
        )
        
        # Assert
        assert result["success"] is True
        assert "filename" in result
        mock_map_func.assert_called_once()

    @pytest.mark.integration
    @patch('rag.tools.research_tools.web_search_func')
    def test_web_search_integration(self, mock_search_func):
        """Test web search tool integration."""
        # Arrange
        mock_search_func.return_value = {
            "success": True,
            "results": [
                {"title": "Test Result", "url": "https://example.com", "snippet": "Test snippet"}
            ]
        }
        
        from rag.tools.research_tools import web_search_func
        
        # Act
        result = web_search_func(
            query="Washington Square Park protest",
            source_types="news",
            max_results=3
        )
        
        # Assert
        assert result["success"] is True
        assert "results" in result
        assert len(result["results"]) > 0
        mock_search_func.assert_called_once()

    @pytest.mark.integration
    @patch('rag.tools.report_tools.create_slides_presentation_func')
    def test_presentation_creation_integration(self, mock_slides_func):
        """Test presentation creation tool integration."""
        # Arrange
        mock_slides_func.return_value = {
            "success": True,
            "url": "https://docs.google.com/presentation/d/test",
            "evidence_count": 5,
            "images_inserted": 3
        }
        
        from rag.tools.report_tools import create_slides_presentation_func
        
        # Act
        result = create_slides_presentation_func(
            investigation_id="test-investigation",
            title="Test Investigation Report"
        )
        
        # Assert
        assert result["success"] is True
        assert "url" in result
        mock_slides_func.assert_called_once()


class TestInvestigationWorkflow:
    """Test complete investigation workflow integration."""

    @pytest.mark.integration
    @patch('rag.investigation_service_simple.investigate_alert_simple')
    def test_simple_investigation_workflow(self, mock_investigate):
        """Test simple investigation workflow."""
        # Arrange
        mock_investigate.return_value = (
            "Investigation completed successfully",
            "test-investigation-id"
        )
        
        from rag.investigation.state_manager import AlertData
        
        alert_data = AlertData(
            alert_id="test-alert",
            event_type="test_event",
            location="Test Location",
            severity=5,
            summary="Test investigation workflow",
            sources=["test_source"],
            timestamp=datetime.now()
        )
        
        # Act
        result, investigation_id = mock_investigate(alert_data)
        
        # Assert
        assert result is not None
        assert investigation_id == "test-investigation-id"
        mock_investigate.assert_called_once()

    @pytest.mark.integration
    @patch('rag.investigation.state_manager.state_manager')
    def test_investigation_state_management(self, mock_state_manager):
        """Test investigation state management."""
        # Arrange
        mock_state = Mock()
        mock_state.investigation_id = "test-investigation"
        mock_state.artifacts = ["artifact1", "artifact2"]
        mock_state.confidence_score = 0.85
        mock_state.phase = "completed"
        mock_state_manager.get_investigation.return_value = mock_state
        
        # Act
        investigation_state = mock_state_manager.get_investigation("test-investigation")
        
        # Assert
        assert investigation_state.investigation_id == "test-investigation"
        assert len(investigation_state.artifacts) == 2
        assert investigation_state.confidence_score == 0.85
        assert investigation_state.phase == "completed"

# Pytest markers for organization
pytestmark = pytest.mark.integration 