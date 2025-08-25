import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.services.conversation_service import ConversationService
from app.models.conversation import Conversation


@pytest.fixture
def conversation_service(mock_chatbot):
    """Create ConversationService instance with mocked dependencies."""
    return ConversationService(mock_chatbot)


@pytest.fixture
def mock_conversation():
    """Mock conversation object."""
    conversation = Mock(spec=Conversation)
    conversation.id = uuid4()
    conversation.topic = "Python Programming"
    conversation.user_id = "user123"
    return conversation


class TestConversationService:
    @pytest.mark.asyncio
    async def test_get_or_create_conversation_new_valid_topic(
        self,
        conversation_service,
        mock_db_session,
        mock_conversation
    ):
        """Test creating new conversation with valid topic."""
        user_id = "user123"
        first_message = "How do I use Python decorators?"
        
        # Mock topic validation
        conversation_service.chatbot.validate_first_message_topic = AsyncMock(
            return_value=(True, "Python Programming", "Valid programming topic")
        )
        
        with patch("app.services.conversation_service.create_conversation", new=AsyncMock(return_value=mock_conversation)):
            result, is_new = await conversation_service.get_or_create_conversation(
                mock_db_session,
                user_id,
                first_message=first_message
            )
        
        # Assertions
        assert result == mock_conversation
        assert is_new is True
        
        # Verify topic validation was called
        conversation_service.chatbot.validate_first_message_topic.assert_called_once_with(first_message)

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_new_invalid_topic(
        self,
        conversation_service,
        mock_db_session
    ):
        """Test creating new conversation with invalid topic raises ValueError."""
        user_id = "user123"
        first_message = "What's the weather today?"
        
        # Mock topic validation to return invalid
        conversation_service.chatbot.validate_first_message_topic = AsyncMock(
            return_value=(False, "Weather", "Not a programming topic")
        )
        
        with pytest.raises(ValueError, match="I can only help with topics related to"):
            await conversation_service.get_or_create_conversation(
                mock_db_session,
                user_id,
                first_message=first_message
            )

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_existing(
        self,
        conversation_service,
        mock_db_session,
        mock_conversation
    ):
        """Test retrieving existing conversation."""
        conversation_id = str(mock_conversation.id)
        user_id = "user123"
        
        with patch("app.services.conversation_service.get_conversation_by_id", new=AsyncMock(return_value=mock_conversation)):
            result, is_new = await conversation_service.get_or_create_conversation(
                mock_db_session,
                user_id,
                conversation_id=conversation_id
            )
        
        # Assertions
        assert result == mock_conversation
        assert is_new is False

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_existing_not_found(
        self,
        conversation_service,
        mock_db_session
    ):
        """Test retrieving non-existent conversation raises ValueError."""
        conversation_id = str(uuid4())
        user_id = "user123"
        
        with patch("app.services.conversation_service.get_conversation_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="Conversation not found"):
                await conversation_service.get_or_create_conversation(
                    mock_db_session,
                    user_id,
                    conversation_id=conversation_id
                )

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_no_first_message(
        self,
        conversation_service,
        mock_db_session
    ):
        """Test creating new conversation without first message raises ValueError."""
        user_id = "user123"
        
        with pytest.raises(ValueError, match="First message required for new conversation"):
            await conversation_service.get_or_create_conversation(
                mock_db_session,
                user_id
            )

    @pytest.mark.asyncio
    async def test_validate_conversation_for_quiz_success(
        self,
        conversation_service,
        mock_db_session,
        mock_conversation
    ):
        """Test successful conversation validation for quiz."""
        conversation_id = str(mock_conversation.id)
        user_id = "user123"
        
        with patch("app.services.conversation_service.get_conversation_by_id", new=AsyncMock(return_value=mock_conversation)), \
             patch("app.services.conversation_service.get_message_count", new=AsyncMock(return_value=4)):  # 4 messages (2 exchanges)
            
            result = await conversation_service.validate_conversation_for_quiz(
                mock_db_session,
                conversation_id,
                user_id
            )
        
        # Assertions
        assert result == mock_conversation

    @pytest.mark.asyncio
    async def test_validate_conversation_for_quiz_wrong_user(
        self,
        conversation_service,
        mock_db_session,
        mock_conversation
    ):
        """Test conversation validation fails for wrong user."""
        conversation_id = str(mock_conversation.id)
        user_id = "different_user"
        mock_conversation.user_id = "original_user"
        
        with patch("app.services.conversation_service.get_conversation_by_id", new=AsyncMock(return_value=mock_conversation)):
            with pytest.raises(ValueError, match="Conversation not found"):
                await conversation_service.validate_conversation_for_quiz(
                    mock_db_session,
                    conversation_id,
                    user_id
                )

    @pytest.mark.asyncio
    async def test_validate_conversation_for_quiz_not_found(
        self,
        conversation_service,
        mock_db_session
    ):
        """Test conversation validation fails when conversation not found."""
        conversation_id = str(uuid4())
        user_id = "user123"
        
        with patch("app.services.conversation_service.get_conversation_by_id", new=AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="Conversation not found"):
                await conversation_service.validate_conversation_for_quiz(
                    mock_db_session,
                    conversation_id,
                    user_id
                )

    @pytest.mark.asyncio
    async def test_validate_conversation_for_quiz_insufficient_messages(
        self,
        conversation_service,
        mock_db_session,
        mock_conversation
    ):
        """Test conversation validation fails with insufficient messages."""
        conversation_id = str(mock_conversation.id)
        user_id = "user123"
        
        with patch("app.services.conversation_service.get_conversation_by_id", new=AsyncMock(return_value=mock_conversation)), \
             patch("app.services.conversation_service.get_message_count", new=AsyncMock(return_value=1)):  # Only 1 message
            
            with pytest.raises(ValueError, match="Please have at least one conversation exchange"):
                await conversation_service.validate_conversation_for_quiz(
                    mock_db_session,
                    conversation_id,
                    user_id
                )

    @pytest.mark.asyncio
    async def test_update_conversation_activity(
        self,
        conversation_service,
        mock_db_session,
        mock_conversation
    ):
        """Test updating conversation activity timestamp."""
        with patch("app.services.conversation_service.update_conversation_timestamp", new=AsyncMock()) as mock_update:
            await conversation_service.update_conversation_activity(
                mock_db_session,
                mock_conversation
            )
        
        # Verify the update function was called
        mock_update.assert_called_once_with(mock_db_session, mock_conversation)

