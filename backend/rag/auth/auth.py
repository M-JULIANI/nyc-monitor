from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import os
import logging
import jwt
import datetime

# Set up logging
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_session_token(token: str) -> dict:
    """Verify and decode session token"""
    secret_key = os.getenv('SESSION_SECRET_KEY', 'your-secret-key-change-this')
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session")


async def verify_session(request: Request) -> dict:
    """Verify session cookie and return user info"""
    # Get session cookie
    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(status_code=401, detail="No session")
    
    # Verify session token
    payload = verify_session_token(session_token)
    
    # Return user info in the same format as verify_google_token
    user_info = {
        "user_id": payload['user_id'],
        "email": payload['email'],
        "name": payload.get('name'),
    }
    
    logger.info(f"Session verified for user: {user_info['email']}")
    return user_info


async def verify_google_token(token: str = Depends(oauth2_scheme)):
    """Verify Google OAuth token"""
    # Use central configuration instead of reading env vars directly
    from ..config import get_config
    config = get_config()

    logger.info("verify_google_token called")
    logger.info(
        f"GOOGLE_CLIENT_ID configured: {bool(config.GOOGLE_CLIENT_ID)}")
    logger.info(
        f"Token received: {bool(token)} (length: {len(token) if token else 0})")

    if not config.GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID environment variable not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Client ID not configured"
        )

    try:
        logger.info("Attempting to verify token with Google...")
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            token, grequests.Request(), config.GOOGLE_CLIENT_ID
        )

        logger.info(
            f"Token verified successfully for user: {idinfo.get('email')}")

        # Return user info
        user_info = {
            "user_id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo.get("name"),
        }
        logger.info(f"Returning user info: {user_info}")
        return user_info
    except ValueError as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
