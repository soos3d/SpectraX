"""Authentication routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from videofeed.credentials import get_credentials

router = APIRouter(prefix="/auth", tags=["authentication"])


class UserCredentials(BaseModel):
    """User credentials for authentication."""
    username: str
    password: str


@router.post("/verify")
async def verify_credentials(user_creds: UserCredentials):
    """Verify if credentials match those in the system keychain."""
    creds = get_credentials()
    
    # Check publisher credentials
    if user_creds.username == creds["publish_user"] and user_creds.password == creds["publish_pass"]:
        return {
            "authenticated": True,
            "user_type": "publisher",
            "username": creds["publish_user"]
        }
    
    # Check viewer credentials
    if user_creds.username == creds["read_user"] and user_creds.password == creds["read_pass"]:
        return {
            "authenticated": True,
            "user_type": "viewer",
            "username": creds["read_user"]
        }
    
    # Invalid credentials
    raise HTTPException(
        status_code=401,
        detail="Invalid credentials"
    )
