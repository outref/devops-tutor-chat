import os
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.chatbot.core import DevOpsChatbot


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.rollback = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_chatbot():
    """Mock chatbot instance."""
    chatbot = Mock(spec=DevOpsChatbot)
    chatbot.validate_first_message_topic = AsyncMock(return_value=(True, "Programming", "Valid topic"))
    chatbot.process_message = AsyncMock(return_value={
        "response": "Mock response",
        "quiz_state": None
    })
    return chatbot


# Set test environment variables
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
os.environ.setdefault("MCP_SERVER_URL", "http://test-mcp:3000")

