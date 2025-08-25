import uuid
import logging
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.conversation import create_conversation, get_conversation_by_id, update_conversation_timestamp
from app.crud.message import get_message_count
from app.models.conversation import Conversation
from app.services.chatbot import DevOpsChatbot

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation lifecycle and validation"""
    
    def __init__(self, chatbot: DevOpsChatbot):
        self.chatbot = chatbot
    
    async def get_or_create_conversation(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: Optional[str] = None,
        first_message: Optional[str] = None
    ) -> Tuple[Conversation, bool]:
        """
        Get existing conversation or create new one with topic validation.
        
        Args:
            db: Database session
            user_id: ID of the user
            conversation_id: Optional existing conversation ID
            first_message: First message for topic validation (required for new conversations)
            
        Returns:
            Tuple of (conversation, is_new_conversation)
            
        Raises:
            ValueError: If topic validation fails for new conversation
        """
        if conversation_id:
            # Fetch existing conversation
            conversation = await get_conversation_by_id(db, uuid.UUID(conversation_id))
            
            if not conversation:
                raise ValueError("Conversation not found")
            
            return conversation, False
        else:
            # For new conversations, validate topic first
            if not first_message:
                raise ValueError("First message required for new conversation")
            
            is_valid_topic, extracted_topic, validation_reason = await self.chatbot.validate_first_message_topic(first_message)
            
            if not is_valid_topic:
                logger.info(f"Rejected new conversation for invalid topic: {validation_reason}")
                raise ValueError("I can only help with topics related to Programming, DevOps, and AI/Machine Learning. Please ask a question about software development, infrastructure, automation, data science, or related technical topics.")
            
            # Create new conversation with validated topic
            conversation = await create_conversation(db, user_id, extracted_topic)
            return conversation, True
    
    async def validate_conversation_for_quiz(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str
    ) -> Conversation:
        """
        Validate that a conversation exists, belongs to user, and has enough messages for quiz.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            user_id: ID of the user
            
        Returns:
            The validated conversation
            
        Raises:
            ValueError: If validation fails
        """
        # Fetch conversation
        conversation = await get_conversation_by_id(db, uuid.UUID(conversation_id))
        
        # Verify ownership
        if conversation and conversation.user_id != user_id:
            raise ValueError("Conversation not found")
        
        if not conversation:
            raise ValueError("Conversation not found")
        
        # Check if conversation has at least one message exchange
        message_count = await get_message_count(db, conversation.id)
        
        if message_count < 2:  # At least one user message and one assistant response
            raise ValueError("Please have at least one conversation exchange before starting a quiz")
        
        return conversation
    
    async def update_conversation_activity(self, db: AsyncSession, conversation: Conversation) -> None:
        """Update conversation's last activity timestamp"""
        await update_conversation_timestamp(db, conversation)
