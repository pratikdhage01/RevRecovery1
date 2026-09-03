"""
LiveKit access token generation.
Backend generates tokens — secrets NEVER go to frontend.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from livekit.api import AccessToken, VideoGrants
from app.core.config import settings
import datetime
import time

router = APIRouter(prefix="/api/livekit", tags=["livekit"])


class TokenRequest(BaseModel):
    customer_id: str
    room_name: str = ""
    participant_name: str = "agent-user"


@router.post("/token")
async def generate_token(body: TokenRequest):
    """
    Generate a LiveKit access token for the browser client.
    The agent joins the same room and starts voice recovery.
    """
    if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured. Set LIVEKIT_API_KEY and LIVEKIT_API_SECRET in .env"
        )

    room_name = body.room_name or f"recovery-{body.customer_id}"

    token = (
        AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(body.participant_name)
        .with_name(body.participant_name)
        .with_grants(VideoGrants(room_join=True, room=room_name))
        .with_ttl(datetime.timedelta(seconds=3600))  # 1 hour
        .to_jwt()
    )

    return {
        "token": token,
        "room_name": room_name,
        "livekit_url": settings.LIVEKIT_URL,
        "customer_id": body.customer_id,
    }
