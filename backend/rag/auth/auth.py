from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import os

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def verify_google_token(token: str = Depends(oauth2_scheme)):
    """Verify Google OAuth token"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Client ID not configured"
        )

    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            token, grequests.Request(), GOOGLE_CLIENT_ID
        )

        # Return user info
        return {
            "user_id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo.get("name"),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
