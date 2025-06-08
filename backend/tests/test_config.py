"""
Unit tests for the configuration module.
Tests environment variable loading, config initialization, and validation.
"""

import pytest
import os
from unittest.mock import patch, Mock

from rag.config import Config, initialize_config, get_config


class TestConfig:
    """Test cases for the Config class."""

    def test_config_initialization_with_defaults(self):
        """Test that Config initializes with proper defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()

            assert config.ENV == "development"
            assert config.INVESTIGATION_APPROACH == "simple"
            assert config.GOOGLE_CLIENT_ID is None
            assert config.RAG_CORPUS is None
            assert not config.is_production
            assert config.is_development

    def test_config_initialization_with_env_vars(self):
        """Test that Config properly reads environment variables."""
        test_env = {
            "ENV": "production",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "RAG_CORPUS": "test-corpus",
            "INVESTIGATION_APPROACH": "adk",
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "GOOGLE_CLOUD_LOCATION": "us-west1",
            "AGENT_ENGINE_ID": "test-engine"
        }

        with patch.dict(os.environ, test_env):
            config = Config()

            assert config.ENV == "production"
            assert config.GOOGLE_CLIENT_ID == "test-client-id"
            assert config.RAG_CORPUS == "test-corpus"
            assert config.INVESTIGATION_APPROACH == "adk"
            assert config.GOOGLE_CLOUD_PROJECT == "test-project"
            assert config.GOOGLE_CLOUD_LOCATION == "us-west1"
            assert config.AGENT_ENGINE_ID == "test-engine"
            assert config.is_production
            assert not config.is_development

    def test_config_properties(self):
        """Test Config property methods."""
        with patch.dict(os.environ, {"ENV": "production"}):
            config = Config()
            assert config.is_production
            assert not config.is_development

        with patch.dict(os.environ, {"ENV": "development"}):
            config = Config()
            assert not config.is_production
            assert config.is_development

    @patch('rag.config.logger')
    def test_config_logs_status(self, mock_logger):
        """Test that Config logs its initialization status."""
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-id"}):
            Config()

            # Verify logging calls were made
            mock_logger.info.assert_called()
            assert any("Configuration loaded" in str(call)
                       for call in mock_logger.info.call_args_list)


class TestConfigGlobal:
    """Test cases for global configuration management."""

    def teardown_method(self):
        """Reset global config after each test."""
        import rag.config
        rag.config.config = None

    def test_initialize_config(self):
        """Test that initialize_config creates global config instance."""
        with patch.dict(os.environ, {"ENV": "test"}):
            initialize_config()
            config = get_config()

            assert config is not None
            assert isinstance(config, Config)
            assert config.ENV == "test"

    def test_get_config_before_initialization_raises_error(self):
        """Test that get_config raises error when called before initialization."""
        import rag.config
        rag.config.config = None

        with pytest.raises(RuntimeError, match="Configuration not initialized"):
            get_config()

    def test_get_config_returns_same_instance(self):
        """Test that get_config returns the same instance across calls."""
        with patch.dict(os.environ, {"ENV": "test"}):
            initialize_config()
            config1 = get_config()
            config2 = get_config()

            assert config1 is config2

    def test_reinitialize_config(self):
        """Test that config can be reinitialized with new values."""
        with patch.dict(os.environ, {"ENV": "development"}):
            initialize_config()
            config1 = get_config()
            assert config1.ENV == "development"

        with patch.dict(os.environ, {"ENV": "production"}):
            initialize_config()
            config2 = get_config()
            assert config2.ENV == "production"
            assert config1 is not config2


class TestConfigValidation:
    """Test cases for configuration validation."""

    def test_missing_critical_config_handling(self):
        """Test behavior when critical configuration is missing."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()

            # Should not raise errors, but should have None values
            assert config.GOOGLE_CLIENT_ID is None
            assert config.RAG_CORPUS is None
            assert config.GOOGLE_CLOUD_PROJECT is None

    def test_config_with_empty_strings(self):
        """Test configuration with empty string environment variables."""
        test_env = {
            "GOOGLE_CLIENT_ID": "",
            "RAG_CORPUS": "",
            "GOOGLE_CLOUD_PROJECT": ""
        }

        with patch.dict(os.environ, test_env):
            config = Config()

            # Empty strings should be treated as None for our use case
            assert config.GOOGLE_CLIENT_ID == ""
            assert config.RAG_CORPUS == ""
            assert config.GOOGLE_CLOUD_PROJECT == ""

    def test_investigation_approach_validation(self):
        """Test that investigation approach defaults correctly."""
        # Test default
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            assert config.INVESTIGATION_APPROACH == "simple"

        # Test explicit values
        with patch.dict(os.environ, {"INVESTIGATION_APPROACH": "adk"}):
            config = Config()
            assert config.INVESTIGATION_APPROACH == "adk"

        with patch.dict(os.environ, {"INVESTIGATION_APPROACH": "invalid"}):
            config = Config()
            # Config doesn't validate, just stores
            assert config.INVESTIGATION_APPROACH == "invalid"
