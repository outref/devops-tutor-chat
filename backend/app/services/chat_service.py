import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.message import create_message, get_messages_by_conversation
from app.models.conversation import Conversation, MessageRole
from app.services.chatbot import DevOpsChatbot
from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat message processing"""
    
    def __init__(self, chatbot: DevOpsChatbot):
        self.chatbot = chatbot
        self.conversation_service = ConversationService(chatbot)
    
    async def process_chat_message(
        self,
        db: AsyncSession,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        is_quiz_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Process a chat message through the complete pipeline.
        
        Args:
            db: Database session
            user_id: ID of the user
            message: User's message
            conversation_id: Optional existing conversation ID
            is_quiz_mode: Whether this is a quiz interaction
            
        Returns:
            Dictionary with response, conversation_id, topic, and optional quiz_state
        """
        try:
            # Get or create conversation
            conversation, is_new = await self.conversation_service.get_or_create_conversation(
                db, user_id, conversation_id, message
            )
            
            # Add user message
            await create_message(
                db,
                conversation.id,
                MessageRole.USER,
                message
            )
            
            # Get all messages for this conversation
            messages = await get_messages_by_conversation(db, conversation.id)
            
            # Convert to format expected by chatbot
            message_dicts = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Get quiz state from the latest assistant message if in quiz mode
            quiz_state = None
            if is_quiz_mode:
                quiz_state = await self._extract_quiz_state(messages)
            
            # Process through chatbot with conversation topic
            result = await self.chatbot.process_message(
                message_dicts,
                str(conversation.id),
                conversation.topic,
                is_quiz_mode=is_quiz_mode,
                quiz_state=quiz_state
            )
            
            response_content = result["response"]
            new_quiz_state = result.get("quiz_state")
            
            # Update conversation timestamp
            await self.conversation_service.update_conversation_activity(db, conversation)
            
            # Add assistant response with quiz state if present
            message_metadata = {}
            if new_quiz_state:
                message_metadata["quiz_state"] = new_quiz_state
            
            await create_message(
                db,
                conversation.id,
                MessageRole.ASSISTANT,
                response_content,
                message_metadata
            )
            
            return {
                "response": response_content,
                "conversation_id": str(conversation.id),
                "topic": conversation.topic,
                "quiz_state": new_quiz_state
            }
            
        except Exception as e:
            await db.rollback()
            raise e
    
    async def get_conversation_messages(
        self,
        db: AsyncSession,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all messages for a conversation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            
        Returns:
            List of message dictionaries
        """
        messages = await get_messages_by_conversation(db, conversation_id)
        
        return [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at
            }
            for msg in messages
        ]
    
    async def _extract_quiz_state(self, messages: List) -> Optional[Dict[str, Any]]:
        """Extract quiz state from the latest assistant message with quiz state"""
        for msg in reversed(messages):
            if (msg.role == MessageRole.ASSISTANT.value and 
                msg.message_metadata and 
                msg.message_metadata.get("quiz_state")):
                quiz_state = msg.message_metadata["quiz_state"]
                logger.info(f"Found quiz state from assistant message: questions={len(quiz_state.get('quiz_questions', []))}, index={quiz_state.get('current_quiz_index')}")
                return quiz_state
        
        if messages:  # Only log warning if there are messages
            logger.warning("Quiz mode requested but no quiz state found in assistant messages")
        
        return None
