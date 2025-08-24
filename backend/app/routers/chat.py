import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud.conversation import (
    create_conversation,
    get_conversation_by_id,
    update_conversation_timestamp,
)
from app.crud.message import create_message, get_messages_by_conversation, get_message_count
from app.models.conversation import Conversation, Message, MessageRole
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageResponse,
    QuizState,
    StartQuizRequest,
)
from app.services.chatbot import DevOpsChatbot

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize chatbot
chatbot = DevOpsChatbot()

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
            conversation = await get_conversation_by_id(db, uuid.UUID(request.conversation_id))
            
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
            conversation = await create_conversation(db, str(current_user.id), extracted_topic)
        
        # Add user message
        await create_message(
            db,
            conversation.id,
            MessageRole.USER,
            request.message
        )
        
        # Get all messages for this conversation
        messages = await get_messages_by_conversation(db, conversation.id)
        
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
        await update_conversation_timestamp(db, conversation)
        
        # Add assistant response with quiz state if present
        message_metadata = {}
        if new_quiz_state:
            message_metadata["quiz_state"] = new_quiz_state
        
        await create_message(
            db,
            conversation.id,
            MessageRole.ASSISTANT,
            response_content,
            message_metadata
        )
        
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
        messages = await get_messages_by_conversation(db, uuid.UUID(conversation_id))
        
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
        conversation = await get_conversation_by_id(db, uuid.UUID(request.conversation_id))
        
        # Verify ownership
        if conversation and conversation.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Check if conversation has at least one message exchange
        message_count = await get_message_count(db, conversation.id)
        
        if message_count < 2:  # At least one user message and one assistant response
            raise HTTPException(
                status_code=400, 
                detail="Please have at least one conversation exchange before starting a quiz"
            )
        
        # Get all messages for context
        messages = await get_messages_by_conversation(db, conversation.id)
        
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
        await create_message(
            db,
            conversation.id,
            MessageRole.SYSTEM,
            "Quiz started",
            {"quiz_state": quiz_state} if quiz_state else {}
        )
        
        # Store the first quiz question as assistant message
        await create_message(
            db,
            conversation.id,
            MessageRole.ASSISTANT,
            response_content,
            {"quiz_state": quiz_state} if quiz_state else {}
        )
        
        await update_conversation_timestamp(db, conversation)
        
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
