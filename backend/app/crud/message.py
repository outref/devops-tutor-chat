"""
CRUD operations for Message model
"""
import uuid
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Message, MessageRole


async def get_messages_by_conversation(
    db: AsyncSession, 
    conversation_id: uuid.UUID
) -> List[Message]:
    """Get all messages for a conversation"""
    stmt = select(Message).where(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at)
    
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_message_count(
    db: AsyncSession, 
    conversation_id: uuid.UUID
) -> int:
    """Get message count for a conversation"""
    stmt = select(func.count(Message.id)).where(
        Message.conversation_id == conversation_id
    )
    result = await db.execute(stmt)
    return result.scalar()


async def create_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: MessageRole,
    content: str,
    metadata: Optional[Dict] = None
) -> Message:
    """Create a new message"""
    message = Message(
        conversation_id=conversation_id,
        role=role.value,
        content=content,
        message_metadata=metadata or {}
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message
