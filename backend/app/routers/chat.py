from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
import logging
import json
from datetime import datetime, timezone

from app.services.database import get_db
from app.services.chatbot import DevOpsChatbot
from app.models.conversation import Conversation, Message, MessageRole
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize chatbot
chatbot = DevOpsChatbot()

# Pydantic models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    is_quiz_mode: bool = Field(False, description="Whether this is a quiz interaction")

class QuizState(BaseModel):
    quiz_questions: Optional[List[Dict[str, Any]]] = None
    current_quiz_index: Optional[int] = None
    quiz_scores: Optional[List[Dict[str, Any]]] = None
    used_quiz_questions: Optional[List[str]] = []
    is_active: bool = False

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    topic: str
    quiz_state: Optional[QuizState] = None

class StartQuizRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID to start quiz for")

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.replace(tzinfo=timezone.utc).isoformat() if v.tzinfo is None else v.isoformat()
        }

@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message to the chatbot"""
    try:
        # Get or create conversation
        if request.conversation_id:
            # Fetch existing conversation
            stmt = select(Conversation).where(
                Conversation.id == uuid.UUID(request.conversation_id)
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # For new conversations, validate topic first
            is_valid_topic, extracted_topic, validation_reason = await chatbot.validate_first_message_topic(request.message)
            
            if not is_valid_topic:
                logger.info(f"Rejected new conversation for invalid topic: {validation_reason}")
                raise HTTPException(
                    status_code=400, 
                    detail="I can only help with topics related to Programming, DevOps, and AI/Machine Learning. Please ask a question about software development, infrastructure, automation, data science, or related technical topics."
                )
            
            # Create new conversation with validated topic
            conversation = Conversation(
                user_id=str(current_user.id),
                topic=extracted_topic
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
        
        # Add user message
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER.value,
            content=request.message
        )
        db.add(user_message)
        await db.commit()
        
        # Get all messages for this conversation
        stmt = select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at)
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        # Convert to format expected by chatbot
        message_dicts = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Get quiz state from the latest assistant message if in quiz mode
        quiz_state = None
        if request.is_quiz_mode:
            # Find the latest assistant message with quiz state
            for msg in reversed(messages):
                if (msg.role == MessageRole.ASSISTANT.value and 
                    msg.message_metadata and 
                    msg.message_metadata.get("quiz_state")):
                    quiz_state = msg.message_metadata["quiz_state"]
                    logger.info(f"Found quiz state from assistant message: questions={len(quiz_state.get('quiz_questions', []))}, index={quiz_state.get('current_quiz_index')}")
                    break
            
            if not quiz_state:
                logger.warning("Quiz mode requested but no quiz state found in assistant messages")
        
        # Process through chatbot with conversation topic
        result = await chatbot.process_message(
            message_dicts,
            str(conversation.id),
            conversation.topic,
            is_quiz_mode=request.is_quiz_mode,
            quiz_state=quiz_state
        )
        
        response_content = result["response"]
        new_quiz_state = result.get("quiz_state")
        
        # Update conversation timestamp
        conversation.updated_at = func.now()
        
        # Add assistant response with quiz state if present
        message_metadata = {}
        if new_quiz_state:
            message_metadata["quiz_state"] = new_quiz_state
        
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT.value,
            content=response_content,
            message_metadata=message_metadata
        )
        db.add(assistant_message)
        await db.commit()
        
        # Build response
        response = ChatResponse(
            response=response_content,
            conversation_id=str(conversation.id),
            topic=conversation.topic
        )
        
        if new_quiz_state:
            response.quiz_state = QuizState(**new_quiz_state)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing chat message: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/messages/{conversation_id}", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all messages for a conversation"""
    try:
        stmt = select(Message).where(
            Message.conversation_id == uuid.UUID(conversation_id)
        ).order_by(Message.created_at)
        
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        return [
            MessageResponse(
                id=str(msg.id),
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    except Exception as e:
        logger.exception(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/start-quiz", response_model=ChatResponse)
async def start_quiz(
    request: StartQuizRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a quiz for the current conversation"""
    try:
        # Fetch conversation
        stmt = select(Conversation).where(
            Conversation.id == uuid.UUID(request.conversation_id),
            Conversation.user_id == str(current_user.id)
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Check if conversation has at least one message exchange
        stmt = select(func.count(Message.id)).where(
            Message.conversation_id == conversation.id
        )
        result = await db.execute(stmt)
        message_count = result.scalar()
        
        if message_count < 2:  # At least one user message and one assistant response
            raise HTTPException(
                status_code=400, 
                detail="Please have at least one conversation exchange before starting a quiz"
            )
        
        # Get all messages for context
        stmt = select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at)
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        # Convert to format expected by chatbot
        message_dicts = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Add a special message to trigger quiz generation
        message_dicts.append({"role": "user", "content": "__START_QUIZ__"})
        
        # Collect all used questions from previous quiz sessions in this conversation
        all_used_questions = []
        for msg in messages:
            if (msg.role == MessageRole.ASSISTANT.value and 
                msg.message_metadata and 
                msg.message_metadata.get("quiz_state")):
                quiz_state_data = msg.message_metadata["quiz_state"]
                if "used_quiz_questions" in quiz_state_data:
                    all_used_questions.extend(quiz_state_data["used_quiz_questions"])
        
        # Remove duplicates while preserving order
        unique_used_questions = list(dict.fromkeys(all_used_questions))
        logger.info(f"Found {len(unique_used_questions)} previously used questions across all quiz sessions")
        
        # Process through chatbot in quiz mode
        initial_quiz_state = {"used_quiz_questions": unique_used_questions}
        result = await chatbot.process_message(
            message_dicts,
            str(conversation.id),
            conversation.topic,
            is_quiz_mode=True,
            quiz_state=initial_quiz_state
        )
        
        response_content = result["response"]
        quiz_state = result.get("quiz_state")
        
        # Store the quiz initiation as a system message
        quiz_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.SYSTEM.value,
            content="Quiz started",
            message_metadata={"quiz_state": quiz_state} if quiz_state else {}
        )
        db.add(quiz_message)
        
        # Store the first quiz question as assistant message
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT.value,
            content=response_content,
            message_metadata={"quiz_state": quiz_state} if quiz_state else {}
        )
        db.add(assistant_message)
        
        conversation.updated_at = func.now()
        await db.commit()
        
        response = ChatResponse(
            response=response_content,
            conversation_id=str(conversation.id),
            topic=conversation.topic
        )
        
        if quiz_state:
            response.quiz_state = QuizState(**quiz_state)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting quiz: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
