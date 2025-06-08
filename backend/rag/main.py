from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import os

from .endpoints import chat_router, investigation_router

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

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


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rag-backend"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
