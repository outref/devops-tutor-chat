import uuid
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud.conversation import (
    delete_conversation as crud_delete_conversation,
    get_conversation_with_messages,
    get_user_conversations,
)
from app.models.conversation import Conversation
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.conversation import ConversationResponse

logger = logging.getLogger(__name__)
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
        logger.info(f"Attempting to delete conversation {conversation_id} for user {current_user.id}")
        
        conversation = await get_conversation_with_messages(db, uuid.UUID(conversation_id))
        
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Verify ownership
        if conversation.user_id != str(current_user.id):
            logger.warning(f"User {current_user.id} attempted to delete conversation {conversation_id} owned by {conversation.user_id}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"Deleting conversation {conversation_id} with {len(conversation.messages)} messages")
        await crud_delete_conversation(db, conversation)
        
        logger.info(f"Successfully deleted conversation {conversation_id}")
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")
