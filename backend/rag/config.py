"""
Central configuration management for the RAG backend.
This ensures environment variables are read once after load_dotenv() and reused everywhere.
"""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Central configuration class that reads environment variables once."""

    def __init__(self):
        # Core environment
        self.ENV: str = os.getenv("ENV", "development")

        # Authentication
        self.GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")

        # RAG and AI
        self.RAG_CORPUS: Optional[str] = os.getenv("RAG_CORPUS")
        self.INVESTIGATION_APPROACH: str = os.getenv(
            "INVESTIGATION_APPROACH", "adk")

        # Google Cloud
        self.GOOGLE_CLOUD_PROJECT: Optional[str] = os.getenv(
            "GOOGLE_CLOUD_PROJECT")
        self.GOOGLE_CLOUD_LOCATION: Optional[str] = os.getenv(
            "GOOGLE_CLOUD_LOCATION")

        # Agent Engine (for deployed ADK agent)
        self.AGENT_ENGINE_ID: Optional[str] = os.getenv("AGENT_ENGINE_ID")

        # Log configuration status
        self._log_config_status()

    def _log_config_status(self):
        """Log the configuration status for debugging."""
        logger.info("🔧 Configuration loaded:")
        logger.info(f"  ENV: {self.ENV}")
        logger.info(
            f"  GOOGLE_CLIENT_ID: {'✅ Set' if self.GOOGLE_CLIENT_ID else '❌ Missing'}")
        logger.info(
            f"  RAG_CORPUS: {'✅ Set' if self.RAG_CORPUS else '❌ Missing'}")
        logger.info(f"  INVESTIGATION_APPROACH: {self.INVESTIGATION_APPROACH}")
        logger.info(
            f"  GOOGLE_CLOUD_PROJECT: {'✅ Set' if self.GOOGLE_CLOUD_PROJECT else '❌ Missing'}")
        logger.info(
            f"  AGENT_ENGINE_ID: {'✅ Set' if self.AGENT_ENGINE_ID else '❌ Missing'}")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENV == "development"


# Global configuration instance - will be initialized after load_dotenv()
config: Optional[Config] = None


def initialize_config():
    """Initialize the global configuration. Call this after load_dotenv()."""
    global config
    config = Config()
    logger.info("✅ Global configuration initialized")


def get_config() -> Config:
    """Get the global configuration instance."""
    if config is None:
        raise RuntimeError(
            "Configuration not initialized. Call initialize_config() first.")
    return config
