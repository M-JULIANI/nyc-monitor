"""
Early environment setup for the RAG backend.
This module loads environment variables BEFORE any other imports that might need them.
"""

import os
from dotenv import load_dotenv


def setup_environment():
    """Load environment variables from .env file if in development mode."""
    # Only load .env file in development (not in production containers)
    # Look for .env in the project root (two levels up from this file)
    env_file_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")

    if os.getenv("ENV") != "production" and os.path.exists(env_file_path):
        load_dotenv(env_file_path)
        print("🔧 Environment setup: Loaded environment variables from .env file")
        print(f"📁 .env file path: {os.path.abspath(env_file_path)}")

        # Verify critical environment variables
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if project:
            print(f"✅ GOOGLE_CLOUD_PROJECT: {project}")
        else:
            print("⚠️ GOOGLE_CLOUD_PROJECT not set in environment")

        return True
    else:
        print("🚀 Environment setup: Using container environment variables")
        return False


# Load environment variables immediately when this module is imported
setup_environment()
