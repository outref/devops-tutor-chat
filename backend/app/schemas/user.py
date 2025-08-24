"""
User-related Pydantic schemas
"""
from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    """Schema for user registration"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    username: str
