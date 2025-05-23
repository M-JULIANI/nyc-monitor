from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from pydantic import BaseModel
from .agent import root_agent
import os

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")  # Set this in your .env

app = FastAPI(
    title="RAG Backend",
    description="Backend service for RAG (Retrieval-Augmented Generation) application using Vertex AI RAG Engine",
    version="0.1.0",
    root_path="/api"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# OAuth2 (Google)
# Not used for Google, but required by FastAPI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_google_token(token: str = Depends(oauth2_scheme)):
    try:
        idinfo = id_token.verify_oauth2_token(
            token, grequests.Request(), GOOGLE_CLIENT_ID)
        return idinfo
    except Exception:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials")


class Question(BaseModel):
    text: str


class Answer(BaseModel):
    response: str


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.post("/ask", response_model=Answer)
@limiter.limit("5/minute")
async def ask_question(
    request: Request,
    question: Question,
    user=Depends(verify_google_token)
):
    try:
        response = root_agent(question.text)
        return Answer(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rag-backend"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
