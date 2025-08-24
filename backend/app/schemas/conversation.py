"""
Conversation-related Pydantic schemas
"""
from datetime import datetime, timezone

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    """Schema for conversation responses"""
    id: str
    user_id: str
    topic: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.replace(tzinfo=timezone.utc).isoformat() if v.tzinfo is None else v.isoformat()
        }
