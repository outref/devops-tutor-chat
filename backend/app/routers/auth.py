import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password
from app.crud.user import authenticate_user, create_user, get_user_by_username
from app.models.user import User
from app.schemas.user import UserRegister, UserResponse

router = APIRouter()
security = HTTPBasic()

async def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    user = await authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    # Check if username already exists
    existing_user = await get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new user
    user = await create_user(db, user_data)
    
    return UserResponse(id=user.id, username=user.username)

@router.post("/login", response_model=UserResponse)
async def login(
    credentials: HTTPBasicCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Login user"""
    user = await authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return UserResponse(id=user.id, username=user.username)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse(id=current_user.id, username=current_user.username)
