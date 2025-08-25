import httpx
import os
from typing import List, Dict, Any, Optional
import logging
import json
import uuid

logger = logging.getLogger(__name__)

class MCPWebSearchService:
    """
    MCP (Model Context Protocol) client for web-search-mcp server.
    Implements JSON-RPC 2.0 protocol for communication.
    """
    
    def __init__(self):
        self.base_url = os.getenv("MCP_SERVER_URL", "http://web-search-mcp:3000")
        self.timeout = httpx.Timeout(45.0, connect=5.0)
        
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search the web using web-search-mcp server.
        
        Args:
            query: Search query
            max_results: Number of results to return (1-10)
            
        Returns:
            List of formatted search results with content
        """
        try:
            # Use the full-web-search tool for comprehensive results
            results = await self._call_mcp_tool(
                "full-web-search",
                {
                    "query": query,
                    "limit": min(max_results, 10),  # Tool limit is 10
                    "includeContent": True
                }
            )
            
            if results:
                return self._format_results(results)
            else:
                logger.warning(f"No results found for query: {query}")
                return []
                
        except Exception as e:
            logger.error(f"Error during MCP search: {e}")
            return []
    

    

    
    async def _call_mcp_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Call an MCP tool using JSON-RPC 2.0 protocol.
        
        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool
            
        Returns:
            Tool response or None if error
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Build JSON-RPC 2.0 request
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params
            },
            "id": request_id
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Send request to MCP server
                response = await client.post(
                    self.base_url,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Check for JSON-RPC error
                    if "error" in response_data:
                        logger.error(f"MCP error: {response_data['error']}")
                        return None
                    
                    # Extract result
                    result = response_data.get("result")
                    if result and isinstance(result, dict):
                        # Handle the tool response content
                        content = result.get("content")
                        if content:
                            # If content is a string, try to parse it as JSON
                            if isinstance(content, str):
                                try:
                                    return json.loads(content)
                                except json.JSONDecodeError:
                                    return {"content": content}
                            return content
                    return result
                else:
                    logger.error(f"MCP request failed with status {response.status_code}")
                    return None
                    
            except httpx.ConnectError:
                logger.error("Failed to connect to MCP server")
                raise
            except Exception as e:
                logger.error(f"Unexpected error calling MCP tool: {e}")
                raise
    
    def _format_results(self, mcp_response: Any) -> List[Dict[str, Any]]:
        """
        Format full search results from web-search-mcp.
        
        Args:
            mcp_response: Raw response from MCP server
            
        Returns:
            List of formatted search results
        """
        formatted_results = []
        
        # Handle different response structures
        if isinstance(mcp_response, dict):
            results = mcp_response.get("results", [])
        elif isinstance(mcp_response, list):
            results = mcp_response
        else:
            logger.warning(f"Unexpected response type: {type(mcp_response)}")
            return []
        
        for result in results:
            formatted_result = {
                "title": result.get("title", ""),
                "content": result.get("content", result.get("snippet", "")),
                "url": result.get("url", ""),
                "metadata": {
                    "source": "web_search",
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", "")
                }
            }
            formatted_results.append(formatted_result)
        
        return formatted_results
    
