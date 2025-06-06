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
from typing import Optional, List, Dict
from .agent import investigate_alert
from .agents.chat_agent import (
    chat_with_corpus,
    clear_chat_session,
    get_active_sessions,
    get_conversation_history,
    get_session_info
)
from .investigation.state_manager import AlertData
import os
from datetime import datetime

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")  # Set this in your .env
RAG_CORPUS_ID = os.environ.get("RAG_CORPUS_ID")  # Set this in your .env

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
        "https://nyc-monitor.app",  # Production custom domain
        "https://atlas-frontend-290750569862.us-central1.run.app",  # Original Cloud Run URL
        "http://localhost:3000",  # Local development
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
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


class ChatMessage(BaseModel):
    text: str
    # Optional session ID for conversation continuity
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str  # Always return session ID for future requests
    conversation_history: List[Dict] = []  # Include conversation history


class Question(BaseModel):
    text: str


class Answer(BaseModel):
    response: str


class InvestigationResult(BaseModel):
    investigation_id: str
    status: str
    findings: str
    artifacts: list
    confidence_score: float


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")  # Higher limit for chat
async def chat_endpoint(
    request: Request,  # Used by rate limiter to track per-IP limits
    chat_message: ChatMessage,
    include_history: bool = False,  # Query param to control history inclusion
    user=Depends(verify_google_token)
):
    """
    Chat with the existing data corpus with conversation memory.

    This endpoint maintains conversation sessions so users can have ongoing dialogues.
    Pass session_id from previous responses to continue the same conversation.

    Query Parameters:
    - include_history: If True, returns full conversation history. If False (default), 
      returns empty history for better performance with frontend state management.

    For full conversation history, use GET /chat/{session_id}/history
    For real-time investigations, use the /investigate endpoint.
    """
    try:
        # Use the session-aware chat function
        response_text, session_id, conversation_history = await chat_with_corpus(
            chat_message.text,
            RAG_CORPUS_ID,
            chat_message.session_id
        )

        # Return history based on query parameter
        history_to_return = conversation_history if include_history else []

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            conversation_history=history_to_return
        )
    except Exception as e:
        print("ERROR in /chat:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/{session_id}/history")
async def get_chat_history(
    session_id: str,
    user=Depends(verify_google_token)
):
    """
    Get conversation history for a specific session.
    """
    try:
        history = await get_conversation_history(session_id)
        session_info = get_session_info(session_id)

        return {
            "session_id": session_id,
            "session_info": session_info,
            "conversation_history": history,
            "message_count": len(history)
        }
    except Exception as e:
        print("ERROR in /chat/history:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/{session_id}")
async def clear_chat_session_endpoint(
    session_id: str,
    user=Depends(verify_google_token)
):
    """
    Clear a specific chat session to start fresh.
    """
    try:
        cleared = clear_chat_session(session_id)
        if cleared:
            return {"message": f"Session {session_id} cleared successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        print("ERROR in /chat/clear:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/sessions")
async def get_chat_sessions(
    user=Depends(verify_google_token)
):
    """
    Get list of active chat sessions (for debugging/admin).
    """
    try:
        sessions = get_active_sessions()

        # Get detailed info for each session
        session_details = []
        for session_id in sessions:
            info = get_session_info(session_id)
            if info:
                history = await get_conversation_history(session_id)
                info["message_count"] = len(history)
                session_details.append(info)

        return {
            "active_sessions": session_details,
            "count": len(sessions)
        }
    except Exception as e:
        print("ERROR in /chat/sessions:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/investigate", response_model=InvestigationResult)
@limiter.limit("3/minute")  # Lower limit for more intensive operations
async def investigate_alert_endpoint(
    request: Request,  # Used by rate limiter to track per-IP limits
    alert_data: AlertData,
    user=Depends(verify_google_token)
):
    """
    Investigate a specific alert using the multi-agent system.
    This is where everything becomes "live" - the main entry funnel for investigations.

    This endpoint triggers a full investigation including:
    - Research agent collecting data and artifacts
    - Analysis of findings  
    - Generation of investigation report
    """
    try:
        # Run the async investigation - this is the main entry funnel
        findings = await investigate_alert(alert_data)

        # Return structured investigation results
        investigation_result = InvestigationResult(
            investigation_id=alert_data.alert_id,
            status="completed",
            findings=findings,
            artifacts=[
                f"media_{alert_data.event_type}_0_0.png",
                f"screenshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            ],
            confidence_score=0.8
        )

        return investigation_result

    except Exception as e:
        print("ERROR in /investigate:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rag-backend"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
