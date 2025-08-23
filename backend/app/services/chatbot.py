from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver
import os
import logging
from app.services.rag_service import RAGService
from app.services.mcp_service import MCPWebSearchService

logger = logging.getLogger(__name__)

# Define state for the graph
class ChatState(dict):
    messages: List[BaseMessage]
    topic: str
    rag_results: Optional[List[Dict[str, Any]]]
    web_results: Optional[List[Dict[str, Any]]]
    current_response: Optional[str]

class DevOpsChatbot:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
        self.rag_service = RAGService(self.embeddings)
        self.mcp_service = MCPWebSearchService()
        self.memory = MemorySaver()
        
        # Build the graph
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ChatState)
        
        # Add nodes
        workflow.add_node("topic_extraction", self._extract_topic)
        workflow.add_node("topic_validation", self._validate_topic)
        workflow.add_node("rag_search", self._rag_search)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("generate_response", self._generate_response)
        
        # Add edges
        workflow.set_entry_point("topic_extraction")
        workflow.add_edge("topic_extraction", "topic_validation")
        workflow.add_conditional_edges(
            "topic_validation",
            self._route_after_validation,
            {
                "valid": "rag_search",
                "invalid": "generate_response"
            }
        )
        workflow.add_edge("rag_search", "web_search")
        workflow.add_edge("web_search", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    async def _extract_topic(self, state: ChatState) -> ChatState:
        """Extract or identify the current topic from the conversation"""
        messages = state["messages"]
        
        # If this is the first message, extract topic
        if len(messages) == 1:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Extract the main DevOps topic from the user's message. Topics include: kubernetes, docker, cicd, aws, gcloud, terraform, ansible, monitoring, etc. Respond with just the topic name."),
                ("user", "{message}")
            ])
            
            response = await self.llm.ainvoke(
                prompt.format_messages(message=messages[-1].content)
            )
            state["topic"] = response.content.strip().lower()
        
        return state
    
    async def _validate_topic(self, state: ChatState) -> ChatState:
        """Validate if the message is related to the current topic"""
        messages = state["messages"]
        topic = state.get("topic", "")
        
        # For first message, always valid if topic extracted
        if len(messages) == 1 and topic:
            return state
        
        # For subsequent messages, check if related to topic
        if len(messages) > 1:
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"Determine if the user's message is related to the DevOps topic '{topic}'. Respond with 'yes' or 'no' only."),
                ("user", "{message}")
            ])
            
            response = await self.llm.ainvoke(
                prompt.format_messages(message=messages[-1].content)
            )
            
            state["is_valid"] = response.content.strip().lower() == "yes"
        else:
            state["is_valid"] = True
            
        return state
    
    def _route_after_validation(self, state: ChatState) -> str:
        """Route based on topic validation"""
        if state.get("is_valid", True):
            return "valid"
        return "invalid"
    
    async def _rag_search(self, state: ChatState) -> ChatState:
        """Search for relevant documents in RAG"""
        topic = state.get("topic", "")
        query = state["messages"][-1].content
        
        try:
            results = await self.rag_service.search(query, topic)
            state["rag_results"] = results
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            state["rag_results"] = []
        
        return state
    
    async def _web_search(self, state: ChatState) -> ChatState:
        """Search the web if RAG doesn't have enough information"""
        rag_results = state.get("rag_results", [])
        
        # Only search web if RAG results are insufficient
        if not rag_results or len(rag_results) < 2:
            topic = state.get("topic", "")
            query = f"{topic} {state['messages'][-1].content}"
            
            try:
                results = await self.mcp_service.search(query)
                state["web_results"] = results
            except Exception as e:
                logger.error(f"Web search error: {e}")
                state["web_results"] = []
        else:
            state["web_results"] = []
        
        return state
    
    async def _generate_response(self, state: ChatState) -> ChatState:
        """Generate the final response"""
        messages = state["messages"]
        topic = state.get("topic", "")
        is_valid = state.get("is_valid", True)
        
        # Handle invalid topic
        if not is_valid:
            state["current_response"] = f"I'm focused on helping you learn about {topic}. Please ask questions related to this topic. If you'd like to explore a different DevOps topic, please start a new conversation."
            return state
        
        # Build context from RAG and web results
        context_parts = []
        
        if state.get("rag_results"):
            context_parts.append("From our knowledge base:")
            for result in state["rag_results"][:3]:
                context_parts.append(f"- {result['content']}")
        
        if state.get("web_results"):
            context_parts.append("\nFrom web search:")
            for result in state["web_results"][:3]:
                context_parts.append(f"- {result['content']}")
        
        context = "\n".join(context_parts) if context_parts else "No specific context found."
        
        # Generate response
        system_prompt = f"""You are a helpful DevOps learning assistant focused on the topic of {topic}.
        Use the provided context to give accurate and educational responses.
        If this is the first interaction, provide a brief lesson about {topic}.
        Always stay focused on {topic} and related DevOps concepts.
        
        Context:
        {context}"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{input}")
        ])
        
        # Prepare message history
        history = messages[:-1] if len(messages) > 1 else []
        
        response = await self.llm.ainvoke(
            prompt.format_messages(
                history=history,
                input=messages[-1].content
            )
        )
        
        state["current_response"] = response.content
        return state
    
    async def process_message(self, messages: List[Dict[str, str]], conversation_id: str) -> str:
        """Process a message through the graph"""
        # Convert messages to BaseMessage objects
        base_messages = []
        for msg in messages:
            if msg["role"] == "user":
                base_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                base_messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                base_messages.append(SystemMessage(content=msg["content"]))
        
        # Create initial state
        initial_state = ChatState(
            messages=base_messages,
            topic="",
            rag_results=None,
            web_results=None,
            current_response=None
        )
        
        # Run the graph
        config = {"configurable": {"thread_id": conversation_id}}
        result = await self.graph.ainvoke(initial_state, config)
        
        return result.get("current_response", "I'm sorry, I couldn't generate a response.")
