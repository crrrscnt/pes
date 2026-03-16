from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from ..dependencies import require_admin
from ..database import get_db
from ..models import User, Job, JobStatus, UserRole
from ..schemas import UserResponse, UserUpdate, UserListResponse, \
    JobListResponse, JobResponse, ExpertRequestResponse, ExpertRequestUpdate
from datetime import datetime, timezone

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
async def list_users(
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        role_filter: Optional[str] = Query(None),
        active_filter: Optional[bool] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """List all users (admin only)"""
    query = db.query(User)

    # Apply filters
    if role_filter:
        query = query.filter(User.role == role_filter)
    if active_filter is not None:
        query = query.filter(User.is_active == active_filter)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * per_page
    users = query.order_by(User.created_at.desc()).offset(offset).limit(
        per_page).all()

    return UserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/users/{user_id}/jobs", response_model=JobListResponse)
async def get_user_jobs(
        user_id: str,
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        status_filter: Optional[JobStatus] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """Get jobs for a specific user (admin only)"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    query = db.query(Job).filter(Job.user_id == user_id)

    # Apply filters
    if status_filter:
        query = query.filter(Job.status == status_filter)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * per_page
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(
        per_page).all()

    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        per_page=per_page
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
        user_id: str,
        user_update: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update fields
    if user_update.email is not None:
        # Check if email is already taken by another user
        existing_user = db.query(User).filter(
            User.email == user_update.email,
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already taken"
            )
        user.email = user_update.email

    if user_update.role is not None:
        user.role = user_update.role

    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/jobs", response_model=JobListResponse)
async def list_all_jobs(
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        status_filter: Optional[JobStatus] = Query(None),
        molecule_filter: Optional[str] = Query(None),
        user_filter: Optional[str] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """List all jobs across all users (admin only)"""
    query = db.query(Job)

    # Apply filters
    if status_filter:
        query = query.filter(Job.status == status_filter)
    if molecule_filter:
        query = query.filter(Job.molecule == molecule_filter)
    if user_filter:
        query = query.filter(Job.user_id == user_filter)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * per_page
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(
        per_page).all()

    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        per_page=per_page
    )


@router.delete("/jobs/{job_id}")
async def delete_job(
        job_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """Delete a job (admin only)"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    db.delete(job)
    db.commit()

    return {"message": "Job deleted successfully"}


@router.get("/expert-requests", response_model=List[ExpertRequestResponse])
async def list_expert_requests(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """List pending expert requests"""
    users = db.query(User).filter(
        User.expert_request_status == "pending"
    ).order_by(User.expert_request_date.desc()).all()

    return [
        ExpertRequestResponse(
            user_id=u.id,
            email=u.email,
            request_date=u.expert_request_date,
            status=u.expert_request_status
        )
        for u in users
    ]


@router.post("/expert-requests/{user_id}")
async def handle_expert_request(
        user_id: str,
        action: ExpertRequestUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """Approve or reject expert request"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if action.action == "approve":
        user.role = UserRole.EXPERT
        user.expert_request_status = "approved"
        user.expert_approved_by = current_user.id
        user.expert_approved_at = datetime.now(timezone.utc)
        message = "Expert access approved"
    elif action.action == "reject":
        user.expert_request_status = "rejected"
        message = "Expert access rejected"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    db.commit()
    return {"message": message}
