import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud.conversation import (
    delete_conversation,
    get_conversation_with_messages,
    get_user_conversations,
)
from app.models.conversation import Conversation
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.conversation import ConversationResponse

router = APIRouter()

@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get user's conversations"""
    try:
        conversations = await get_user_conversations(db, str(current_user.id), limit)
        
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific conversation"""
    try:
        conversation = await get_conversation_with_messages(db, uuid.UUID(conversation_id))
        
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation"""
    try:
        conversation = await get_conversation_with_messages(db, uuid.UUID(conversation_id))
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        await delete_conversation(db, conversation)
        
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
