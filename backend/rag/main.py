from .auth import verify_google_token
from .endpoints import chat_router, investigation_router, auth_router, admin_router, alerts_router
from .config import initialize_config, get_config
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import os
from dotenv import load_dotenv
import logging

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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nyc-monitor.app",
        "https://atlas-frontend-290750569862.us-central1.run.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    return {"status": "healthy", "service": "rag-backend"}


@app.get("/auth-test")
async def auth_test(user=Depends(verify_google_token)):
    """Test endpoint to verify authentication is working"""
    return {
        "status": "authenticated",
        "user": user,
        "message": "Authentication is working correctly!"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
