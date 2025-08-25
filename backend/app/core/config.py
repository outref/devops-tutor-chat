"""
Configuration management for the DevOps Chatbot API
"""
import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "DevOps Chatbot API"
    app_version: str = "1.0.0"
    description: str = "A chatbot for learning DevOps topics with RAG and MCP integration"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://chatbot:chatbot123@postgres:5432/devops_chatbot",
        env="DATABASE_URL"
    )
    
    # CORS
    allowed_origins: List[str] = Field(
        default=["http://localhost:3001", "http://localhost:3000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OpenAI
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    
    # Redis
    redis_url: str = Field(default="redis://redis:6379", env="REDIS_URL")
    
    # MCP Service
    mcp_websearch_url: str = Field(
        default="http://web-search-mcp:3000",
        env="MCP_WEBSEARCH_URL"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Debug: Print the loaded origins
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"Loaded CORS origins: {settings.allowed_origins}")
logger.info(f"CORS origins type: {type(settings.allowed_origins)}")
