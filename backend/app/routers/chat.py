import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
from app.services.chat_service import ChatService
from app.services.quiz_management_service import QuizManagementService

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
chatbot = DevOpsChatbot()
chat_service = ChatService(chatbot)
quiz_service = QuizManagementService(chatbot)

@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message to the chatbot"""
    try:
        # Process the message through the chat service
        result = await chat_service.process_chat_message(
            db=db,
            user_id=str(current_user.id),
            message=request.message,
            conversation_id=request.conversation_id,
            is_quiz_mode=request.is_quiz_mode
        )
        
        # Build response
        response = ChatResponse(
            response=result["response"],
            conversation_id=result["conversation_id"],
            topic=result["topic"]
        )
        
        if result.get("quiz_state"):
            response.quiz_state = QuizState(**result["quiz_state"])
        
        return response
        
    except ValueError as e:
        # Handle validation errors from services
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/messages/{conversation_id}", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all messages for a conversation"""
    try:
        messages_data = await chat_service.get_conversation_messages(db, conversation_id)
        
        return [
            MessageResponse(
                id=msg_data["id"],
                role=msg_data["role"],
                content=msg_data["content"],
                created_at=msg_data["created_at"]
            )
            for msg_data in messages_data
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
        # Start quiz session through the quiz management service
        result = await quiz_service.start_quiz_session(
            db=db,
            user_id=str(current_user.id),
            conversation_id=request.conversation_id
        )
        
        # Build response
        response = ChatResponse(
            response=result["response"],
            conversation_id=result["conversation_id"],
            topic=result["topic"]
        )
        
        if result.get("quiz_state"):
            response.quiz_state = QuizState(**result["quiz_state"])
        
        return response
        
    except ValueError as e:
        # Handle validation errors from services
        if "Conversation not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error starting quiz: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
