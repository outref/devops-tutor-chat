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
    # Quiz-related state
    is_quiz_mode: bool
    quiz_questions: Optional[List[Dict[str, Any]]]
    current_quiz_index: Optional[int]
    quiz_scores: Optional[List[Dict[str, Any]]]
    used_quiz_questions: Optional[List[str]]  # Track questions asked across sessions

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
        # Quiz nodes
        workflow.add_node("generate_quiz_questions", self._generate_quiz_questions)
        workflow.add_node("process_quiz_answer", self._process_quiz_answer)
        
        # Set entry point and add conditional routing
        workflow.set_entry_point("topic_extraction")
        
        workflow.add_edge("topic_extraction", "topic_category_validation")
        workflow.add_conditional_edges(
            "topic_category_validation",
            self._route_after_category_validation,
            {
                "valid_first": "rag_search",  # First message with valid category
                "valid_subsequent": "topic_validation",  # Subsequent messages
                "invalid": "generate_response",  # Invalid category
                "quiz_generation": "generate_quiz_questions",  # Start quiz
                "quiz_answer": "process_quiz_answer"  # Process quiz answer
            }
        )
        workflow.add_conditional_edges(
            "topic_validation",
            self._route_after_topic_validation,
            {
                "valid": "rag_search",
                "invalid": "generate_response",
                "quiz_generation": "generate_quiz_questions",
                "quiz_answer": "process_quiz_answer"
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
        workflow.add_edge("generate_quiz_questions", END)
        workflow.add_edge("process_quiz_answer", END)
        
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
            
            # Skip topic extraction if we're in quiz mode - topic is already set
            if state.get("is_quiz_mode", False):
                return state
            
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
            
            # Skip validation if we're in quiz mode - topic is already validated
            if state.get("is_quiz_mode", False):
                state["topic_category_valid"] = True
                return state
            
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
        
        # Skip validation if we're in quiz mode - quiz answers should always be considered valid
        if state.get("is_quiz_mode", False):
            state["is_valid"] = True
            return state
        
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
        # Check for quiz mode first
        is_quiz_mode = state.get("is_quiz_mode", False)
        has_questions = state.get("quiz_questions") is not None
        has_index = state.get("current_quiz_index") is not None
        
        logger.info(f"Routing after category validation - Quiz mode: {is_quiz_mode}, Has questions: {has_questions}, Has index: {has_index}")
        
        if is_quiz_mode:
            if has_questions and has_index:
                logger.info("Routing to quiz_answer")
                return "quiz_answer"
            else:
                logger.info("Routing to quiz_generation")
                return "quiz_generation"
        
        if not state.get("topic_category_valid", False):
            logger.info("Routing to invalid - topic category not valid")
            return "invalid"
        
        if state["is_first_message"]:
            logger.info("Routing to valid_first")
            return "valid_first"
        else:
            logger.info("Routing to valid_subsequent")
            return "valid_subsequent"
    
    def _route_after_topic_validation(self, state: ChatState) -> str:
        """Route based on topic validation for subsequent messages"""
        # Check for quiz mode first
        is_quiz_mode = state.get("is_quiz_mode", False)
        has_questions = state.get("quiz_questions") is not None
        has_index = state.get("current_quiz_index") is not None
        
        logger.info(f"Routing after topic validation - Quiz mode: {is_quiz_mode}, Has questions: {has_questions}, Has index: {has_index}")
        
        if is_quiz_mode:
            if has_questions and has_index:
                logger.info("Routing to quiz_answer from topic validation")
                return "quiz_answer"
            else:
                logger.info("Routing to quiz_generation from topic validation")
                return "quiz_generation"
                
        if state.get("is_valid", True):
            logger.info("Routing to valid")
            return "valid"
        logger.info("Routing to invalid - topic not valid")
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
    
    async def _generate_quiz_questions(self, state: ChatState) -> ChatState:
        """Generate quiz questions based on conversation history"""
        messages = state["messages"]
        topic = state.get("topic", "")
        used_questions = state.get("used_quiz_questions", [])
        
        # Also try to get used questions from previous messages in the conversation
        for msg in messages:
            if isinstance(msg, AIMessage) and "Quiz Complete!" in getattr(msg, 'content', ''):
                # This was a completed quiz - try to extract questions that were asked
                continue
        
        logger.info(f"Starting quiz generation with {len(used_questions)} previously used questions")
        
        # Build conversation context
        conversation_history = []
        for msg in messages[:-1]:  # Exclude the quiz request message
            if isinstance(msg, HumanMessage):
                conversation_history.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                conversation_history.append(f"Assistant: {msg.content[:200]}...")  # Truncate long responses
        
        context = "\n".join(conversation_history)
        
        # Generate quiz questions
        quiz_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are creating an interactive quiz based on the conversation history. You MUST respond with ONLY a valid JSON array, nothing else.

Generate 5 COMPLETELY DIFFERENT quiz questions that test understanding of the concepts discussed.

CRITICAL REQUIREMENTS:
- Questions MUST be directly related to what was discussed in the conversation
- Create DIVERSE questions covering different aspects of the topic
- Mix question types: multiple choice, true/false, and short answer
- Test understanding and application, NOT just memorization
- Questions should be SIGNIFICANTLY DIFFERENT from any previously asked questions

AVOID REPETITION: Do NOT create questions similar to previously asked ones. If previous questions exist, create questions about different aspects, use different wording, focus on different concepts, or ask about related but distinct topics.

JSON FORMAT REQUIRED:
[
  {{
    "question": "What is the main purpose of Docker containers?",
    "type": "multiple_choice", 
    "options": ["Virtual machine replacement", "Application containerization", "Network management", "Storage solutions"],
    "correct_answer": "Application containerization",
    "explanation": "Docker containers provide lightweight containerization for applications."
  }}
]

CRITICAL: 
- For multiple choice: options array MUST contain ONLY plain text, NO letter prefixes like "A.", "B.", "C.", "D."
- WRONG: "options": ["A. Virtual machines", "B. Containers"] 
- CORRECT: "options": ["Virtual machines", "Containers"]

Return ONLY the JSON array. No explanations, no markdown, no code blocks.

Previously asked questions to AVOID repeating:
""" + ("\n- " + "\n- ".join(used_questions) if used_questions else "None")),
            ("user", f"Topic: {topic}\n\nConversation History:\n{context}\n\nGenerate 5 NEW and DIFFERENT quiz questions as JSON:")
        ])
        
        response = await self.llm.ainvoke(
            quiz_prompt.format_messages()
        )
        
        try:
            import json
            import re
            
            # Log the raw response for debugging
            logger.info(f"Raw quiz generation response: {response.content[:500]}...")
            
            # Extract JSON from response with multiple strategies
            json_str = response.content.strip()
            
            # Strategy 1: Look for JSON code block
            if "```json" in json_str.lower():
                json_match = re.search(r'```json\s*(.*?)\s*```', json_str, re.DOTALL | re.IGNORECASE)
                if json_match:
                    json_str = json_match.group(1).strip()
            elif "```" in json_str:
                json_match = re.search(r'```\s*(.*?)\s*```', json_str, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
            
            # Strategy 2: Look for array starting with [
            if not json_str.startswith('['):
                array_match = re.search(r'\[.*\]', json_str, re.DOTALL)
                if array_match:
                    json_str = array_match.group(0)
            
            logger.info(f"Extracted JSON string: {json_str[:200]}...")
            
            # Parse JSON
            quiz_questions = json.loads(json_str)
            
            # Validate structure
            if not isinstance(quiz_questions, list):
                raise ValueError("Quiz questions should be a list")
            
            if len(quiz_questions) == 0:
                raise ValueError("No quiz questions generated")
            
            # Ensure we have at most 5 questions
            if len(quiz_questions) > 5:
                quiz_questions = quiz_questions[:5]
            
            # Validate and normalize each question
            for i, q in enumerate(quiz_questions):
                if not isinstance(q, dict):
                    raise ValueError(f"Question {i+1} is not a dictionary")
                if "question" not in q:
                    raise ValueError(f"Question {i+1} missing 'question' field")
                
                # Normalize field names and add missing fields
                if "answer" in q and "correct_answer" not in q:
                    q["correct_answer"] = q["answer"]
                    del q["answer"]
                
                if "correct_answer" not in q:
                    raise ValueError(f"Question {i+1} missing answer field")
                
                # Add type based on presence of options
                if "type" not in q:
                    if "options" in q and len(q.get("options", [])) > 0:
                        q["type"] = "multiple_choice"
                    else:
                        q["type"] = "short_answer"
                
                # Randomize multiple choice options to distribute correct answers
                if q["type"] == "multiple_choice" and "options" in q:
                    import random
                    import re
                    options = q["options"]
                    correct_text = q["correct_answer"]
                    
                    # Clean options by removing any existing letter prefixes (A., B., etc.)
                    cleaned_options = []
                    for option in options:
                        # Remove letter prefixes like "A. ", "B. ", etc.
                        cleaned_option = re.sub(r'^[A-D]\.\s*', '', option.strip())
                        cleaned_options.append(cleaned_option)
                    
                    # Create a list of (option_text, is_correct) tuples
                    option_tuples = []
                    for option in cleaned_options:
                        # Check if this option matches the correct answer
                        is_correct = (option.strip().lower() == correct_text.strip().lower() or 
                                    correct_text.strip().lower() in option.strip().lower() or 
                                    option.strip().lower() in correct_text.strip().lower())
                        option_tuples.append((option, is_correct))
                    
                    # Shuffle the options
                    random.shuffle(option_tuples)
                    
                    # Rebuild the options list and find new correct answer position
                    shuffled_options = []
                    new_correct_letter = None
                    
                    for idx, (option_text, is_correct) in enumerate(option_tuples):
                        shuffled_options.append(option_text)
                        if is_correct:
                            new_correct_letter = chr(65 + idx)  # A, B, C, D
                    
                    # Update the question with cleaned and shuffled options
                    q["options"] = shuffled_options
                    if new_correct_letter:
                        q["correct_answer"] = new_correct_letter
                        logger.info(f"Question {i+1}: Randomized options, correct answer is now '{new_correct_letter}'")
                    else:
                        # Fallback - set first option as correct
                        q["correct_answer"] = "A"
                        logger.warning(f"Question {i+1}: Could not identify correct option after shuffle, defaulting to 'A'")
                
                # Add default explanation if missing
                if "explanation" not in q:
                    q["explanation"] = f"This question tests your understanding of the concepts discussed about {topic}."
            
            state["quiz_questions"] = quiz_questions
            state["current_quiz_index"] = 0
            state["quiz_scores"] = []
            
            # Return the first question
            first_question = quiz_questions[0]
            question_text = self._format_quiz_question(first_question, 1)
            state["current_response"] = question_text
            
            logger.info(f"Successfully generated {len(quiz_questions)} quiz questions")
            
        except Exception as e:
            logger.error(f"Error parsing quiz questions: {e}")
            logger.error(f"Raw response was: {response.content}")
            
            # Fallback: Generate a simple quiz question manually
            fallback_questions = [
                {
                    "question": f"Based on our discussion about {topic}, what is the main benefit of this technology?",
                    "type": "short_answer",
                    "correct_answer": "Various benefits including efficiency, automation, and scalability",
                    "explanation": "This technology provides multiple advantages in modern development and operations."
                }
            ]
            
            state["quiz_questions"] = fallback_questions
            state["current_quiz_index"] = 0
            state["quiz_scores"] = []
            state["current_response"] = self._format_quiz_question(fallback_questions[0], 1) + "\n\n*Note: Using simplified quiz due to generation error.*"
        
        return state
    
    async def _process_quiz_answer(self, state: ChatState) -> ChatState:
        """Process user's quiz answer and provide feedback"""
        logger.info("Processing quiz answer")
        
        messages = state["messages"]
        user_answer = messages[-1].content
        quiz_questions = state.get("quiz_questions", [])
        current_index = state.get("current_quiz_index", 0)
        quiz_scores = state.get("quiz_scores", [])
        
        logger.info(f"User answer: '{user_answer}', Current index: {current_index}, Quiz questions count: {len(quiz_questions)}")
        
        if not quiz_questions or current_index >= len(quiz_questions):
            logger.error("No quiz in progress or invalid index")
            state["current_response"] = "No quiz in progress."
            return state
        
        current_question = quiz_questions[current_index]
        
        # Evaluate the answer
        evaluation_prompt = ChatPromptTemplate.from_messages([
            ("system", """Evaluate the user's answer to the quiz question. Be encouraging and educational.

Question: {question}
Question Type: {q_type}
Correct Answer: {correct_answer}
User Answer: {user_answer}

CRITICAL: You must start your response with EXACTLY one of these:
- "CORRECT:" if the answer is right
- "INCORRECT:" if the answer is wrong

For multiple choice questions:
- Compare the user's letter (A, B, C, D) with the option that matches the correct answer
- Be flexible: accept both letter answers and full text answers
- "A", "B", "C", "D" should be treated as selecting that option

For short answer questions:
- Be flexible and accept answers that demonstrate understanding
- Look for key concepts rather than exact wording

Format your response as:
CORRECT: [Brief explanation and educational insight]
OR
INCORRECT: The correct answer is [correct answer]. [Brief explanation and educational insight]"""),
            ("user", "Evaluate this answer")
        ])
        
        # Build context for evaluation
        question_context = current_question["question"]
        if current_question["type"] == "multiple_choice" and "options" in current_question:
            options = current_question["options"]
            options_text = "\n".join([f"{chr(65 + i)}. {option}" for i, option in enumerate(options)])
            question_context = f"{current_question['question']}\n\nOptions:\n{options_text}"
        
        response = await self.llm.ainvoke(
            evaluation_prompt.format_messages(
                question=question_context,
                q_type=current_question["type"],
                correct_answer=current_question["correct_answer"],
                user_answer=user_answer
            )
        )
        
        # Parse evaluation
        evaluation = response.content.strip()
        is_correct = evaluation.upper().startswith("CORRECT:")
        
        logger.info(f"Evaluation response: {evaluation[:100]}...")
        logger.info(f"Parsed as correct: {is_correct}")
        
        # Store score
        quiz_scores.append({
            "question_index": current_index,
            "correct": is_correct,
            "user_answer": user_answer
        })
        state["quiz_scores"] = quiz_scores
        
        # Build response
        feedback = evaluation
        
        # Check if quiz is complete
        if current_index + 1 >= len(quiz_questions):
            # Quiz complete
            correct_count = sum(1 for score in quiz_scores if score["correct"])
            total_count = len(quiz_scores)
            
            completion_message = f"\n\n🎉 **Quiz Complete!**\nYour score: {correct_count}/{total_count}\n"
            if correct_count == total_count:
                completion_message += "Perfect score! Excellent understanding! 🌟"
            elif correct_count >= total_count * 0.8:
                completion_message += "Great job! You have a strong grasp of the concepts! 💪"
            elif correct_count >= total_count * 0.6:
                completion_message += "Good effort! Keep learning and you'll master these concepts! 📚"
            else:
                completion_message += "Keep practicing! Review the conversation and try again when ready! 🚀"
            
            # Mark questions as used
            used_questions = state.get("used_quiz_questions", [])
            for q in quiz_questions:
                used_questions.append(q["question"])
            state["used_quiz_questions"] = used_questions
            logger.info(f"Added {len(quiz_questions)} questions to used list. Total used questions: {len(used_questions)}")
            
            state["current_response"] = feedback + completion_message
            state["is_quiz_mode"] = False  # Exit quiz mode
        else:
            # Continue to next question
            next_index = current_index + 1
            next_question = quiz_questions[next_index]
            next_question_text = self._format_quiz_question(next_question, next_index + 1)
            
            state["current_quiz_index"] = next_index
            state["current_response"] = feedback + "\n\n---\n\n" + next_question_text
        
        return state
    
    def _format_quiz_question(self, question: Dict[str, Any], number: int) -> str:
        """Format a quiz question for display"""
        q_type = question["type"]
        q_text = f"**Question {number}/5:** {question['question']}\n\n"
        
        if q_type == "multiple_choice":
            options = question.get("options", [])
            for i, option in enumerate(options):
                q_text += f"{chr(65 + i)}. {option}\n"
            q_text += "\n*Please enter your answer (A, B, C, or D)*"
        elif q_type == "true_false":
            q_text += "*Please answer True or False*"
        else:  # short_answer
            q_text += "*Please provide a brief answer*"
        
        return q_text
    
    async def process_message(self, messages: List[Dict[str, str]], conversation_id: str, conversation_topic: str = "", 
                            is_quiz_mode: bool = False, quiz_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a message through the graph
        
        Returns a dict with 'response' and optional 'quiz_state' for quiz mode
        """
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
                is_valid=True,
                # Quiz state
                is_quiz_mode=is_quiz_mode,
                quiz_questions=quiz_state.get("quiz_questions") if quiz_state else None,
                current_quiz_index=quiz_state.get("current_quiz_index") if quiz_state else None,
                quiz_scores=quiz_state.get("quiz_scores") if quiz_state else None,
                used_quiz_questions=quiz_state.get("used_quiz_questions", []) if quiz_state else []
            )
            
            # Run the graph
            config = {"configurable": {"thread_id": conversation_id}}
            result = await self.graph.ainvoke(initial_state, config)
            
            response = result.get("current_response", "I'm sorry, I couldn't generate a response.")
            logger.info(f"Successfully processed message for conversation {conversation_id}")
            
            # Build return dict
            return_data = {"response": response}
            
            # Include quiz state if in quiz mode
            if is_quiz_mode:
                return_data["quiz_state"] = {
                    "quiz_questions": result.get("quiz_questions"),
                    "current_quiz_index": result.get("current_quiz_index"),
                    "quiz_scores": result.get("quiz_scores"),
                    "used_quiz_questions": result.get("used_quiz_questions", []),
                    "is_active": result.get("is_quiz_mode", False)  # Quiz still active?
                }
            
            return return_data
            
        except Exception as e:
            logger.exception(f"Error processing message for conversation {conversation_id}: {e}")
            return {"response": "I'm sorry, I encountered an error while processing your message. Please try again."}
