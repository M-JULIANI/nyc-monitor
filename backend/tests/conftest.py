"""
Pytest configuration and shared fixtures for RAG backend tests.
"""

import pytest
import os
from unittest.mock import Mock, patch
from typing import Dict, Any

from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables and initialize configuration."""
    test_env = {
        "ENV": "test",
        "GOOGLE_CLIENT_ID": "test-google-client-id",
        "RAG_CORPUS": "test-corpus",
        "INVESTIGATION_APPROACH": "simple",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1"
    }

    with patch.dict(os.environ, test_env):
        # Initialize configuration for tests
        from rag.config import initialize_config
        initialize_config()
        yield


@pytest.fixture
def test_config():
    """Create a test configuration with safe defaults."""
    from rag.config import Config
    return Config()


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    from rag.config import Config
    config = Mock(spec=Config)
    config.ENV = "test"
    config.GOOGLE_CLIENT_ID = "test-google-client-id"
    config.RAG_CORPUS = "test-corpus"
    config.INVESTIGATION_APPROACH = "simple"
    config.GOOGLE_CLOUD_PROJECT = "test-project"
    config.GOOGLE_CLOUD_LOCATION = "us-central1"
    config.AGENT_ENGINE_ID = "test-agent-engine"
    config.is_production = False
    config.is_development = False
    return config


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from rag.main import app
    return TestClient(app)


@pytest.fixture
def mock_google_token_verify():
    """Mock Google token verification to return a test user."""
    with patch('rag.auth.auth.id_token.verify_oauth2_token') as mock_verify:
        mock_verify.return_value = {
            "sub": "test-user-id",
            "email": "test@example.com",
            "name": "Test User"
        }
        yield mock_verify


@pytest.fixture
def mock_user():
    """Mock authenticated user for testing."""
    return {
        "user_id": "test-user-id",
        "email": "test@example.com",
        "name": "Test User"
    }


@pytest.fixture
def sample_alert_data():
    """Sample alert data for investigation tests."""
    return {
        "alert_id": "test-alert-123",
        "severity": 3,
        "event_type": "traffic_incident",
        "location": "Manhattan, NY",
        "summary": "Major traffic incident reported on Broadway",
        "timestamp": "2024-01-15T10:30:00Z",
        "sources": ["reddit", "twitter"]
    }


@pytest.fixture
def sample_chat_message():
    """Sample chat message for chat endpoint tests."""
    return {
        "text": "What are the latest traffic conditions in Manhattan?",
        "session_id": "test-session-123"
    }


@pytest.fixture
def mock_rag_corpus():
    """Mock RAG corpus for testing chat functionality."""
    with patch('rag.agents.chat_agent.create_rag_retrieval_tool') as mock_tool:
        mock_tool.return_value = Mock()
        yield mock_tool


@pytest.fixture
def mock_investigation_service():
    """Mock investigation service for testing."""
    with patch('rag.investigation_service_simple.investigate_alert_simple') as mock_investigate:
        mock_investigate.return_value = (
            "Investigation results", "test-investigation-id")
        yield mock_investigate


@pytest.fixture
def mock_state_manager():
    """Mock state manager for testing."""
    with patch('rag.investigation.state_manager.state_manager') as mock_manager:
        mock_state = Mock()
        mock_state.investigation_id = "test-investigation-id"
        mock_state.artifacts = ["artifact1", "artifact2"]
        mock_state.confidence_score = 0.85
        mock_state.is_complete = True
        mock_manager.get_investigation.return_value = mock_state
        yield mock_manager
