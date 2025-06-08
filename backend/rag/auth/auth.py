from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from typing import List
import json
import os
from datetime import datetime

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_google_token(token: str = Depends(oauth2_scheme)):
    """Token verification - should be moved to a shared auth module."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as grequests

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

    try:
        idinfo = id_token.verify_oauth2_token(
            token, grequests.Request(), GOOGLE_CLIENT_ID)
        return idinfo
    except Exception:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials")
