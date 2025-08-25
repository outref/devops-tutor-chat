import logging
from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.message import create_message, get_messages_by_conversation
from app.models.conversation import Conversation, MessageRole
from app.services.chatbot import DevOpsChatbot
from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)


class QuizManagementService:
    """Service for managing quiz operations and state"""
    
    def __init__(self, chatbot: DevOpsChatbot):
        self.chatbot = chatbot
        self.conversation_service = ConversationService(chatbot)
    
    async def start_quiz_session(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Start a quiz session for a conversation.
        
        Args:
            db: Database session
            user_id: ID of the user
            conversation_id: ID of the conversation
            
        Returns:
            Dictionary with response, conversation_id, topic, and quiz_state
        """
        try:
            # Validate conversation for quiz
            conversation = await self.conversation_service.validate_conversation_for_quiz(
                db, conversation_id, user_id
            )
            
            # Get all messages for context
            messages = await get_messages_by_conversation(db, conversation.id)
            
            # Convert to format expected by chatbot
            message_dicts = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Add a special message to trigger quiz generation
            message_dicts.append({"role": "user", "content": "__START_QUIZ__"})
            
            # Collect all used questions from previous quiz sessions in this conversation
            all_used_questions = await self._collect_used_questions(messages)
            
            logger.info(f"Found {len(all_used_questions)} previously used questions across all quiz sessions")
            
            # Process through chatbot in quiz mode
            initial_quiz_state = {"used_quiz_questions": all_used_questions}
            result = await self.chatbot.process_message(
                message_dicts,
                str(conversation.id),
                conversation.topic,
                is_quiz_mode=True,
                quiz_state=initial_quiz_state
            )
            
            response_content = result["response"]
            quiz_state = result.get("quiz_state")
            
            # Store the quiz initiation as a system message
            await create_message(
                db,
                conversation.id,
                MessageRole.SYSTEM,
                "Quiz started",
                {"quiz_state": quiz_state} if quiz_state else {}
            )
            
            # Store the first quiz question as assistant message
            await create_message(
                db,
                conversation.id,
                MessageRole.ASSISTANT,
                response_content,
                {"quiz_state": quiz_state} if quiz_state else {}
            )
            
            await self.conversation_service.update_conversation_activity(db, conversation)
            
            return {
                "response": response_content,
                "conversation_id": str(conversation.id),
                "topic": conversation.topic,
                "quiz_state": quiz_state
            }
            
        except Exception as e:
            await db.rollback()
            raise e
    
    async def _collect_used_questions(self, messages: List) -> List[str]:
        """
        Collect all used questions from previous quiz sessions in the conversation.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            List of unique used questions
        """
        all_used_questions = []
        
        for msg in messages:
            if (msg.role == MessageRole.ASSISTANT.value and 
                msg.message_metadata and 
                msg.message_metadata.get("quiz_state")):
                quiz_state_data = msg.message_metadata["quiz_state"]
                if "used_quiz_questions" in quiz_state_data:
                    all_used_questions.extend(quiz_state_data["used_quiz_questions"])
        
        # Remove duplicates while preserving order
        unique_used_questions = list(dict.fromkeys(all_used_questions))
        return unique_used_questions
