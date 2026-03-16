from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.orm import Session
from ..dependencies import get_current_user, require_user, get_optional_user
from ..database import get_db
from ..models import User
from ..schemas import (
    LoginRequest, LoginResponse, RegisterRequest, RegisterResponse,
    UserResponse, UserCreate
)
from ..security import hash_password, verify_password, create_session, \
    delete_session
from datetime import datetime, timezone

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=RegisterResponse)
async def register(
        request: RegisterRequest,
        db: Session = Depends(get_db)
):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = hash_password(request.password)
    user = User(
        email=request.email,
        hashed_password=hashed_password,
        role="user"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(message="Registration successful")


@router.post("/login", response_model=LoginResponse)
async def login(
        request: LoginRequest,
        response: Response,
        db: Session = Depends(get_db)
):
    """Login user and create session"""
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Create session
    session_id = create_session(str(user.id), user.role)

    # Set HTTP-only cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=604800  # 7 days
    )

    return LoginResponse(
        user=UserResponse.model_validate(user),
        message="Login successful"
    )


@router.post("/logout")
async def logout(
        response: Response,
        session_id: str = Cookie(None),
        current_user: User = Depends(get_current_user)
):
    """Logout user and delete session"""
    if session_id:
        delete_session(session_id)

    # Clear cookie
    response.delete_cookie(key="session_id")

    return {"message": "Logout successful"}


@router.post("/request-expert")
async def request_expert_access(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_user)
):
    """Request expert access"""
    if current_user.role != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only regular users can request expert access"
        )

    if current_user.expert_request_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request already pending"
        )

    current_user.expert_request_status = "pending"
    current_user.expert_request_date = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Expert access request submitted"}


# @router.get("/me", response_model=UserResponse)
# async def get_current_user_info(
#     current_user: User = Depends(get_current_user)
# ):
#     """Get current user information"""
#     return UserResponse.model_validate(current_user)


@router.get("/me", response_model=Optional[UserResponse])
async def get_current_user_info(
        current_user: Optional[User] = Depends(get_current_user)
):
    # если не аутентифицирован — вернём null (None -> JSON null)
    if current_user is None:
        return None
    return UserResponse.model_validate(current_user)
