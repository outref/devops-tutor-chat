import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx
import json

from app.services.mcp_service import MCPWebSearchService


@pytest.fixture
def mcp_service():
    """Create MCPWebSearchService instance."""
    return MCPWebSearchService()


@pytest.fixture
def mock_search_response():
    """Mock search response data."""
    return {
        "results": [
            {
                "title": "Python Decorators Tutorial",
                "content": "Learn how to use Python decorators effectively",
                "url": "https://example.com/python-decorators",
                "snippet": "Python decorators are a powerful feature..."
            },
            {
                "title": "DevOps Best Practices",
                "content": "Essential DevOps practices for modern development",
                "url": "https://example.com/devops-practices",
                "snippet": "DevOps combines development and operations..."
            }
        ]
    }


class TestMCPWebSearchService:
    @pytest.mark.asyncio
    async def test_search_success(self, mcp_service, mock_search_response):
        """Test successful web search."""
        query = "Python decorators"
        max_results = 3
        
        with patch.object(mcp_service, '_call_mcp_tool', new=AsyncMock(return_value=mock_search_response)) as mock_call:
            result = await mcp_service.search(query, max_results)
        
        # Assertions
        assert len(result) == 2
        assert result[0]["title"] == "Python Decorators Tutorial"
        assert result[0]["url"] == "https://example.com/python-decorators"
        assert result[0]["metadata"]["source"] == "web_search"
        
        # Verify MCP tool was called correctly
        mock_call.assert_called_once_with(
            "full-web-search",
            {
                "query": query,
                "limit": 3,
                "includeContent": True
            }
        )

    @pytest.mark.asyncio
    async def test_search_max_results_limit(self, mcp_service, mock_search_response):
        """Test that max_results is limited to 10."""
        query = "Python decorators"
        max_results = 15  # Exceeds tool limit
        
        with patch.object(mcp_service, '_call_mcp_tool', new=AsyncMock(return_value=mock_search_response)) as mock_call:
            result = await mcp_service.search(query, max_results)
        
        # Verify limit was applied
        mock_call.assert_called_once_with(
            "full-web-search",
            {
                "query": query,
                "limit": 10,  # Should be capped at 10
                "includeContent": True
            }
        )

    @pytest.mark.asyncio
    async def test_search_no_results(self, mcp_service):
        """Test search when no results are returned."""
        query = "nonexistent topic"
        
        with patch.object(mcp_service, '_call_mcp_tool', new=AsyncMock(return_value=None)) as mock_call:
            result = await mcp_service.search(query)
        
        # Assertions
        assert result == []
        mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_exception_handling(self, mcp_service):
        """Test search error handling."""
        query = "Python decorators"
        
        with patch.object(mcp_service, '_call_mcp_tool', new=AsyncMock(side_effect=Exception("MCP error"))):
            result = await mcp_service.search(query)
        
        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_call_mcp_tool_success(self, mcp_service):
        """Test successful MCP tool call."""
        tool_name = "full-web-search"
        params = {"query": "test", "limit": 5}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "content": json.dumps({"results": [{"title": "Test", "url": "https://test.com"}]})
            }
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await mcp_service._call_mcp_tool(tool_name, params)
        
        # Assertions
        assert result is not None
        assert "results" in result
        assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_call_mcp_tool_http_error(self, mcp_service):
        """Test MCP tool call with HTTP error."""
        tool_name = "full-web-search"
        params = {"query": "test"}
        
        mock_response = Mock()
        mock_response.status_code = 500
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await mcp_service._call_mcp_tool(tool_name, params)
        
        # Should return None on HTTP error
        assert result is None

    @pytest.mark.asyncio
    async def test_call_mcp_tool_mcp_error(self, mcp_service):
        """Test MCP tool call with MCP protocol error."""
        tool_name = "full-web-search"
        params = {"query": "test"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": {"code": -1, "message": "Tool not found"}
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await mcp_service._call_mcp_tool(tool_name, params)
        
        # Should return None on MCP error
        assert result is None

    @pytest.mark.asyncio
    async def test_call_mcp_tool_connection_error(self, mcp_service):
        """Test MCP tool call with connection error."""
        tool_name = "full-web-search"
        params = {"query": "test"}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )
            
            with pytest.raises(httpx.ConnectError):
                await mcp_service._call_mcp_tool(tool_name, params)

    @pytest.mark.asyncio
    async def test_call_mcp_tool_content_parsing(self, mcp_service):
        """Test MCP tool call with different content formats."""
        tool_name = "full-web-search"
        params = {"query": "test"}
        
        # Test with string content that needs JSON parsing
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "content": '{"results": [{"title": "Test"}]}'
            }
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await mcp_service._call_mcp_tool(tool_name, params)
        
        # Should parse JSON content
        assert result["results"][0]["title"] == "Test"

    def test_format_results_dict_response(self, mcp_service, mock_search_response):
        """Test formatting results from dict response."""
        result = mcp_service._format_results(mock_search_response)
        
        # Assertions
        assert len(result) == 2
        assert result[0]["title"] == "Python Decorators Tutorial"
        assert result[0]["content"] == "Learn how to use Python decorators effectively"
        assert result[0]["url"] == "https://example.com/python-decorators"
        assert result[0]["metadata"]["source"] == "web_search"

    def test_format_results_list_response(self, mcp_service):
        """Test formatting results from list response."""
        list_response = [
            {
                "title": "Test Title",
                "content": "Test content",
                "url": "https://test.com"
            }
        ]
        
        result = mcp_service._format_results(list_response)
        
        # Assertions
        assert len(result) == 1
        assert result[0]["title"] == "Test Title"
        assert result[0]["content"] == "Test content"

    def test_format_results_unexpected_type(self, mcp_service):
        """Test formatting results with unexpected response type."""
        unexpected_response = "not a dict or list"
        
        result = mcp_service._format_results(unexpected_response)
        
        # Should return empty list for unexpected types
        assert result == []

    def test_format_results_missing_fields(self, mcp_service):
        """Test formatting results with missing fields."""
        incomplete_response = {
            "results": [
                {
                    "title": "Test Title"
                    # Missing content, url, etc.
                }
            ]
        }
        
        result = mcp_service._format_results(incomplete_response)
        
        # Should handle missing fields gracefully
        assert len(result) == 1
        assert result[0]["title"] == "Test Title"
        assert result[0]["content"] == ""  # Default empty string
        assert result[0]["url"] == ""  # Default empty string
