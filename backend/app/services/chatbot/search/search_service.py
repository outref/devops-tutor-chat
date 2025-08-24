from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.services.rag_service import RAGService
from app.services.mcp_service import MCPWebSearchService
import logging

logger = logging.getLogger(__name__)


class SearchService:
    """Service for handling RAG and web search operations"""
    
    def __init__(self, rag_service: RAGService, mcp_service: MCPWebSearchService, llm: ChatOpenAI):
        self.rag_service = rag_service
        self.mcp_service = mcp_service
        self.llm = llm
    
    async def extract_search_concepts(self, query: str, topic: str = "") -> str:
        """
        Extract key concepts from conversational query for better RAG search.
        
        Args:
            query: Raw user query with conversational elements
            topic: Current conversation topic for context
            
        Returns:
            Cleaned query with key concepts for semantic search
        """
        try:
            # Create a focused prompt to extract search concepts
            concept_prompt = ChatPromptTemplate.from_messages([
                ("system", """Extract the key technical concepts and topics from the user's question that would be most relevant for searching technical documentation.

Remove conversational elements like:
- Politeness ("please", "can you", "could you")
- Question words ("what is", "how does", "why do")  
- Personal context ("I'm new to", "I heard that")
- Filler words and unnecessary context

Focus on:
- Technical terms and concepts
- Specific technologies, tools, frameworks
- Key processes or methodologies
- Important keywords

Examples:
Input: "Can you please explain how Docker containers work?"
Output: "Docker containers architecture functionality"

Input: "I'm new to programming. What is React and how do I use it?"
Output: "React JavaScript library components usage"

Input: "Could you help me understand CI/CD pipelines in Jenkins?"
Output: "CI/CD pipelines Jenkins automation deployment"

Return only the key concepts as a concise phrase (2-8 words max)."""),
                ("user", f"Topic context: {topic}\nUser query: {query}")
            ])
            
            response = await self.llm.ainvoke(concept_prompt.format_messages())
            
            extracted_concepts = response.content.strip().strip("'\"")
            logger.info(f"Extracted concepts: '{extracted_concepts}' from query: '{query[:50]}...'")
            return extracted_concepts
            
        except Exception as e:
            logger.error(f"Error extracting search concepts: {e}")
            # Fallback to original query if extraction fails
            return query
    
    async def rag_search(self, query: str, topic: str = "") -> List[Dict[str, Any]]:
        """Search for relevant documents in RAG using preprocessed queries and quality threshold"""
        try:
            # Extract key concepts from conversational query for better semantic search
            search_concepts = await self.extract_search_concepts(query, topic)
            
            # Use semantic search with similarity threshold to ensure quality
            # Only return results that are actually relevant (similarity >= 0.7)
            results = await self.rag_service.search(
                search_concepts, 
                topic=None, 
                limit=5, 
                similarity_threshold=0.7
            )
            logger.info(f"RAG search with concepts '{search_concepts}' returned {len(results)} high-quality results")
            
            return results
            
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return []  # Return empty results on error
    
    async def web_search(self, query: str, topic: str, rag_results: List[Dict[str, Any]], 
                        search_concepts: str) -> List[Dict[str, Any]]:
        """Search the web if RAG doesn't have sufficient high-quality information"""
        # Determine if we need web search based on RAG result quality
        should_search_web = self._should_use_web_search(rag_results, query)
        
        if should_search_web:
            # Use extracted concepts if available, otherwise use raw query
            search_query = f"{topic} {search_concepts}"
            
            try:
                logger.info(f"RAG results insufficient, triggering web search with concepts: '{search_concepts[:50]}...'")
                results = await self.mcp_service.search(search_query)
                logger.info(f"Web search returned {len(results)} results")
                return results
            except Exception as e:
                logger.error(f"Web search error: {e}")
                return []
        else:
            logger.info(f"RAG results sufficient, skipping web search for: '{query[:50]}...'")
            return []
    
    def _should_use_web_search(self, rag_results: List[Dict[str, Any]], query: str) -> bool:
        """
        Determine if web search should be used based on RAG result quality.
        
        Args:
            rag_results: Results from RAG search
            query: Original user query
            
        Returns:
            True if web search should be used, False otherwise
        """
        # No RAG results means we definitely need web search
        if not rag_results:
            logger.info("No RAG results found, web search needed")
            return True
        
        # Check if we have enough high-quality results
        min_results_needed = 2
        if len(rag_results) < min_results_needed:
            logger.info(f"Only {len(rag_results)} high-quality RAG results found (need {min_results_needed}), web search needed")
            return True
        
        # Check average similarity score
        similarities = [result.get("similarity", 0) for result in rag_results]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        min_avg_similarity = 0.75
        
        if avg_similarity < min_avg_similarity:
            logger.info(f"Average RAG similarity {avg_similarity:.3f} below threshold {min_avg_similarity}, web search needed")
            return True
        
        # Check if the best result is high quality enough
        best_similarity = max(similarities) if similarities else 0
        min_best_similarity = 0.8
        
        if best_similarity < min_best_similarity:
            logger.info(f"Best RAG similarity {best_similarity:.3f} below threshold {min_best_similarity}, web search needed")
            return True
        
        logger.info(f"RAG results sufficient: {len(rag_results)} results, avg similarity {avg_similarity:.3f}, best similarity {best_similarity:.3f}")
        return False
    
    async def search_with_fallback(self, query: str, topic: str = "") -> Dict[str, Any]:
        """Perform RAG search with web fallback if needed"""
        # First, extract search concepts and perform RAG search
        search_concepts = await self.extract_search_concepts(query, topic)
        rag_results = await self.rag_search(query, topic)
        
        # Then, determine if web search is needed and perform it
        web_results = await self.web_search(query, topic, rag_results, search_concepts)
        
        return {
            "rag_results": rag_results,
            "web_results": web_results,
            "search_concepts": search_concepts
        }
