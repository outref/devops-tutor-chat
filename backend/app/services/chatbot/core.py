from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver
import os
import logging

from app.services.rag_service import RAGService
from app.services.mcp_service import MCPWebSearchService
from .state import ChatState
from .quiz.quiz_service import QuizService
from .search.search_service import SearchService
from .generators.content_generator import ContentGenerator
from .validators import TopicValidator, ConversationRouter

logger = logging.getLogger(__name__)


class DevOpsChatbot:
    """Main chatbot orchestrator using modular services"""
    
    def __init__(self):
        # Initialize LLM and embeddings
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize base services
        self.rag_service = RAGService(self.embeddings)
        self.mcp_service = MCPWebSearchService()
        self.memory = MemorySaver()
        
        # Initialize specialized services
        self.quiz_service = QuizService(self.llm)
        self.search_service = SearchService(self.rag_service, self.mcp_service, self.llm)
        self.content_generator = ContentGenerator(self.llm)
        self.topic_validator = TopicValidator(self.llm)
        self.router = ConversationRouter()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the conversation workflow graph"""
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
            self.router.route_after_category_validation,
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
            self.router.route_after_topic_validation,
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
            self.router.route_after_web_search,
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
    
    # Node implementations using the extracted services
    
    async def _extract_topic(self, state: ChatState) -> ChatState:
        """Extract or identify the current topic from the conversation"""
        try:
            messages = state["messages"]
            
            # Determine if this is the first message
            state["is_first_message"] = len(messages) == 1
            
            # Skip topic extraction if we're in quiz mode - topic is already set
            if state.get("is_quiz_mode", False):
                return state
            
            # Extract topic using the validator service
            topic = await self.topic_validator.extract_topic(
                messages, 
                state["is_first_message"], 
                state.get("topic")
            )
            state["topic"] = topic
            
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
            
            # Use validator service
            is_valid = await self.topic_validator.validate_topic_category(
                topic, 
                messages[-1].content, 
                state["is_first_message"]
            )
            state["topic_category_valid"] = is_valid
                
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
        
        # Use validator service
        is_valid = await self.topic_validator.validate_topic_relevance(
            messages[-1].content, 
            topic
        )
        state["is_valid"] = is_valid
        return state
    
    async def _rag_search(self, state: ChatState) -> ChatState:
        """Search for relevant documents in RAG using preprocessed queries and quality threshold"""
        raw_query = state["messages"][-1].content
        topic = state.get("topic", "")
        
        try:
            # Use search service for RAG search
            search_results = await self.search_service.search_with_fallback(raw_query, topic)
            
            state["rag_results"] = search_results["rag_results"]
            state["search_concepts"] = search_results["search_concepts"]
            
            logger.info(f"RAG search returned {len(search_results['rag_results'])} high-quality results")
            
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            state["rag_results"] = []
            state["search_concepts"] = raw_query  # Fallback to raw query
        
        return state
    
    async def _web_search(self, state: ChatState) -> ChatState:
        """Search the web if RAG doesn't have sufficient high-quality information"""
        rag_results = state.get("rag_results", [])
        raw_query = state["messages"][-1].content
        topic = state.get("topic", "")
        search_concepts = state.get("search_concepts", raw_query)
        
        try:
            # Use search service for web search
            web_results = await self.search_service.web_search(
                raw_query, topic, rag_results, search_concepts
            )
            state["web_results"] = web_results
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            state["web_results"] = []
        
        return state
    
    async def _generate_lesson(self, state: ChatState) -> ChatState:
        """Generate a structured lesson for the first message"""
        messages = state["messages"]
        topic = state.get("topic", "")
        rag_results = state.get("rag_results", [])
        web_results = state.get("web_results", [])
        
        # Use content generator service
        response = await self.content_generator.generate_lesson(
            messages, topic, rag_results, web_results
        )
        
        state["current_response"] = response
        return state
    
    async def _generate_response(self, state: ChatState) -> ChatState:
        """Generate regular response for subsequent messages or invalid topics"""
        messages = state["messages"]
        topic = state.get("topic", "")
        is_valid = state.get("is_valid", True)
        rag_results = state.get("rag_results", [])
        web_results = state.get("web_results", [])
        
        # Use content generator service
        response = await self.content_generator.generate_response(
            messages, topic, rag_results, web_results, is_valid
        )
        
        state["current_response"] = response
        return state
    
    async def _generate_quiz_questions(self, state: ChatState) -> ChatState:
        """Generate quiz questions based on conversation history"""
        messages = state["messages"]
        topic = state.get("topic", "")
        used_questions = state.get("used_quiz_questions", [])
        
        # Use quiz service
        quiz_questions = await self.quiz_service.generate_quiz_questions(
            messages, topic, used_questions
        )
        
        state["quiz_questions"] = quiz_questions
        state["current_quiz_index"] = 0
        state["quiz_scores"] = []
        
        # Return the first question
        first_question = quiz_questions[0]
        question_text = self.quiz_service.format_quiz_question(first_question, 1)
        state["current_response"] = question_text
        
        logger.info(f"Successfully generated {len(quiz_questions)} quiz questions")
        
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
        
        # Use quiz service to process answer
        evaluation_result = await self.quiz_service.process_quiz_answer(
            current_question, user_answer
        )
        
        # Store score
        quiz_scores.append({
            "question_index": current_index,
            "correct": evaluation_result["is_correct"],
            "user_answer": user_answer
        })
        state["quiz_scores"] = quiz_scores
        
        # Build response
        feedback = evaluation_result["feedback"]
        
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
            next_question_text = self.quiz_service.format_quiz_question(next_question, next_index + 1)
            
            state["current_quiz_index"] = next_index
            state["current_response"] = feedback + "\n\n---\n\n" + next_question_text
        
        return state
    
    # Main public interface
    
    async def validate_first_message_topic(self, message: str) -> tuple[bool, str, str]:
        """
        Validate if a first message is related to allowed topics (Programming/DevOps/AI).
        
        Args:
            message: The user's first message
            
        Returns:
            Tuple of (is_valid, topic, reason)
        """
        return await self.topic_validator.validate_first_message_topic(message)
    
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
