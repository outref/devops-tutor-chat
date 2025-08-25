import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import os

from app.services.chatbot.core import DevOpsChatbot
from app.services.chatbot.state import ChatState
from langchain.schema import HumanMessage, AIMessage, SystemMessage


@pytest.fixture
def mock_llm():
    """Mock ChatOpenAI LLM."""
    llm = Mock()
    llm.ainvoke = AsyncMock(return_value="Mock LLM response")
    return llm


@pytest.fixture
def mock_embeddings():
    """Mock OpenAI embeddings."""
    embeddings = Mock()
    embeddings.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return embeddings


@pytest.fixture
def mock_services():
    """Mock all the specialized services."""
    services = {
        'rag_service': Mock(),
        'mcp_service': Mock(),
        'quiz_service': Mock(),
        'search_service': Mock(),
        'content_generator': Mock(),
        'topic_validator': Mock(),
        'router': Mock()
    }
    
    # Set up default mock behaviors
    services['topic_validator'].extract_topic = AsyncMock(return_value="Python Programming")
    services['topic_validator'].validate_topic_category = AsyncMock(return_value=True)
    services['topic_validator'].validate_topic_relevance = AsyncMock(return_value=True)
    services['topic_validator'].validate_first_message_topic = AsyncMock(return_value=(True, "Python", "Valid"))
    
    services['search_service'].search_with_fallback = AsyncMock(return_value={
        "rag_results": [{"title": "Test Doc", "content": "Test content"}],
        "search_concepts": "Python programming"
    })
    services['search_service'].web_search = AsyncMock(return_value=[{"title": "Web result"}])
    
    services['content_generator'].generate_lesson = AsyncMock(return_value="Here's a lesson about Python")
    services['content_generator'].generate_response = AsyncMock(return_value="Here's a response about Python")
    
    services['quiz_service'].generate_quiz_questions = AsyncMock(return_value=[
        {"question": "What is Python?", "answer": "A programming language"}
    ])
    services['quiz_service'].process_quiz_answer = AsyncMock(return_value={
        "is_correct": True,
        "feedback": "Correct!"
    })
    services['quiz_service'].format_quiz_question = Mock(return_value="Question 1: What is Python?")
    
    services['router'].route_after_category_validation = Mock(return_value="valid_first")
    services['router'].route_after_topic_validation = Mock(return_value="valid")
    services['router'].route_after_web_search = Mock(return_value="lesson")
    
    return services


@pytest.fixture
def chatbot(mock_llm, mock_embeddings, mock_services):
    """Create DevOpsChatbot instance with mocked dependencies."""
    with patch("app.services.chatbot.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.services.chatbot.core.OpenAIEmbeddings", return_value=mock_embeddings), \
         patch("app.services.chatbot.core.RAGService", return_value=mock_services['rag_service']), \
         patch("app.services.chatbot.core.MCPWebSearchService", return_value=mock_services['mcp_service']), \
         patch("app.services.chatbot.core.QuizService", return_value=mock_services['quiz_service']), \
         patch("app.services.chatbot.core.SearchService", return_value=mock_services['search_service']), \
         patch("app.services.chatbot.core.ContentGenerator", return_value=mock_services['content_generator']), \
         patch("app.services.chatbot.core.TopicValidator", return_value=mock_services['topic_validator']), \
         patch("app.services.chatbot.core.ConversationRouter", return_value=mock_services['router']), \
         patch("app.services.chatbot.core.MemorySaver"), \
         patch("app.services.chatbot.core.StateGraph"), \
         patch("app.services.chatbot.core.END"):
        
        chatbot = DevOpsChatbot()
        
        # Inject mocked services
        chatbot.rag_service = mock_services['rag_service']
        chatbot.mcp_service = mock_services['mcp_service']
        chatbot.quiz_service = mock_services['quiz_service']
        chatbot.search_service = mock_services['search_service']
        chatbot.content_generator = mock_services['content_generator']
        chatbot.topic_validator = mock_services['topic_validator']
        chatbot.router = mock_services['router']
        
        return chatbot


