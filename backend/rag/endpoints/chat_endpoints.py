"""Chat-related API endpoints."""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from typing import Optional, List, Dict
import os

from ..agents.chat_agent import (
    chat_with_corpus,
    clear_chat_session,
    get_active_sessions,
    get_conversation_history,
    get_session_info
)
from ..auth import verify_google_token

# Environment variables
RAG_CORPUS_ID = os.environ.get("RAG_CORPUS_ID")

# Router
chat_router = APIRouter(prefix="/chat", tags=["chat"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# OAuth2 scheme (defined in main.py)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class ChatMessage(BaseModel):
    text: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    conversation_history: List[Dict] = []


@chat_router.post("", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat_endpoint(
    request: Request,
    chat_message: ChatMessage,
    include_history: bool = False,
    user=Depends(verify_google_token)
):
    """
    Chat with the existing data corpus with conversation memory.

    Query Parameters:
    - include_history: If True, returns full conversation history. If False (default), 
      returns empty history for better performance with frontend state management.
    """
    try:
        response_text, session_id, conversation_history = await chat_with_corpus(
            chat_message.text,
            RAG_CORPUS_ID,
            chat_message.session_id
        )

        history_to_return = conversation_history if include_history else []

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            conversation_history=history_to_return
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.get("/{session_id}/history")
async def get_chat_history(
    session_id: str,
    user=Depends(verify_google_token)
):
    """Get conversation history for a specific session."""
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
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.delete("/{session_id}")
async def clear_chat_session_endpoint(
    session_id: str,
    user=Depends(verify_google_token)
):
    """Clear a specific chat session to start fresh."""
    try:
        cleared = clear_chat_session(session_id)
        if cleared:
            return {"message": f"Session {session_id} cleared successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.get("/sessions")
async def get_chat_sessions(
    user=Depends(verify_google_token)
):
    """Get list of active chat sessions."""
    try:
        sessions = get_active_sessions()

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
        raise HTTPException(status_code=500, detail=str(e))
