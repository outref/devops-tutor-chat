import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import numpy as np

from app.services.rag_service import RAGService
from app.models.document import Document


@pytest.fixture
def mock_embeddings():
    """Mock OpenAI embeddings."""
    embeddings = Mock()
    embeddings.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4, 0.5])
    return embeddings


@pytest.fixture
def rag_service(mock_embeddings):
    """Create RAGService instance with mocked dependencies."""
    return RAGService(mock_embeddings)


@pytest.fixture
def mock_document():
    """Mock document object."""
    document = Mock(spec=Document)
    document.id = "doc123"
    document.title = "Python Tutorial"
    document.content = "Learn Python programming basics"
    document.embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    document.document_metadata = {"topic": "programming", "difficulty": "beginner"}
    return document


@pytest.fixture
def mock_documents_data():
    """Mock documents data for batch operations."""
    return [
        {
            "title": "Python Basics",
            "content": "Python is a programming language...",
            "metadata": {"topic": "programming"}
        },
        {
            "title": "DevOps Introduction",
            "content": "DevOps combines development and operations...",
            "metadata": {"topic": "devops"}
        }
    ]


class TestRAGService:
    @pytest.mark.asyncio
    async def test_add_document_success(self, rag_service, mock_embeddings):
        """Test successfully adding a single document."""
        title = "Python Tutorial"
        content = "Learn Python programming basics"
        topic = "programming"
        metadata = {"difficulty": "beginner"}
        
        with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Mock document creation
            mock_doc = Mock()
            mock_doc.id = "doc123"
            mock_session.add = Mock()
            mock_session.commit = AsyncMock()
            
            # Mock the Document model creation
            with patch("app.services.rag_service.Document", return_value=mock_doc):
                result = await rag_service.add_document(title, content, topic, metadata)
        
        # Assertions
        assert result == "doc123"
        mock_embeddings.aembed_query.assert_called_once_with(content)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_document_error_handling(self, rag_service, mock_embeddings):
        """Test error handling when adding document fails."""
        title = "Python Tutorial"
        content = "Learn Python programming basics"
        topic = "programming"
        
        with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Mock error during commit
            mock_session.commit = AsyncMock(side_effect=Exception("Database error"))
            mock_session.rollback = AsyncMock()
            
            with pytest.raises(Exception, match="Database error"):
                await rag_service.add_document(title, content, topic)
            
            # Verify rollback was called
            mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_documents_batch_success(self, rag_service, mock_embeddings, mock_documents_data):
        """Test successfully adding multiple documents in batch."""
        with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Mock document creation
            mock_doc = Mock()
            mock_doc.id = "doc123"
            mock_session.add = Mock()
            mock_session.commit = AsyncMock()
            
            result = await rag_service.add_documents_batch(mock_documents_data)
        
        # Assertions
        assert len(result) == 2
        assert all(isinstance(doc_id, str) for doc_id in result)
        
        # Verify embeddings were generated for each document
        assert mock_embeddings.aembed_query.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_documents_batch_with_chunking(self, rag_service, mock_embeddings):
        """Test batch document addition with content chunking."""
        long_content = "This is a very long document content. " * 50  # Long content that will be chunked
        
        documents_data = [
            {
                "title": "Long Document",
                "content": long_content,
                "metadata": {"topic": "programming"}
            }
        ]
        
        with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            mock_doc = Mock()
            mock_doc.id = "doc123"
            mock_session.add = Mock()
            mock_session.commit = AsyncMock()
            
            result = await rag_service.add_documents_batch(documents_data)
        
        # Should create multiple chunks for long content
        assert len(result) > 1
        assert mock_embeddings.aembed_query.call_count > 1

    @pytest.mark.asyncio
    async def test_add_documents_batch_error_handling(self, rag_service, mock_embeddings, mock_documents_data):
        """Test error handling when batch document addition fails."""
        with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Mock error during commit
            mock_session.commit = AsyncMock(side_effect=Exception("Batch error"))
            mock_session.rollback = AsyncMock()
            
            with pytest.raises(Exception, match="Batch error"):
                await rag_service.add_documents_batch(mock_documents_data)
            
            # Verify rollback was called
            mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_success(self, rag_service, mock_embeddings, mock_document):
        """Test successful document search."""
        query = "Python programming"
        topic = "programming"
        limit = 3
        similarity_threshold = 0.7
        
        with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Mock query execution
            mock_result = Mock()
            mock_result.all.return_value = [(mock_document, 0.2)]  # Low distance = high similarity
            
            mock_stmt = Mock()
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            with patch("app.services.rag_service.select", return_value=mock_stmt):
                result = await rag_service.search(query, topic, limit, similarity_threshold)
        
        # Assertions
        assert len(result) == 1
        assert result[0]["id"] == "doc123"
        assert result[0]["title"] == "Python Tutorial"
        assert result[0]["similarity"] >= similarity_threshold
        
        # Verify embedding was generated for query
        mock_embeddings.aembed_query.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_search_below_threshold(self, rag_service, mock_embeddings, mock_document):
        """Test search filtering by similarity threshold."""
        query = "Python programming"
        similarity_threshold = 0.9  # High threshold
        
        with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Mock query execution with high distance (low similarity)
            mock_result = Mock()
            mock_result.all.return_value = [(mock_document, 0.5)]  # High distance = low similarity
            
            mock_stmt = Mock()
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            with patch("app.services.rag_service.select", return_value=mock_stmt):
                result = await rag_service.search(query, similarity_threshold=similarity_threshold)
        
        # Should filter out low similarity results
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_search_with_topic_filtering(self, rag_service, mock_embeddings, mock_document):
        """Test search with topic-specific filtering."""
        query = "Python programming"
        topic = "programming"
        
        with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            mock_result = Mock()
            mock_result.all.return_value = [(mock_document, 0.2)]
            
            mock_stmt = Mock()
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            with patch("app.services.rag_service.select", return_value=mock_stmt):
                result = await rag_service.search(query, topic)
        
        # Should return results for the specified topic
        assert len(result) == 1
        assert result[0]["metadata"]["topic"] == "programming"

    @pytest.mark.asyncio
    async def test_search_error_handling(self, rag_service, mock_embeddings):
        """Test error handling when search fails."""
        query = "Python programming"
        
        with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Mock error during execution
            mock_session.execute = AsyncMock(side_effect=Exception("Search error"))
            
            result = await rag_service.search(query)
        
        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_search_limit_enforcement(self, rag_service, mock_embeddings, mock_document):
        """Test that search respects the result limit."""
        query = "Python programming"
        limit = 2
        
        # Create multiple mock documents
        mock_docs = []
        for i in range(5):
            doc = Mock(spec=Document)
            doc.id = f"doc{i}"
            doc.title = f"Document {i}"
            doc.content = f"Content {i}"
            doc.document_metadata = {}
            mock_docs.append((doc, 0.1))  # High similarity
        
        with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            mock_result = Mock()
            mock_result.all.return_value = mock_docs
            
            mock_stmt = Mock()
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            with patch("app.services.rag_service.select", return_value=mock_stmt):
                result = await rag_service.search(query, limit=limit)
        
        # Should respect the limit
        assert len(result) == limit

    def test_text_splitter_initialization(self, mock_embeddings):
        """Test that text splitter is properly initialized."""
        rag_service = RAGService(mock_embeddings)
        
        # Verify text splitter configuration
        assert rag_service.text_splitter._chunk_size == 1000
        assert rag_service.text_splitter._chunk_overlap == 200
        assert "\n\n" in rag_service.text_splitter._separators
