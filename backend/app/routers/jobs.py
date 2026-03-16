from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from rq import Queue
from ..dependencies import get_current_user, get_optional_user, require_user
from ..database import get_db, SessionLocal
from ..models import User, Job, JobStatus
from ..schemas import JobCreate, JobResponse, JobListResponse, MOLECULE_PARAMS, \
    OPTIMIZERS, MAPPERS
from ..redis_client import get_redis
from ..workers.pes_worker import run_pes_scan
import uuid
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def validate_job_parameters(
        molecule: str,
        atom_name: str,
        optimizer: str,
        mapper: str,
        precision_multiplier: int,
        user: User,
        use_linucb: bool = False,
):
    """Validate job parameters based on user role"""
    if molecule not in MOLECULE_PARAMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid molecule. Must be one of: {list(MOLECULE_PARAMS.keys())}"
        )

    expected_molecule, expected_atom = MOLECULE_PARAMS[molecule]
    if atom_name != expected_atom:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid atom_name for {molecule}. Expected: {expected_atom}"
        )

    if precision_multiplier not in [1, 2]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="precision_multiplier must be 1 or 2"
        )

    if precision_multiplier == 2 and user.role not in ["expert", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2x precision is only available for expert users"
        )

    # В режиме LinUCB optimizer/mapper выбираются автоматически — не валидируем
    if use_linucb:
        return

    if optimizer not in OPTIMIZERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid optimizer. Must be one of: {OPTIMIZERS}"
        )

    if mapper not in MAPPERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mapper. Must be one of: {MAPPERS}"
        )

    if user.role == "user":
        if optimizer != "SLSQP" or mapper != "Parity":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Regular users must use default optimizer (SLSQP) and mapper (Parity)"
            )


@router.post("/", response_model=JobResponse)
async def create_job(
        job_data: JobCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_user)  # Changed from get_optional_user to require_user!
):
    """Create a new PES scan job - requires authentication"""
    validate_job_parameters(
        job_data.molecule,
        job_data.atom_name,
        job_data.optimizer,
        job_data.mapper,
        job_data.precision_multiplier,
        current_user,
        use_linucb=job_data.use_linucb,
    )

    # В режиме LinUCB — mapper/optimizer будут выбраны воркером
    optimizer = job_data.optimizer if not job_data.use_linucb else "linucb_pending"
    mapper    = job_data.mapper    if not job_data.use_linucb else "linucb_pending"

    job = Job(
        user_id=current_user.id,
        molecule=job_data.molecule,
        atom_name=job_data.atom_name,
        optimizer=optimizer,
        mapper=mapper,
        precision_multiplier=job_data.precision_multiplier,
        use_linucb=job_data.use_linucb,
        is_public=True,
        status=JobStatus.QUEUED
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue job
    run_pes_scan.delay(str(job.id))

    return JobResponse.model_validate(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
        job_id: str,
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_optional_user)
):
    """Get job details"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check access permissions
    if current_user and current_user.role == "admin":
        # Admin can see all jobs
        pass
    elif current_user and job.user_id == current_user.id:
        # User can see their own jobs
        pass
    else:
        # No access for others (anonymous users can't create jobs anymore)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return JobResponse.model_validate(job)


@router.get("/", response_model=JobListResponse)
async def list_jobs(
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        status_filter: Optional[JobStatus] = Query(None),
        molecule_filter: Optional[str] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_user)  # Changed to require_user!
):
    """List jobs for current user - requires authentication"""
    query = db.query(Job)

    # Filter by user (unless admin)
    if current_user.role != "admin":
        query = query.filter(Job.user_id == current_user.id)

    # Apply filters
    if status_filter:
        query = query.filter(Job.status == status_filter)
    if molecule_filter:
        query = query.filter(Job.molecule == molecule_filter)

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


@router.get("/{job_id}/stream")
async def stream_job_progress(
        job_id: str,
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_optional_user),
        request: Request = None,
):
    """Stream job progress via Server-Sent Events"""
    import asyncio
    from fastapi.responses import StreamingResponse
    import json

    # Check job exists and user has access
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"Access check: job.user_id={job.user_id} ({type(job.user_id)}), "
        f"current_user.id={getattr(current_user, 'id', None)} "
        f"({type(getattr(current_user, 'id', None))}), "
        f"current_user.role={getattr(current_user, 'role', None)}"
    )

    # Check access permissions
    if current_user and current_user.role == "admin":
        pass
    elif current_user and job.user_id == current_user.id:
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    async def event_generator():
        """Yield Server-Sent Events for job updates."""
        logger = logging.getLogger(__name__)
        redis = get_redis()

        logger.info(f"Starting SSE stream for job {job_id}")

        try:
            while True:
                try:
                    with SessionLocal() as session:
                        job_fresh = session.query(Job).filter(
                            Job.id == job_id).first()

                        if not job_fresh:
                            payload = {"id": job_id, "error": "Job not found"}
                            yield f"data: {json.dumps(payload)}\n\n"
                            break

                        job_dict = {
                            "id": str(job_fresh.id),
                            "status": job_fresh.status,
                            "progress": job_fresh.progress,
                            "error_message": job_fresh.error_message,
                            "created_at": job_fresh.created_at.isoformat() if job_fresh.created_at else None,
                            "started_at": job_fresh.started_at.isoformat() if job_fresh.started_at else None,
                            "completed_at": job_fresh.completed_at.isoformat() if job_fresh.completed_at else None,
                            "results": job_fresh.results if job_fresh.status == JobStatus.COMPLETED else None,
                            "job_metadata": job_fresh.job_metadata if job_fresh.status == JobStatus.COMPLETED else None,
                        }

                        # Send partial results
                        redis_key = f"job:{job_id}:partial_results"
                        partial_results = []

                        while True:
                            result_json = redis.rpop(redis_key)
                            if not result_json:
                                break
                            partial_results.append(json.loads(result_json))

                        if partial_results:
                            job_dict["partial_results"] = partial_results

                    yield f"data: {json.dumps(job_dict)}\n\n"

                    if job_dict["status"] in [JobStatus.COMPLETED, JobStatus.FAILED]:
                        break

                except Exception as loop_exc:
                    logging.getLogger(__name__).exception(
                        "Error while streaming job %s: %s", job_id, loop_exc)
                    payload = {"id": job_id,
                               "error": "Internal server error during stream"}
                    yield f"data: {json.dumps(payload)}\n\n"
                    break

                await asyncio.sleep(4)

            # Final fetch
            try:
                with SessionLocal() as session:
                    job_latest = session.query(Job).filter(
                        Job.id == job_id).first()
                    if job_latest:
                        final_dict = {
                            "id": str(job_latest.id),
                            "status": job_latest.status,
                            "progress": job_latest.progress,
                            "error_message": job_latest.error_message,
                            "created_at": job_latest.created_at.isoformat() if job_latest.created_at else None,
                            "started_at": job_latest.started_at.isoformat() if job_latest.started_at else None,
                            "completed_at": job_latest.completed_at.isoformat() if job_latest.completed_at else None,
                            "results": job_latest.results,
                            "job_metadata": job_latest.job_metadata,
                        }
                        yield f"data: {json.dumps(final_dict)}\n\n"
            except Exception:
                logger.exception(f"Final fetch failed for job {job_id}")

        finally:
            logger.info(f"Ending SSE stream for job {job_id}")
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
