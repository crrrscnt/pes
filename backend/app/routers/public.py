from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from ..dependencies import get_current_user, get_optional_user
from ..database import get_db, SessionLocal
from ..models import User, Job, JobStatus
from ..schemas import JobResponse, JobListResponse

router_public = APIRouter(prefix="/api/public", tags=["public"])


@router_public.get("/jobs", response_model=JobListResponse)
async def list_public_jobs(
        page: int = Query(1, ge=1),
        per_page: int = Query(12, ge=1, le=50),
        molecule_filter: Optional[str] = Query(None),
        status_filter: Optional[str] = Query(None, regex="^(completed)$"),
        sort_by: str = Query("date", regex="^(date|oldest)$"),
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_optional_user)
):
    query = db.query(Job).outerjoin(User, Job.user_id == User.id)

    query = query.filter(
        Job.is_public == True,
        Job.status == JobStatus.COMPLETED
    )

    if not current_user:
        query = query.filter(
            or_(Job.user_id.is_(None), User.role == "user")
        )
    elif current_user.role == "user":
        query = query.filter(
            or_(Job.user_id.is_(None), User.role == "user")
        )
    elif current_user.role == "expert":
        query = query.filter(
            or_(Job.user_id.is_(None), User.role.in_(["user", "expert"]))
        )

    if molecule_filter:
        try:
            from ..utils.molecule_utils import normalize_formula
            canonical = normalize_formula(molecule_filter)
            query = query.filter(Job.molecule_preset_id == canonical)
        except Exception:
            pass

    total = query.count()

    if sort_by == "date":
        query = query.order_by(
            func.coalesce(Job.completed_at, Job.created_at).desc()
        )
    elif sort_by == "oldest":
        query = query.order_by(
            func.coalesce(Job.completed_at, Job.created_at).asc()
        )

    offset = (page - 1) * per_page
    jobs = query.offset(offset).limit(per_page).all()

    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        per_page=per_page
    )


@router_public.get("/jobs/{job_id}", response_model=JobResponse)
async def get_public_job(
        job_id: str,
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_optional_user)
):
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.is_public == True,
        Job.status == JobStatus.COMPLETED
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id is None:
        pass
    else:
        job_owner = db.query(User).filter(User.id == job.user_id).first()

        if not job_owner:
            pass
        else:
            job_user_role = job_owner.role

            if not current_user:
                if job_user_role != "user":
                    raise HTTPException(status_code=403, detail="Access denied")
            elif current_user.role == "user":
                if job_user_role not in ["user"]:
                    raise HTTPException(status_code=403, detail="Access denied")
            elif current_user.role == "expert":
                if job_user_role not in ["user", "expert"]:
                    raise HTTPException(status_code=403, detail="Access denied")

    return JobResponse.model_validate(job)