@pytest.fixture
def sample_messages():
    """Sample messages for testing."""
    return [
        {"role": "user", "content": "How do I use Python decorators?"},
        {"role": "assistant", "content": "Python decorators are functions that modify other functions."}
    ]


class TestDevOpsChatbot:
    @pytest.mark.asyncio
    async def test_validate_first_message_topic_success(self, chatbot, mock_services):
        """Test successful topic validation for first message."""
        message = "How do I use Python decorators?"
        
        result = await chatbot.validate_first_message_topic(message)
        
        # Assertions
        assert result == (True, "Python", "Valid")
        mock_services['topic_validator'].validate_first_message_topic.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_validate_first_message_topic_invalid(self, chatbot, mock_services):
        """Test topic validation failure for first message."""
        message = "What's the weather like?"
        
        # Mock invalid topic
        mock_services['topic_validator'].validate_first_message_topic = AsyncMock(
            return_value=(False, "Weather", "Not programming related")
        )
        
        result = await chatbot.validate_first_message_topic(message)
        
        # Assertions
        assert result == (False, "Weather", "Not programming related")

    @pytest.mark.asyncio
    async def test_process_message_success(self, chatbot, sample_messages):
        """Test successful message processing."""
        conversation_id = "conv123"
        conversation_topic = "Python Programming"
        
        # Mock the graph execution
        mock_result = Mock()
        mock_result.get.return_value = "Here's a response about Python decorators"
        
        chatbot.graph = Mock()
        chatbot.graph.ainvoke = AsyncMock(return_value=mock_result)
        
        result = await chatbot.process_message(
            sample_messages,
            conversation_id,
            conversation_topic
        )
        
        # Assertions
        assert "response" in result
        assert result["response"] == "Here's a response about Python decorators"
        assert "quiz_state" not in result  # Not in quiz mode

    @pytest.mark.asyncio
    async def test_process_message_quiz_mode(self, chatbot, sample_messages):
        """Test message processing in quiz mode."""
        conversation_id = "conv123"
        conversation_topic = "Python Programming"
        is_quiz_mode = True
        quiz_state = {
            "quiz_questions": [{"question": "What is Python?"}],
            "current_quiz_index": 0
        }
        
        # Mock the graph execution with quiz state
        mock_result = Mock()
        mock_result.get.side_effect = lambda key, default=None: {
            "current_response": "Correct!",
            "quiz_questions": quiz_state["quiz_questions"],
            "current_quiz_index": 0,
            "quiz_scores": [],
            "used_quiz_questions": [],
            "is_quiz_mode": True
        }.get(key, default)
        
        chatbot.graph = Mock()
        chatbot.graph.ainvoke = AsyncMock(return_value=mock_result)
        
        result = await chatbot.process_message(
            sample_messages,
            conversation_id,
            conversation_topic,
            is_quiz_mode,
            quiz_state
        )
        
        # Assertions
        assert "response" in result
        assert "quiz_state" in result
        assert result["quiz_state"]["quiz_questions"] == quiz_state["quiz_questions"]
        assert result["quiz_state"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, chatbot, sample_messages):
        """Test error handling in message processing."""
        conversation_id = "conv123"
        conversation_topic = "Python Programming"
        
        # Mock the graph to raise an exception
        chatbot.graph = Mock()
        chatbot.graph.ainvoke = AsyncMock(side_effect=Exception("Graph execution failed"))
        
        result = await chatbot.process_message(
            sample_messages,
            conversation_id,
            conversation_topic
        )
        
        # Should return error message
        assert "response" in result
        assert "error" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_process_message_converts_message_formats(self, chatbot, sample_messages):
        """Test that message formats are properly converted."""
        conversation_id = "conv123"
        conversation_topic = "Python Programming"
        
        # Mock the graph execution
        mock_result = Mock()
        mock_result.get.return_value = "Response"
        
        chatbot.graph = Mock()
        chatbot.graph.ainvoke = AsyncMock(return_value=mock_result)
        
        # Spy on the graph invocation to check message conversion
        await chatbot.process_message(
            sample_messages,
            conversation_id,
            conversation_topic
        )
        
        # Verify the graph was called with converted messages
        chatbot.graph.ainvoke.assert_called_once()
        call_args = chatbot.graph.ainvoke.call_args
        initial_state = call_args[0][0]  # First argument is the initial state
        
        # Check that messages were converted to BaseMessage objects
        assert len(initial_state["messages"]) == 2
        assert isinstance(initial_state["messages"][0], HumanMessage)
        assert isinstance(initial_state["messages"][1], AIMessage)
        assert initial_state["messages"][0].content == "How do I use Python decorators?"

    @pytest.mark.asyncio
    async def test_process_message_sets_initial_state_correctly(self, chatbot, sample_messages):
        """Test that initial state is set correctly for message processing."""
        conversation_id = "conv123"
        conversation_topic = "Python Programming"
        is_quiz_mode = True
        quiz_state = {
            "quiz_questions": [{"question": "Test"}],
            "current_quiz_index": 0
        }
        
        # Mock the graph execution
        mock_result = Mock()
        mock_result.get.return_value = "Response"
        
        chatbot.graph = Mock()
        chatbot.graph.ainvoke = AsyncMock(return_value=mock_result)
        
        await chatbot.process_message(
            sample_messages,
            conversation_id,
            conversation_topic,
            is_quiz_mode,
            quiz_state
        )
        
        # Verify the graph was called with correct initial state
        call_args = chatbot.graph.ainvoke.call_args
        initial_state = call_args[0][0]
        
        # Check state properties
        assert initial_state["topic"] == conversation_topic
        assert initial_state["is_quiz_mode"] is True
        assert initial_state["quiz_questions"] == quiz_state["quiz_questions"]
        assert initial_state["current_quiz_index"] == quiz_state["current_quiz_index"]
        assert initial_state["topic_category_valid"] is True  # Pre-validated topic

    @pytest.mark.asyncio
    async def test_process_message_handles_system_messages(self, chatbot):
        """Test that system messages are handled correctly."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"}
        ]
        conversation_id = "conv123"
        conversation_topic = "General"
        
        # Mock the graph execution
        mock_result = Mock()
        mock_result.get.return_value = "Hello! How can I help you?"
        
        chatbot.graph = Mock()
        chatbot.graph.ainvoke = AsyncMock(return_value=mock_result)
        
        result = await chatbot.process_message(
            messages,
            conversation_id,
            conversation_topic
        )
        
        # Should process successfully
        assert "response" in result
        
        # Verify system message was converted
        call_args = chatbot.graph.ainvoke.call_args
        initial_state = call_args[0][0]
        assert isinstance(initial_state["messages"][0], SystemMessage)
        assert initial_state["messages"][0].content == "You are a helpful assistant"

    def test_initialization_creates_services(self, mock_llm, mock_embeddings):
        """Test that chatbot initialization creates all required services."""
        with patch("app.services.chatbot.core.ChatOpenAI", return_value=mock_llm), \
             patch("app.services.chatbot.core.OpenAIEmbeddings", return_value=mock_embeddings), \
             patch("app.services.chatbot.core.RAGService"), \
             patch("app.services.chatbot.core.MCPWebSearchService"), \
             patch("app.services.chatbot.core.QuizService"), \
             patch("app.services.chatbot.core.SearchService"), \
             patch("app.services.chatbot.core.ContentGenerator"), \
             patch("app.services.chatbot.core.TopicValidator"), \
             patch("app.services.chatbot.core.ConversationRouter"), \
             patch("app.services.chatbot.core.MemorySaver"), \
             patch("app.services.chatbot.core.StateGraph"), \
             patch("app.services.chatbot.core.END"):
            
            chatbot = DevOpsChatbot()
            
            # Verify services were created
            assert hasattr(chatbot, 'rag_service')
            assert hasattr(chatbot, 'mcp_service')
            assert hasattr(chatbot, 'quiz_service')
            assert hasattr(chatbot, 'search_service')
            assert hasattr(chatbot, 'content_generator')
            assert hasattr(chatbot, 'topic_validator')
            assert hasattr(chatbot, 'router')
            assert hasattr(chatbot, 'graph')
