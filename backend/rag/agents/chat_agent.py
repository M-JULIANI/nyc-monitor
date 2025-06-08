"""Chat agent for conversing with the existing data corpus."""

import os
import logging
from typing import Optional, Dict, List
from datetime import date
import uuid

from google.adk.agents import Agent
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from ..tools.research_tools import create_rag_retrieval_tool

logger = logging.getLogger(__name__)
date_today = date.today()

# Global session storage for conversation memory
_chat_sessions: Dict[str, Runner] = {}
_session_service = InMemorySessionService()


def create_chat_agent(rag_corpus: Optional[str] = None) -> Agent:
    """
    Create a chat agent optimized for conversing with the data corpus.

    Args:
        rag_corpus: RAG corpus ID for retrieving data

    Returns:
        Agent configured for chat interactions
    """
    tools = []

    # Add RAG tool for corpus queries
    rag_tool = create_rag_retrieval_tool(rag_corpus)
    if rag_tool:
        tools.append(rag_tool)
    else:
        logger.warning(
            "No RAG corpus provided for chat agent - will operate without corpus access")

    return Agent(
        model=os.getenv("CHAT_AGENT_MODEL", "gemini-2.0-flash-001"),
        name="atlas_chat_agent",
        instruction=f"""
You are the Atlas NYC Monitor Chat Agent. Today's date: {date_today}

Your role is to help users explore and understand information from the NYC monitoring data corpus.
You have access to a comprehensive knowledge base about NYC events, incidents, and urban data.

Guidelines:
- Use the RAG retrieval tool to search for relevant information from the corpus
- Provide helpful, accurate responses based on the available data
- If asked about current/live events, explain that you work with the stored corpus data
- For real-time investigations, suggest users use the investigation endpoint
- Be conversational and helpful while staying focused on NYC-related topics
- Remember previous messages in this conversation and build upon them
- Reference earlier parts of the conversation when relevant
- If asked about conversation history, acknowledge what has been discussed

When users ask questions:
1. Consider the conversation history and context
2. Search the corpus for relevant information using RAG
3. Synthesize findings into a clear, helpful response
4. Cite sources when available
5. Suggest follow-up questions or related topics when appropriate
""",
        tools=tools,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.3),  # Slightly more creative for chat
    )


def get_or_create_chat_session(session_id: Optional[str] = None, rag_corpus: Optional[str] = None) -> tuple[str, Runner]:
    """
    Get existing chat session or create a new one.

    Args:
        session_id: Optional existing session ID
        rag_corpus: RAG corpus ID for the chat agent

    Returns:
        Tuple of (session_id, runner)
    """
    if session_id and session_id in _chat_sessions:
        logger.info(f"Retrieved existing chat session: {session_id}")
        return session_id, _chat_sessions[session_id]

    # Create new session
    new_session_id = str(uuid.uuid4())

    # Create chat agent and runner
    chat_agent = create_chat_agent(rag_corpus)
    runner = Runner(
        agent=chat_agent,
        app_name="atlas_chat",
        session_service=_session_service
    )

    # Store session
    _chat_sessions[new_session_id] = runner

    logger.info(f"Created new chat session: {new_session_id}")
    return new_session_id, runner


async def get_conversation_history(session_id: str) -> List[Dict]:
    """
    Get conversation history for a specific session.

    Args:
        session_id: Session ID to get history for

    Returns:
        List of conversation messages
    """
    if session_id not in _chat_sessions:
        return []

    try:
        runner = _chat_sessions[session_id]

        # Access the session from the runner
        # The session service stores conversation history internally
        session_data = _session_service._sessions.get(session_id, {})

        # Extract conversation history if available
        if 'conversation' in session_data:
            return session_data['conversation']

        # Fallback: try to get session history from runner
        if hasattr(runner, '_session_id'):
            session_info = _session_service._sessions.get(
                runner._session_id, {})
            return session_info.get('history', [])

        return []

    except Exception as e:
        logger.error(
            f"Error retrieving conversation history for session {session_id}: {e}")
        return []


async def chat_with_corpus(
    message: str,
    rag_corpus: Optional[str] = None,
    session_id: Optional[str] = None
) -> tuple[str, str, List[Dict]]:
    """
    Main entry point for chatting with the data corpus with conversation memory.

    Args:
        message: User's chat message
        rag_corpus: Optional RAG corpus ID
        session_id: Optional session ID for conversation continuity

    Returns:
        Tuple of (response, session_id, conversation_history)
    """
    try:
        # Get or create chat session
        current_session_id, runner = get_or_create_chat_session(
            session_id, rag_corpus)

        # Get current conversation history before adding new message
        history_before = await get_conversation_history(current_session_id)

        # Execute chat with conversation memory
        logger.info(
            f"Processing chat message in session {current_session_id}: {message[:50]}...")
        logger.info(
            f"Conversation history length: {len(history_before)} messages")

        # Run the chat through the agent (maintains conversation history)
        chat_response = await runner.run_async(message)

        # Get updated conversation history after response
        history_after = await get_conversation_history(current_session_id)

        logger.info(
            f"Chat response generated successfully for session {current_session_id}")
        return chat_response, current_session_id, history_after

    except Exception as e:
        logger.error(f"Error during chat: {e}")
        error_response = f"I apologize, but I encountered an error while processing your message: {str(e)}"
        # Return current session ID and empty history even on error
        return error_response, session_id or str(uuid.uuid4()), []


def clear_chat_session(session_id: str) -> bool:
    """
    Clear a specific chat session.

    Args:
        session_id: Session ID to clear

    Returns:
        True if session was found and cleared, False otherwise
    """
    if session_id in _chat_sessions:
        # Clear from our storage
        del _chat_sessions[session_id]

        # Also clear from session service if possible
        try:
            if hasattr(_session_service, '_sessions') and session_id in _session_service._sessions:
                del _session_service._sessions[session_id]
        except Exception as e:
            logger.warning(
                f"Could not clear session from session service: {e}")

        logger.info(f"Cleared chat session: {session_id}")
        return True
    return False


def get_active_sessions() -> List[str]:
    """Get list of active session IDs."""
    return list(_chat_sessions.keys())


def get_session_info(session_id: str) -> Optional[Dict]:
    """
    Get detailed information about a specific session.

    Args:
        session_id: Session ID to get info for

    Returns:
        Session information dictionary or None if not found
    """
    if session_id not in _chat_sessions:
        return None

    try:
        # Get basic session info
        runner = _chat_sessions[session_id]

        return {
            "session_id": session_id,
            "app_name": "atlas_chat",
            "agent_name": "atlas_chat_agent",
            "created": True,
            "active": True
        }

    except Exception as e:
        logger.error(f"Error getting session info for {session_id}: {e}")
        return None
