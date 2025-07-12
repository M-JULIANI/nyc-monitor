from fastapi import APIRouter, Depends
from google.cloud import firestore
from ..auth import verify_google_token
from ..config import get_config
from ..exceptions import AuthenticationError, DatabaseError
import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)

# Initialize router
auth_router = APIRouter(prefix="/auth", tags=["auth"])

# Collection name
users_collection = 'users'


def get_db():
    """Get Firestore client instance"""
    # Any connection errors will be caught by global handlers
    return firestore.Client(project=get_config().GOOGLE_CLOUD_PROJECT)


def get_default_role(email: str) -> str:
    """Determine default role based on email whitelist"""
    # Get whitelisted emails from environment
    admin_emails = os.getenv('ADMIN_EMAILS', '').split(',')
    judge_emails = os.getenv('JUDGE_EMAILS', '').split(',')

    # Clean up whitespace
    admin_emails = [email.strip().lower()
                    for email in admin_emails if email.strip()]
    judge_emails = [email.strip().lower()
                    for email in judge_emails if email.strip()]

    email_lower = email.lower()

    if email_lower in admin_emails:
        return 'admin'
    elif email_lower in judge_emails:
        return 'judge'
    else:
        return 'viewer'


async def get_or_create_user(user_info: Dict) -> Dict:
    """
    Get existing user or create new one if doesn't exist.
    Returns user document with role.
    """
    # Validate required user info
    if not user_info.get('user_id'):
        raise AuthenticationError("User ID is required")

    if not user_info.get('email'):
        raise AuthenticationError("Email is required")

    # Get database connection - any errors will be caught by global handlers
    db = get_db()

    # Check if user exists
    user_ref = db.collection(users_collection).document(user_info['user_id'])
    user_doc = user_ref.get()

    if user_doc.exists:
        # Return existing user
        return user_doc.to_dict()

    # Determine role based on email whitelist
    default_role = get_default_role(user_info['email'])

    # Create new user with determined role
    new_user = {
        'id': user_info['user_id'],
        'email': user_info['email'],
        'name': user_info.get('name', ''),
        'role': default_role,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }

    # Store in Firestore - any database errors will be caught by global handlers
    user_ref.set(new_user)

    # Log successful user creation
    logger.info(
        f"Created new user: {user_info['email']} with role: {default_role}")

    return new_user


@auth_router.get("/me")
async def get_current_user(user_info: Dict = Depends(verify_google_token)):
    """Get current user info, creating user if doesn't exist"""

    # Get or create user - any errors will be caught by global handlers
    user = await get_or_create_user(user_info)

    return {
        "user": user,
        "token": "valid"  # Token is already verified by verify_google_token
    }
