from fastapi import APIRouter, HTTPException, Depends
from google.cloud import firestore
from ..auth import verify_google_token
from ..config import get_config
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
    try:
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

    except Exception as e:
        logger.error(f"Error in get_or_create_user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get or create user"
        )


async def require_admin(current_user: Dict = Depends(verify_google_token)) -> Dict:
    """Dependency to ensure current user is admin"""
    user_doc = await get_or_create_user(current_user)
    if user_doc['role'] != 'admin':
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return user_doc


@admin_router.get("/users")
async def get_all_users(admin_user: Dict = Depends(require_admin)):
    """Return all users (admin only)"""
    try:
        db = get_db()
        users_ref = db.collection(users_collection)
        users = [doc.to_dict() for doc in users_ref.stream()]
        return users
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")


@admin_router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_update: Dict,
    admin_user: Dict = Depends(require_admin)
):
    """Update user role (admin only)"""
    try:
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

    except Exception as e:
        logger.error(f"Error updating user role: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update user role"
        )


@admin_router.get("/stats")
async def get_admin_stats(admin_user: Dict = Depends(require_admin)):
    """Return system stats (admin only)"""
    try:
        db = get_db()
        users_ref = db.collection(users_collection)
        users = list(users_ref.stream())

        # Basic stats
        total_users = len(users)
        role_counts = {}
        for user_doc in users:
            user_data = user_doc.to_dict()
            role = user_data.get('role', 'viewer')
            role_counts[role] = role_counts.get(role, 0) + 1

        return {
            "total_users": total_users,
            "users_by_role": role_counts,
            "total_alerts": 0,  # Placeholder - you can add real alert stats later
            "system_status": "healthy"
        }
    except Exception as e:
        logger.error(f"Error fetching admin stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")
