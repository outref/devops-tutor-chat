import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.services.chat_service import ChatService
from app.models.conversation import Conversation, MessageRole


@pytest.fixture
def chat_service(mock_chatbot):
    """Create ChatService instance with mocked dependencies."""
    return ChatService(mock_chatbot)


@pytest.fixture
def mock_conversation():
    """Mock conversation object."""
    conversation = Mock(spec=Conversation)
    conversation.id = uuid4()
    conversation.topic = "Python Programming"
    conversation.user_id = "user123"
    return conversation


@pytest.fixture
def mock_message():
    """Mock message object."""
    message = Mock()
    message.id = uuid4()
    message.role = MessageRole.USER
    message.content = "Test message"
    message.created_at = "2023-01-01T00:00:00Z"
    message.message_metadata = {}
    return message


class TestChatService:
    @pytest.mark.asyncio
    async def test_process_chat_message_new_conversation(
        self,
        chat_service,
        mock_db_session,
        mock_conversation,
        mock_message
    ):
        """Test processing a chat message with new conversation creation."""
        user_id = "user123"
        message = "How do I use Python decorators?"
        
        # Mock the conversation service behavior
        chat_service.conversation_service.get_or_create_conversation = AsyncMock(
            return_value=(mock_conversation, True)
        )
        chat_service.conversation_service.update_conversation_activity = AsyncMock()
        
        with patch("app.services.chat_service.create_message", new=AsyncMock()) as mock_create_message, \
             patch("app.services.chat_service.get_messages_by_conversation", new=AsyncMock(return_value=[mock_message])) as mock_get_messages:
            
            result = await chat_service.process_chat_message(
                mock_db_session,
                user_id,
                message
            )
        
        # Assertions
        assert result["response"] == "Mock response"
        assert result["conversation_id"] == str(mock_conversation.id)
        assert result["topic"] == mock_conversation.topic
        assert result["quiz_state"] is None
        
        # Verify service calls
        chat_service.conversation_service.get_or_create_conversation.assert_called_once_with(
            mock_db_session, user_id, None, message
        )
        assert mock_create_message.call_count == 2  # User message + assistant response
        chat_service.conversation_service.update_conversation_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chat_message_existing_conversation(
        self,
        chat_service,
        mock_db_session,
        mock_conversation,
        mock_message
    ):
        """Test processing a chat message with existing conversation."""
        user_id = "user123"
        message = "Can you explain more about decorators?"
        conversation_id = str(mock_conversation.id)
        
        # Mock the conversation service behavior
        chat_service.conversation_service.get_or_create_conversation = AsyncMock(
            return_value=(mock_conversation, False)
        )
        chat_service.conversation_service.update_conversation_activity = AsyncMock()
        
        with patch("app.services.chat_service.create_message", new=AsyncMock()), \
             patch("app.services.chat_service.get_messages_by_conversation", new=AsyncMock(return_value=[mock_message])):
            
            result = await chat_service.process_chat_message(
                mock_db_session,
                user_id,
                message,
                conversation_id
            )
        
        # Assertions
        assert result["response"] == "Mock response"
        assert result["conversation_id"] == conversation_id
        
        # Verify service calls
        chat_service.conversation_service.get_or_create_conversation.assert_called_once_with(
            mock_db_session, user_id, conversation_id, message
        )

    @pytest.mark.asyncio
    async def test_process_chat_message_quiz_mode(
        self,
        chat_service,
        mock_db_session,
        mock_conversation,
        mock_message
    ):
        """Test processing a chat message in quiz mode."""
        user_id = "user123"
        message = "A"
        is_quiz_mode = True
        
        # Mock quiz state
        quiz_state = {
            "quiz_questions": [{"question": "What is Python?"}],
            "current_quiz_index": 0
        }
        
        # Mock chatbot response with quiz state
        chat_service.chatbot.process_message = AsyncMock(return_value={
            "response": "Correct! Python is a programming language.",
            "quiz_state": quiz_state
        })
        
        # Mock quiz state extraction
        mock_message.message_metadata = {"quiz_state": quiz_state}
        mock_message.role = MessageRole.ASSISTANT
        
        chat_service.conversation_service.get_or_create_conversation = AsyncMock(
            return_value=(mock_conversation, False)
        )
        chat_service.conversation_service.update_conversation_activity = AsyncMock()
        
        with patch("app.services.chat_service.create_message", new=AsyncMock()), \
             patch("app.services.chat_service.get_messages_by_conversation", new=AsyncMock(return_value=[mock_message])):
            
            result = await chat_service.process_chat_message(
                mock_db_session,
                user_id,
                message,
                str(mock_conversation.id),
                is_quiz_mode
            )
        
        # Assertions
        assert result["response"] == "Correct! Python is a programming language."
        assert result["quiz_state"] == quiz_state

    @pytest.mark.asyncio
    async def test_process_chat_message_error_handling(
        self,
        chat_service,
        mock_db_session
    ):
        """Test error handling in process_chat_message."""
        user_id = "user123"
        message = "Test message"
        
        # Mock conversation service to raise exception
        chat_service.conversation_service.get_or_create_conversation = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        with pytest.raises(Exception, match="Database error"):
            await chat_service.process_chat_message(
                mock_db_session,
                user_id,
                message
            )
        
        # Verify rollback was called
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_conversation_messages(
        self,
        chat_service,
        mock_db_session,
        mock_message
    ):
        """Test retrieving conversation messages."""
        conversation_id = str(uuid4())
        
        with patch("app.services.chat_service.get_messages_by_conversation", new=AsyncMock(return_value=[mock_message])):
            result = await chat_service.get_conversation_messages(
                mock_db_session,
                conversation_id
            )
        
        # Assertions
        assert len(result) == 1
        assert result[0]["id"] == str(mock_message.id)
        assert result[0]["role"] == mock_message.role
        assert result[0]["content"] == mock_message.content
        assert result[0]["created_at"] == mock_message.created_at

    @pytest.mark.asyncio
    async def test_extract_quiz_state_found(self, chat_service):
        """Test extracting quiz state from messages when available."""
        quiz_state = {"current_quiz_index": 0, "quiz_questions": []}
        
        # Mock message with quiz state
        mock_msg = Mock()
        mock_msg.role = MessageRole.ASSISTANT.value
        mock_msg.message_metadata = {"quiz_state": quiz_state}
        
        messages = [mock_msg]
        
        result = await chat_service._extract_quiz_state(messages)
        
        assert result == quiz_state

    @pytest.mark.asyncio
    async def test_extract_quiz_state_not_found(self, chat_service):
        """Test extracting quiz state when not available."""
        # Mock message without quiz state
        mock_msg = Mock()
        mock_msg.role = MessageRole.USER.value
        mock_msg.message_metadata = {}
        
        messages = [mock_msg]
        
        result = await chat_service._extract_quiz_state(messages)
        
        assert result is None

