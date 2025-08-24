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
    search_concepts: Optional[str]
    is_first_message: bool
    topic_category_valid: bool
    is_valid: bool

class DevOpsChatbot:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
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
        workflow.add_node("topic_category_validation", self._validate_topic_category)
        workflow.add_node("topic_validation", self._validate_topic)
        workflow.add_node("rag_search", self._rag_search)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("generate_lesson", self._generate_lesson)
        workflow.add_node("generate_response", self._generate_response)
        
        # Add edges
        workflow.set_entry_point("topic_extraction")
        workflow.add_edge("topic_extraction", "topic_category_validation")
        workflow.add_conditional_edges(
            "topic_category_validation",
            self._route_after_category_validation,
            {
                "valid_first": "rag_search",  # First message with valid category
                "valid_subsequent": "topic_validation",  # Subsequent messages
                "invalid": "generate_response"  # Invalid category
            }
        )
        workflow.add_conditional_edges(
            "topic_validation",
            self._route_after_topic_validation,
            {
                "valid": "rag_search",
                "invalid": "generate_response"
            }
        )
        workflow.add_edge("rag_search", "web_search")
        workflow.add_conditional_edges(
            "web_search",
            self._route_after_web_search,
            {
                "lesson": "generate_lesson",
                "response": "generate_response"
            }
        )
        workflow.add_edge("generate_lesson", END)
        workflow.add_edge("generate_response", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    async def validate_first_message_topic(self, message: str) -> tuple[bool, str, str]:
        """
        Validate if a first message is related to allowed topics (Programming/DevOps/AI).
        
        Args:
            message: The user's first message
            
        Returns:
            Tuple of (is_valid, topic, reason)
        """
        try:
            # Extract topic first
            topic_prompt = ChatPromptTemplate.from_messages([
                ("system", "Generate a concise, descriptive topic name (2-4 words max) based on the user's question. Be specific and user-friendly. Examples:\n- 'Jenkins CI/CD' instead of 'cicd'\n- 'Docker Containers' instead of 'docker'\n- 'Kubernetes Deployment' instead of 'kubernetes'\n- 'AWS EC2 Setup' instead of 'aws'\n- 'Terraform Infrastructure' instead of 'terraform'\n- 'Ansible Automation' instead of 'ansible'\n- 'Monitoring & Alerting' instead of 'monitoring'\n- 'Python FastAPI' instead of 'python'\n- 'Machine Learning Basics' instead of 'ml'\nRespond with just the topic name."),
                ("user", "{message}")
            ])
            
            topic_response = await self.llm.ainvoke(
                topic_prompt.format_messages(message=message)
            )
            topic = topic_response.content.strip().strip("'\"")  # Remove quotes and whitespace
            
            # Validate topic category
            validation_prompt = ChatPromptTemplate.from_messages([
                ("system", """Determine if the given topic/question is related to Programming, DevOps, or AI/Machine Learning.
                
                Programming topics include: web development, software engineering, databases, APIs, frameworks, languages (Python, JavaScript, Java, etc.), software architecture, etc.
                
                DevOps topics include: containerization (Docker, Kubernetes), CI/CD, cloud services (AWS, GCP, Azure), infrastructure as code, monitoring, automation, deployment, etc.
                
                AI/ML topics include: machine learning, artificial intelligence, data science, neural networks, deep learning, natural language processing, computer vision, etc.
                
                Respond with 'yes' if the topic falls into any of these categories, 'no' if it doesn't."""),
                ("user", f"Topic: {topic}\nUser message: {message}")
            ])
            
            validation_response = await self.llm.ainvoke(
                validation_prompt.format_messages()
            )
            
            is_valid = validation_response.content.strip().lower() == "yes"
            reason = "Topic is within allowed categories" if is_valid else "Topic is not related to Programming, DevOps, or AI/Machine Learning"
            
            return is_valid, topic, reason
            
        except Exception as e:
            logger.error(f"Error validating first message topic: {e}")
            # Default to invalid on error to be safe
            return False, "Unknown", f"Validation error: {str(e)}"
    
    async def _extract_topic(self, state: ChatState) -> ChatState:
        """Extract or identify the current topic from the conversation"""
        try:
            messages = state["messages"]
            
            # Determine if this is the first message
            state["is_first_message"] = len(messages) == 1
            
            # For new conversations, topic is already pre-validated and set
            # For existing conversations with first message, we still need to extract topic
            if state["is_first_message"] and not state.get("topic"):
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "Generate a concise, descriptive topic name (2-4 words max) based on the user's question. Be specific and user-friendly. Examples:\n- 'Jenkins CI/CD' instead of 'cicd'\n- 'Docker Containers' instead of 'docker'\n- 'Kubernetes Deployment' instead of 'kubernetes'\n- 'AWS EC2 Setup' instead of 'aws'\n- 'Terraform Infrastructure' instead of 'terraform'\n- 'Ansible Automation' instead of 'ansible'\n- 'Monitoring & Alerting' instead of 'monitoring'\n- 'Python FastAPI' instead of 'python'\n- 'Machine Learning Basics' instead of 'ml'\nRespond with just the topic name."),
                    ("user", "{message}")
                ])
                
                response = await self.llm.ainvoke(
                    prompt.format_messages(message=messages[-1].content)
                )
                state["topic"] = response.content.strip().strip("'\"")  # Remove quotes and whitespace
            
            return state
        except Exception as e:
            logger.error(f"Error extracting topic: {e}")
            if not state.get("topic"):
                state["topic"] = "General"
            if "is_first_message" not in state:
                state["is_first_message"] = len(state["messages"]) == 1
            return state
    
    async def _validate_topic_category(self, state: ChatState) -> ChatState:
        """Validate if the topic is in allowed categories (Programming/DevOps/AI)"""
        try:
            messages = state["messages"]
            topic = state.get("topic", "")
            
            if state["is_first_message"]:
                # For new conversations, topic is already pre-validated at endpoint level
                # For existing conversations with first message, still need to validate
                if topic and topic != "General":
                    # Topic already validated at endpoint level
                    state["topic_category_valid"] = True
                else:
                    # Legacy path - validate topic category for first message
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", """Determine if the given topic/question is related to Programming, DevOps, or AI/Machine Learning.
                        
                        Programming topics include: web development, software engineering, databases, APIs, frameworks, languages (Python, JavaScript, Java, etc.), software architecture, etc.
                        
                        DevOps topics include: containerization (Docker, Kubernetes), CI/CD, cloud services (AWS, GCP, Azure), infrastructure as code, monitoring, automation, deployment, etc.
                        
                        AI/ML topics include: machine learning, artificial intelligence, data science, neural networks, deep learning, natural language processing, computer vision, etc.
                        
                        Respond with 'yes' if the topic falls into any of these categories, 'no' if it doesn't."""),
                        ("user", f"Topic: {topic}\nUser message: {messages[-1].content}")
                    ])
                    
                    response = await self.llm.ainvoke(
                        prompt.format_messages()
                    )
                    
                    state["topic_category_valid"] = response.content.strip().lower() == "yes"
            else:
                # For subsequent messages, category is already validated
                state["topic_category_valid"] = True
                
            return state
        except Exception as e:
            logger.error(f"Error validating topic category: {e}")
            # Default to valid to avoid blocking users on error
            state["topic_category_valid"] = True
            return state
        
    async def _validate_topic(self, state: ChatState) -> ChatState:
        """Validate if the message is related to the current topic (for subsequent messages)"""
        messages = state["messages"]
        topic = state.get("topic", "")
        
        # This is only called for subsequent messages
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"Determine if the user's message is related to the topic '{topic}'. Respond with 'yes' or 'no' only."),
            ("user", "{message}")
        ])
        
        response = await self.llm.ainvoke(
            prompt.format_messages(message=messages[-1].content)
        )
        
        state["is_valid"] = response.content.strip().lower() == "yes"
        return state
    
    def _route_after_category_validation(self, state: ChatState) -> str:
        """Route based on topic category validation"""
        if not state.get("topic_category_valid", False):
            return "invalid"
        
        if state["is_first_message"]:
            return "valid_first"
        else:
            return "valid_subsequent"
    
    def _route_after_topic_validation(self, state: ChatState) -> str:
        """Route based on topic validation for subsequent messages"""
        if state.get("is_valid", True):
            return "valid"
        return "invalid"
    
    def _route_after_web_search(self, state: ChatState) -> str:
        """Route to lesson generation for first message, regular response for others"""
        if state["is_first_message"]:
            return "lesson"
        else:
            return "response"
    
    async def _extract_search_concepts(self, query: str, topic: str = "") -> str:
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
            
            response = await self.llm.ainvoke(
                concept_prompt.format_messages()
            )
            
            extracted_concepts = response.content.strip().strip("'\"")
            logger.info(f"Extracted concepts: '{extracted_concepts}' from query: '{query[:50]}...'")
            return extracted_concepts
            
        except Exception as e:
            logger.error(f"Error extracting search concepts: {e}")
            # Fallback to original query if extraction fails
            return query
    
    async def _rag_search(self, state: ChatState) -> ChatState:
        """Search for relevant documents in RAG using preprocessed queries and quality threshold"""
        raw_query = state["messages"][-1].content
        topic = state.get("topic", "")
        
        try:
            # Extract key concepts from conversational query for better semantic search
            search_concepts = await self._extract_search_concepts(raw_query, topic)
            
            # Use semantic search with similarity threshold to ensure quality
            # Only return results that are actually relevant (similarity >= 0.7)
            results = await self.rag_service.search(
                search_concepts, 
                topic=None, 
                limit=5, 
                similarity_threshold=0.7
            )
            state["rag_results"] = results
            logger.info(f"RAG search with concepts '{search_concepts}' returned {len(results)} high-quality results")
            
            # Store the extracted concepts for potential use in web search
            state["search_concepts"] = search_concepts
            
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            state["rag_results"] = []
            state["search_concepts"] = raw_query  # Fallback to raw query
        
        return state
    
    async def _web_search(self, state: ChatState) -> ChatState:
        """Search the web if RAG doesn't have sufficient high-quality information"""
        rag_results = state.get("rag_results", [])
        raw_query = state["messages"][-1].content
        
        # Determine if we need web search based on RAG result quality
        should_search_web = self._should_use_web_search(rag_results, raw_query)
        
        if should_search_web:
            topic = state.get("topic", "")
            
            # Use extracted concepts if available, otherwise use raw query
            search_concepts = state.get("search_concepts", raw_query)
            search_query = f"{topic} {search_concepts}"
            
            try:
                logger.info(f"RAG results insufficient, triggering web search with concepts: '{search_concepts[:50]}...'")
                results = await self.mcp_service.search(search_query)
                state["web_results"] = results
                logger.info(f"Web search returned {len(results)} results")
            except Exception as e:
                logger.error(f"Web search error: {e}")
                state["web_results"] = []
        else:
            logger.info(f"RAG results sufficient, skipping web search for: '{raw_query[:50]}...'")
            state["web_results"] = []
        
        return state
    
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
    
    async def _generate_lesson(self, state: ChatState) -> ChatState:
        """Generate a structured lesson for the first message"""
        messages = state["messages"]
        topic = state.get("topic", "")
        
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
        
        state["current_response"] = response.content
        return state
    
    async def _generate_response(self, state: ChatState) -> ChatState:
        """Generate regular response for subsequent messages or invalid topics"""
        messages = state["messages"]
        topic = state.get("topic", "")
        is_valid = state.get("is_valid", True)
        topic_category_valid = state.get("topic_category_valid", True)
        
        # Handle invalid topic category (first message)
        if state["is_first_message"] and not topic_category_valid:
            state["current_response"] = "I'm sorry, but I can only help with topics related to Programming, DevOps, and AI/Machine Learning. Please ask a question about software development, infrastructure, automation, data science, or related technical topics."
            return state
        
        # Handle invalid topic for subsequent messages
        if not state["is_first_message"] and not is_valid:
            state["current_response"] = f"I'm focused on helping you learn about {topic}. Please ask questions related to this topic. If you'd like to explore a different topic, please start a new conversation."
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
        
        state["current_response"] = response.content
        return state
    
    async def process_message(self, messages: List[Dict[str, str]], conversation_id: str, conversation_topic: str = "") -> str:
        """Process a message through the graph"""
        try:
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
                topic=conversation_topic,  # Use pre-validated topic from conversation
                rag_results=None,
                web_results=None,
                current_response=None,
                search_concepts=None,
                is_first_message=False,
                topic_category_valid=True if conversation_topic else False,  # Pre-validated topics are valid
                is_valid=True
            )
            
            # Run the graph
            config = {"configurable": {"thread_id": conversation_id}}
            result = await self.graph.ainvoke(initial_state, config)
            
            response = result.get("current_response", "I'm sorry, I couldn't generate a response.")
            logger.info(f"Successfully processed message for conversation {conversation_id}")
            return response
            
        except Exception as e:
            logger.exception(f"Error processing message for conversation {conversation_id}: {e}")
            return "I'm sorry, I encountered an error while processing your message. Please try again."
