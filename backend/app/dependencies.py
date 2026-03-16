from fastapi import HTTPException, status, Cookie, Depends
from sqlalchemy.orm import Session
from typing import Optional
from .database import get_db
from .models import User
from .security import get_session


async def get_current_user(
        session_id: Optional[str] = Cookie(None),
        db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user from session cookie"""
    if not session_id:
        return None

    session_data = get_session(session_id)
    if not session_data:
        return None

    user = db.query(User).filter(User.id == session_data["user_id"]).first()
    if not user or not user.is_active:
        return None

    return user


async def require_user(
        user: Optional[User] = Depends(get_current_user)) -> User:
    """Require authenticated user"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user


async def require_admin(user: User = Depends(require_user)) -> User:
    """Require admin user"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def get_optional_user(user: Optional[User] = Depends(get_current_user)) -> \
Optional[User]:
    """Get user if authenticated, None otherwise (for anonymous access)"""
    return user


async def require_expert(user: User = Depends(require_user)) -> User:
    """Require expert or admin user"""
    if user.role not in ["expert", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Expert or admin access required"
        )
    return user
