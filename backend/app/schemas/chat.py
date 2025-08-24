"""
Chat-related Pydantic schemas
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Schema for chat message requests"""
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    is_quiz_mode: bool = Field(False, description="Whether this is a quiz interaction")


class QuizState(BaseModel):
    """Schema for quiz state"""
    quiz_questions: Optional[List[Dict[str, Any]]] = None
    current_quiz_index: Optional[int] = None
    quiz_scores: Optional[List[Dict[str, Any]]] = None
    used_quiz_questions: Optional[List[str]] = []
    is_active: bool = False


class ChatResponse(BaseModel):
    """Schema for chat responses"""
    response: str
    conversation_id: str
    topic: str
    quiz_state: Optional[QuizState] = None


class StartQuizRequest(BaseModel):
    """Schema for starting a quiz"""
    conversation_id: str = Field(..., description="Conversation ID to start quiz for")


class MessageResponse(BaseModel):
    """Schema for message responses"""
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.replace(tzinfo=timezone.utc).isoformat() if v.tzinfo is None else v.isoformat()
        }
