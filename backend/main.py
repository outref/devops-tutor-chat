import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import Base, engine
from app.routers import auth, chat, conversations

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    logger.info("Shutting down application...")
    await engine.dispose()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.description,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    logger.exception(f"Unhandled exception occurred: {exc}")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request method: {request.method}")
    
    # Don't expose internal errors in production
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred. Please try again."}
    )

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])

@app.get("/")
async def root():
    return {"message": "DevOps Chatbot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
