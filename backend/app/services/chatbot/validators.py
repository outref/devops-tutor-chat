from typing import List, Tuple
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from .state import ChatState
import logging

logger = logging.getLogger(__name__)


class TopicValidator:
    """Service for topic validation and extraction"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    async def validate_first_message_topic(self, message: str) -> Tuple[bool, str, str]:
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
    
    async def extract_topic(self, messages: List[BaseMessage], is_first_message: bool, 
                           current_topic: str = None) -> str:
        """Extract or identify the current topic from the conversation"""
        try:
            # Skip topic extraction if we're in quiz mode - topic is already set
            if current_topic:
                return current_topic
            
            # For new conversations, topic is already pre-validated and set
            # For existing conversations with first message, we still need to extract topic
            if is_first_message and not current_topic:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "Generate a concise, descriptive topic name (2-4 words max) based on the user's question. Be specific and user-friendly. Examples:\n- 'Jenkins CI/CD' instead of 'cicd'\n- 'Docker Containers' instead of 'docker'\n- 'Kubernetes Deployment' instead of 'kubernetes'\n- 'AWS EC2 Setup' instead of 'aws'\n- 'Terraform Infrastructure' instead of 'terraform'\n- 'Ansible Automation' instead of 'ansible'\n- 'Monitoring & Alerting' instead of 'monitoring'\n- 'Python FastAPI' instead of 'python'\n- 'Machine Learning Basics' instead of 'ml'\nRespond with just the topic name."),
                    ("user", "{message}")
                ])
                
                response = await self.llm.ainvoke(
                    prompt.format_messages(message=messages[-1].content)
                )
                return response.content.strip().strip("'\"")  # Remove quotes and whitespace
            
            return current_topic or "General"
        except Exception as e:
            logger.error(f"Error extracting topic: {e}")
            return current_topic or "General"
    
    async def validate_topic_category(self, topic: str, message: str, is_first_message: bool) -> bool:
        """Validate if the topic is in allowed categories (Programming/DevOps/AI)"""
        try:
            if is_first_message:
                # For new conversations, topic is already pre-validated at endpoint level
                # For existing conversations with first message, still need to validate
                if topic and topic != "General":
                    # Topic already validated at endpoint level
                    return True
                else:
                    # Legacy path - validate topic category for first message
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", """Determine if the given topic/question is related to Programming, DevOps, or AI/Machine Learning.
                        
                        Programming topics include: web development, software engineering, databases, APIs, frameworks, languages (Python, JavaScript, Java, etc.), software architecture, etc.
                        
                        DevOps topics include: containerization (Docker, Kubernetes), CI/CD, cloud services (AWS, GCP, Azure), infrastructure as code, monitoring, automation, deployment, etc.
                        
                        AI/ML topics include: machine learning, artificial intelligence, data science, neural networks, deep learning, natural language processing, computer vision, etc.
                        
                        Respond with 'yes' if the topic falls into any of these categories, 'no' if it doesn't."""),
                        ("user", f"Topic: {topic}\nUser message: {message}")
                    ])
                    
                    response = await self.llm.ainvoke(prompt.format_messages())
                    
                    return response.content.strip().lower() == "yes"
            else:
                # For subsequent messages, category is already validated
                return True
                
        except Exception as e:
            logger.error(f"Error validating topic category: {e}")
            # Default to valid to avoid blocking users on error
            return True
        
    async def validate_topic_relevance(self, message: str, topic: str) -> bool:
        """Validate if the message is related to the current topic (for subsequent messages)"""
        try:
            # This is only called for subsequent messages
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"Determine if the user's message is related to the topic '{topic}'. Respond with 'yes' or 'no' only."),
                ("user", "{message}")
            ])
            
            response = await self.llm.ainvoke(
                prompt.format_messages(message=message)
            )
            
            return response.content.strip().lower() == "yes"
        except Exception as e:
            logger.error(f"Error validating topic relevance: {e}")
            return True  # Default to valid to avoid blocking users


class ConversationRouter:
    """Handles routing decisions in the conversation workflow"""
    
    def route_after_category_validation(self, state: ChatState) -> str:
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
    
    def route_after_topic_validation(self, state: ChatState) -> str:
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
    
    def route_after_web_search(self, state: ChatState) -> str:
        """Route to lesson generation for first message, regular response for others"""
        if state["is_first_message"]:
            return "lesson"
        else:
            return "response"
