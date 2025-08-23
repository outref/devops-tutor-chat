import httpx
import os
from typing import List, Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

class MCPWebSearchService:
    def __init__(self):
        self.base_url = os.getenv("MCP_WEB_SEARCH_URL", "http://localhost:3000")
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web using MCP server"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Make request to MCP server
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "query": query,
                        "max_results": max_results
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._format_results(data.get("results", []))
                else:
                    logger.error(f"MCP search failed with status {response.status_code}")
                    return []
                    
            except httpx.ConnectError:
                logger.warning("MCP server not available, using fallback search")
                return await self._fallback_search(query)
            except Exception as e:
                logger.error(f"Error during MCP search: {e}")
                return []
    
    def _format_results(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format MCP search results"""
        formatted = []
        for result in raw_results:
            formatted.append({
                "title": result.get("title", ""),
                "content": result.get("snippet", ""),
                "url": result.get("url", ""),
                "metadata": {
                    "source": "web_search",
                    "url": result.get("url", "")
                }
            })
        return formatted
    
    async def _fallback_search(self, query: str) -> List[Dict[str, Any]]:
        """Fallback search when MCP is not available"""
        # This is a simple fallback that returns predefined DevOps content
        # In a real implementation, you might use another search API
        
        devops_knowledge = {
            "kubernetes": [
                {
                    "title": "Kubernetes Basics",
                    "content": "Kubernetes is an open-source container orchestration platform that automates deploying, scaling, and managing containerized applications.",
                    "metadata": {"source": "fallback"}
                }
            ],
            "docker": [
                {
                    "title": "Docker Fundamentals",
                    "content": "Docker is a platform for developing, shipping, and running applications in containers. Containers package code and dependencies together.",
                    "metadata": {"source": "fallback"}
                }
            ],
            "cicd": [
                {
                    "title": "CI/CD Pipeline",
                    "content": "CI/CD stands for Continuous Integration and Continuous Deployment. It's a method to frequently deliver apps by introducing automation into app development.",
                    "metadata": {"source": "fallback"}
                }
            ],
            "aws": [
                {
                    "title": "AWS Cloud Services",
                    "content": "Amazon Web Services provides on-demand cloud computing platforms and APIs. Key services include EC2, S3, Lambda, and RDS.",
                    "metadata": {"source": "fallback"}
                }
            ],
            "terraform": [
                {
                    "title": "Infrastructure as Code with Terraform",
                    "content": "Terraform is an infrastructure as code tool that lets you define cloud and on-prem resources in human-readable configuration files.",
                    "metadata": {"source": "fallback"}
                }
            ]
        }
        
        # Search for relevant topic in fallback data
        query_lower = query.lower()
        results = []
        
        for topic, content in devops_knowledge.items():
            if topic in query_lower:
                results.extend(content)
        
        return results[:5]  # Limit to 5 results
