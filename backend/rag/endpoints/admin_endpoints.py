from fastapi import APIRouter, HTTPException, Depends
from google.cloud import firestore
from ..auth import verify_google_token
from ..config import get_config
from ..exceptions import AuthenticationError, DatabaseError
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Initialize router with /admin prefix
admin_router = APIRouter(prefix="/admin", tags=["admin"])

# Collection name
users_collection = 'users'


def get_db():
    """Get Firestore client instance"""
    return firestore.Client(project=get_config().GOOGLE_CLOUD_PROJECT)


async def get_or_create_user(user_info: Dict) -> Dict:
    """
    Get existing user or create new one if doesn't exist.
    Returns user document with role.
    """
    # Input validation
    if not user_info.get('user_id'):
        raise AuthenticationError("User ID is required")

    if not user_info.get('email'):
        raise AuthenticationError("Email is required")

    db = get_db()
    # Check if user exists
    user_ref = db.collection(
        users_collection).document(user_info['user_id'])
    user_doc = user_ref.get()

    if user_doc.exists:
        # Return existing user
        return user_doc.to_dict()

    # Create new user with default role
    new_user = {
        'id': user_info['user_id'],
        'email': user_info['email'],
        'name': user_info.get('name', ''),
        'role': 'viewer',  # Default role
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }

    # Store in Firestore
    user_ref.set(new_user)
    logger.info(f"Created new user: {user_info['email']}")

    return new_user


async def require_admin(current_user: Dict = Depends(verify_google_token)) -> Dict:
    """Dependency to ensure current user is admin"""
    user_doc = await get_or_create_user(current_user)
    if user_doc['role'] != 'admin':
        raise AuthenticationError("Admin access required")
    return user_doc


@admin_router.get("/users")
async def get_all_users(admin_user: Dict = Depends(require_admin)):
    """Return all users (admin only)"""
    db = get_db()
    users_ref = db.collection(users_collection)
    users = [doc.to_dict() for doc in users_ref.stream()]
    return users


@admin_router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_update: Dict,
    admin_user: Dict = Depends(require_admin)
):
    """Update user role (admin only)"""
    # Input validation
    if not user_id or not user_id.strip():
        raise AuthenticationError("User ID is required")

    if not role_update.get('role'):
        raise AuthenticationError("Role is required")

    # Validate role value
    valid_roles = ['admin', 'editor', 'viewer']
    if role_update['role'] not in valid_roles:
        raise AuthenticationError(
            f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    db = get_db()
    # Update role
    user_ref = db.collection(users_collection).document(user_id)
    user_ref.update({
        'role': role_update['role'],
        'updated_at': firestore.SERVER_TIMESTAMP
    })

    # Get updated user
    updated_user = user_ref.get().to_dict()
    return updated_user
