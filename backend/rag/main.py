from .auth import verify_google_token
from .endpoints import chat_router, investigation_router, auth_router, admin_router, alerts_router
from .config import initialize_config, get_config
from .exceptions import (
    APIError,
    api_error_handler,
    validation_error_handler,
    generic_exception_handler
)
from .middleware import configure_middleware, get_middleware_health
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.exceptions import RequestValidationError
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Only load .env file in development (not in production containers)
# Look for .env in the parent directory (project root)
env_file_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.getenv("ENV") != "production" and os.path.exists(env_file_path):
    load_dotenv(env_file_path)
    print("🔧 Development mode: Loaded environment variables from .env file")
    print(f"📁 .env file path: {os.path.abspath(env_file_path)}")
else:
    print("🚀 Production mode: Using container environment variables")
    print(
        f"📁 Looked for .env at: {os.path.abspath(env_file_path) if 'env_file_path' in locals() else 'not checked'}")

# Initialize configuration AFTER load_dotenv()
initialize_config()


# Debug logging for environment variables
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get configuration
config = get_config()

logger.info(f"FastAPI starting up...")
logger.info(f"Environment: {config.ENV}")
logger.info(f"GOOGLE_CLIENT_ID configured: {bool(config.GOOGLE_CLIENT_ID)}")
if config.GOOGLE_CLIENT_ID:
    logger.info(f"GOOGLE_CLIENT_ID preview: {config.GOOGLE_CLIENT_ID[:20]}...")
else:
    logger.error("GOOGLE_CLIENT_ID not found in environment!")

logger.info(f"RAG_CORPUS configured: {bool(config.RAG_CORPUS)}")
if config.RAG_CORPUS:
    logger.info(f"RAG_CORPUS: {config.RAG_CORPUS}")
else:
    logger.warning("RAG_CORPUS not found in environment!")

app = FastAPI(
    title="RAG Backend",
    description="Backend service for RAG (Retrieval-Augmented Generation) application using Vertex AI RAG Engine",
    version="0.1.0",
    root_path="/api"
)

# Configure all middleware in one place
configure_middleware(app)

# Centralized Exception Handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Include routers
app.include_router(chat_router)
app.include_router(investigation_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(alerts_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    """Enhanced health check with middleware status"""
    base_health = {"status": "healthy", "service": "rag-backend"}
    middleware_health = get_middleware_health()

    return {
        **base_health,
        "middleware": middleware_health,
        "timestamp": middleware_health["timestamp"]
    }


@app.get("/auth-test")
async def auth_test(user=Depends(verify_google_token)):
    """Test endpoint to verify authentication is working"""
    return {
        "status": "authenticated",
        "user": user,
        "message": "Authentication is working correctly!"
    }
