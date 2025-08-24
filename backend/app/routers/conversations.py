from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone

from app.services.database import get_db
from app.models.conversation import Conversation

router = APIRouter()

class ConversationResponse(BaseModel):
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

@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    user_id: str = "default_user",
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get user's conversations"""
    try:
        stmt = select(Conversation).where(
            Conversation.user_id == user_id
        ).options(selectinload(Conversation.messages)).order_by(desc(Conversation.updated_at)).limit(limit)
        
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        
        responses = []
        for conv in conversations:
            # Count messages (in production, you'd want to optimize this)
            responses.append(
                ConversationResponse(
                    id=str(conv.id),
                    user_id=conv.user_id,
                    topic=conv.topic,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    message_count=len(conv.messages)
                )
            )
        
        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific conversation"""
    try:
        stmt = select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id)
        ).options(selectinload(Conversation.messages))
        
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return ConversationResponse(
            id=str(conversation.id),
            user_id=conversation.user_id,
            topic=conversation.topic,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation"""
    try:
        stmt = select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id)
        )
        
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        await db.delete(conversation)
        await db.commit()
        
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
