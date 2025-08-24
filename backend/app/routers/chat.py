from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
import logging
from datetime import datetime, timezone

from app.services.database import get_db
from app.services.chatbot import DevOpsChatbot
from app.models.conversation import Conversation, Message, MessageRole
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize chatbot
chatbot = DevOpsChatbot()

# Pydantic models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    topic: str

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.replace(tzinfo=timezone.utc).isoformat() if v.tzinfo is None else v.isoformat()
        }

@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message to the chatbot"""
    try:
        # Get or create conversation
        if request.conversation_id:
            # Fetch existing conversation
            stmt = select(Conversation).where(
                Conversation.id == uuid.UUID(request.conversation_id)
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation (topic will be set after first message)
            conversation = Conversation(
                user_id=str(current_user.id),
                topic="pending"
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
        
        # Add user message
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER.value,
            content=request.message
        )
        db.add(user_message)
        await db.commit()
        
        # Get all messages for this conversation
        stmt = select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at)
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        # Convert to format expected by chatbot
        message_dicts = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Process through chatbot
        response_content = await chatbot.process_message(
            message_dicts,
            str(conversation.id)
        )
        
        # Extract topic from chatbot's state if this is the first message
        if conversation.topic == "pending" and len(messages) == 1:
            # Get the topic from the chatbot's internal state
            config = {"configurable": {"thread_id": str(conversation.id)}}
            try:
                # Access the chatbot's memory to get the extracted topic
                checkpointer = chatbot.memory
                checkpoint = await checkpointer.aget(config)
                if checkpoint and "topic" in checkpoint.get("channel_values", {}):
                    extracted_topic = checkpoint["channel_values"]["topic"]
                    if extracted_topic and extracted_topic.strip():
                        conversation.topic = extracted_topic.strip()
                    else:
                        conversation.topic = "General"
                else:
                    conversation.topic = "General"
            except Exception as e:
                # Fallback to general if we can't extract the topic
                logger.error(f"Error extracting topic from chatbot state: {e}")
                conversation.topic = "General"
        
        # Update conversation timestamp
        conversation.updated_at = func.now()
        
        # Add assistant response
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT.value,
            content=response_content
        )
        db.add(assistant_message)
        await db.commit()
        
        return ChatResponse(
            response=response_content,
            conversation_id=str(conversation.id),
            topic=conversation.topic
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/messages/{conversation_id}", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all messages for a conversation"""
    try:
        stmt = select(Message).where(
            Message.conversation_id == uuid.UUID(conversation_id)
        ).order_by(Message.created_at)
        
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        return [
            MessageResponse(
                id=str(msg.id),
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
