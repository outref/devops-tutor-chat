"""
CRUD operations for User model
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserRegister
from app.core.security import get_password_hash, verify_password


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username"""
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserRegister) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        hashed_password=hashed_password
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate a user"""
    user = await get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
