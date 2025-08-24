from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage
import logging

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Service for generating lesson content and conversational responses"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    async def generate_lesson(self, messages: List[BaseMessage], topic: str, 
                            rag_results: List[Dict[str, Any]] = None, 
                            web_results: List[Dict[str, Any]] = None) -> str:
        """Generate a structured lesson for the first message"""
        # Build context from RAG and web results
        context_parts = []
        
        if rag_results:
            context_parts.append("From our knowledge base:")
            for result in rag_results[:3]:
                context_parts.append(f"- {result['content']}")
        
        if web_results:
            context_parts.append("\nFrom web search:")
            for result in web_results[:3]:
                context_parts.append(f"- {result['content']}")
        
        context = "\n".join(context_parts) if context_parts else "No specific context found."
        
        # Generate structured lesson
        # Create the full system message without template variables to avoid parsing issues
        full_system_message = """You are an expert learning assistant specializing in Programming, DevOps, and AI topics. 
        Create a well-structured educational lesson about the requested topic.
        
        Requirements:
        - Provide an in-depth lesson (7-10 paragraphs) with detailed explanations, examples, and best practices
        - Use clear headings and structure (## for main sections)
        - Include practical examples and code snippets where relevant
        - Focus on hands-on learning and real-world applications
        - End with actionable next steps or practice suggestions
        
        Context for reference:
        """ + context
        
        # Create messages directly to avoid template parsing issues
        messages_for_llm = [
            {"role": "system", "content": full_system_message},
            {"role": "user", "content": f"Create a lesson about: {messages[-1].content}"}
        ]
        
        response = await self.llm.ainvoke(messages_for_llm)
        return response.content
    
    async def generate_response(self, messages: List[BaseMessage], topic: str, 
                              rag_results: List[Dict[str, Any]] = None, 
                              web_results: List[Dict[str, Any]] = None,
                              is_valid: bool = True, 
                              topic_category_valid: bool = True,
                              is_first_message: bool = False) -> str:
        """Generate regular response for subsequent messages or invalid topics"""
        # Handle invalid topic category (first message)
        if is_first_message and not topic_category_valid:
            return "I'm sorry, but I can only help with topics related to Programming, DevOps, and AI/Machine Learning. Please ask a question about software development, infrastructure, automation, data science, or related technical topics."
        
        # Handle invalid topic for subsequent messages
        if not is_first_message and not is_valid:
            return f"I'm focused on helping you learn about {topic}. Please ask questions related to this topic. If you'd like to explore a different topic, please start a new conversation."
        
        # Build context from RAG and web results
        context_parts = []
        
        if rag_results:
            context_parts.append("From our knowledge base:")
            for result in rag_results[:3]:
                context_parts.append(f"- {result['content']}")
        
        if web_results:
            context_parts.append("\nFrom web search:")
            for result in web_results[:3]:
                context_parts.append(f"- {result['content']}")
        
        context = "\n".join(context_parts) if context_parts else "No specific context found."
        
        # Generate conversational response  
        full_system_message = "You are a helpful learning assistant focused on " + topic + """.
        Use the provided context to give accurate and educational responses.
        Answer the user's question directly and provide practical insights.
        Stay focused on """ + topic + """ and related concepts.
        
        Context:
        """ + context
        
        # Create messages directly to avoid template parsing issues
        messages_for_llm = [
            {"role": "system", "content": full_system_message}
        ]
        
        # Add message history
        history = messages[:-1] if len(messages) > 1 else []
        for msg in history:
            if isinstance(msg, HumanMessage):
                messages_for_llm.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages_for_llm.append({"role": "assistant", "content": msg.content})
        
        # Add current user message
        messages_for_llm.append({"role": "user", "content": messages[-1].content})
        
        response = await self.llm.ainvoke(messages_for_llm)
        return response.content
