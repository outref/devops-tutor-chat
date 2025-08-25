"""
CRUD operations for Conversation model
"""
import uuid
from typing import List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message


async def get_conversation_by_id(
    db: AsyncSession, 
    conversation_id: uuid.UUID
) -> Optional[Conversation]:
    """Get conversation by ID"""
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_conversation_with_messages(
    db: AsyncSession, 
    conversation_id: uuid.UUID
) -> Optional[Conversation]:
    """Get conversation with messages"""
    stmt = select(Conversation).where(
        Conversation.id == conversation_id
    ).options(selectinload(Conversation.messages))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_conversations(
    db: AsyncSession, 
    user_id: str, 
    limit: int = 20
) -> List[Conversation]:
    """Get user's conversations"""
    stmt = select(Conversation).where(
        Conversation.user_id == user_id
    ).options(selectinload(Conversation.messages)).order_by(
        desc(Conversation.updated_at)
    ).limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_conversation(
    db: AsyncSession, 
    user_id: str, 
    topic: str
) -> Conversation:
    """Create a new conversation"""
    conversation = Conversation(user_id=user_id, topic=topic)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def update_conversation_timestamp(
    db: AsyncSession, 
    conversation: Conversation
) -> None:
    """Update conversation timestamp"""
    conversation.updated_at = func.now()
    await db.commit()


async def delete_conversation(
    db: AsyncSession, 
    conversation: Conversation
) -> None:
    """Delete a conversation"""
    try:
        await db.delete(conversation)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e
