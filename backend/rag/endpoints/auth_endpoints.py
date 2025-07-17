from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.security import HTTPBearer
from google.cloud import firestore
from ..auth import verify_google_token
from ..config import get_config
import logging
import os
import jwt
import datetime
from typing import Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Initialize router
auth_router = APIRouter(prefix="/auth", tags=["auth"])

# Collection name
users_collection = 'users'

# Pydantic models
class LoginRequest(BaseModel):
    token: str

class LoginResponse(BaseModel):
    user: Dict
    message: str

def get_db():
    """Get Firestore client instance"""
    return firestore.Client(project=get_config().GOOGLE_CLOUD_PROJECT)

def create_session_token(user_data: Dict) -> str:
    """Create a secure session token"""
    config = get_config()
    
    # Use a secret key for signing (should be in environment variables)
    secret_key = os.getenv('SESSION_SECRET_KEY', 'your-secret-key-change-this')
    
    payload = {
        'user_id': user_data['user_id'],
        'email': user_data['email'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),  # 7 day expiration
        'iat': datetime.datetime.utcnow(),
    }
    
    return jwt.encode(payload, secret_key, algorithm='HS256')

def verify_session_token(token: str) -> Dict:
    """Verify and decode session token"""
    secret_key = os.getenv('SESSION_SECRET_KEY', 'your-secret-key-change-this')
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session")

@auth_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """
    Exchange Google ID token for secure session cookie
    """
    try:
        # Verify Google ID token
        user_data = await verify_google_token(request.token)
        
        # Get or create user in database
        db = get_db()
        user_ref = db.collection(users_collection).document(user_data['user_id'])
        user_doc = user_ref.get()
        
        if user_doc.exists:
            stored_user = user_doc.to_dict()
            # Update last login
            user_ref.update({'last_login': firestore.SERVER_TIMESTAMP})
        else:
            # Create new user
            stored_user = {
                'id': user_data['user_id'],
                'email': user_data['email'],
                'name': user_data.get('name', ''),
                'role': 'viewer',  # Default role
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_login': firestore.SERVER_TIMESTAMP,
            }
            user_ref.set(stored_user)
        
        # Create session token
        session_token = create_session_token(user_data)
        
        # Set HttpOnly cookie
        response.set_cookie(
            key="session",
            value=session_token,
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,  # Cannot be accessed by JavaScript
            secure=True,    # Only sent over HTTPS
            samesite="lax"  # CSRF protection
        )
        
        return LoginResponse(
            user=stored_user,
            message="Login successful"
        )
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@auth_router.post("/logout")
async def logout(response: Response):
    """
    Clear session cookie
    """
    response.delete_cookie(
        key="session",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return {"message": "Logout successful"}

@auth_router.get("/me")
async def get_current_user(request: Request):
    """
    Get current user from session cookie
    """
    try:
        # Get session cookie
        session_token = request.cookies.get("session")
        if not session_token:
            raise HTTPException(status_code=401, detail="No session")
        
        # Verify session token
        payload = verify_session_token(session_token)
        
        # Get user from database
        db = get_db()
        user_ref = db.collection(users_collection).document(payload['user_id'])
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_doc.to_dict()
        return {"user": user_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid session")