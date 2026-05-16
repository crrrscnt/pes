from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
from ..dependencies import get_current_user, get_optional_user, require_user
from ..database import get_db, SessionLocal
from ..models import User, Job, JobStatus, MoleculePreset
from ..schemas import JobCreate, JobResponse, JobListResponse, OPTIMIZERS, MAPPERS
from ..redis_client import get_redis
from ..workers.pes_worker import run_pes_scan
from ..utils.molecule_utils import (
    normalize_formula, parse_chemical_formula,
    get_total_atom_count, ELEMENT_SYMBOLS
)
import uuid
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def get_or_create_preset(db: Session, canonical: str) -> MoleculePreset:
    preset = db.query(MoleculePreset).filter(MoleculePreset.id == canonical).first()
    if preset:
        return preset
    preset = MoleculePreset(
        id=canonical,
        name=canonical,
        distance_min=0.5,
        distance_max=2.0,
        step=0.1,
        reference_distance=1.25,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    logger.info("Auto-created preset for %s", canonical)
    return preset


def validate_job_parameters(
        molecule: str,
        optimizer: str,
        mapper: str,
        precision_multiplier: int,
        user: User,
        use_linucb: bool = False,
        db: Session = None,
):
    if db is None:
        raise RuntimeError("db session required for validation")

    try:
        canonical = normalize_formula(molecule)
        counts = parse_chemical_formula(canonical)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid molecule formula: {str(e)}"
        )

    if get_total_atom_count(canonical) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only diatomic molecules are supported"
        )

    for element in counts.keys():
        if element not in ELEMENT_SYMBOLS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported element: {element}"
            )

    get_or_create_preset(db, canonical)

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

    if use_linucb:
        return canonical

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

    return canonical


@router.post("", response_model=JobResponse)
async def create_job(
        job_data: JobCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_user)
):
    canonical = validate_job_parameters(
        job_data.molecule,
        job_data.optimizer,
        job_data.mapper,
        job_data.precision_multiplier,
        current_user,
        use_linucb=job_data.use_linucb,
        db=db,
    )

    optimizer = job_data.optimizer if not job_data.use_linucb else "linucb_pending"
    mapper = job_data.mapper if not job_data.use_linucb else "linucb_pending"

    job = Job(
        user_id=current_user.id,
        molecule_preset_id=canonical,
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

    run_pes_scan.delay(str(job.id))

    return JobResponse.model_validate(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
        job_id: str,
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_optional_user)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if current_user and current_user.role == "admin":
        pass
    elif current_user and job.user_id == current_user.id:
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        status_filter: Optional[JobStatus] = Query(None),
        molecule_filter: Optional[str] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_user)
):
    query = db.query(Job)

    if current_user.role != "admin":
        query = query.filter(Job.user_id == current_user.id)

    if status_filter:
        query = query.filter(Job.status == status_filter)
    if molecule_filter:
        try:
            canonical = normalize_formula(molecule_filter)
            query = query.filter(Job.molecule_preset_id == canonical)
        except Exception:
            pass

    total = query.count()

    offset = (page - 1) * per_page
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(per_page).all()

    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        per_page=per_page
    )


@router.post("/{job_id}/preview", response_model=JobResponse)
async def upload_job_preview(
        job_id: str,
        image: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_user)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cover image can only be uploaded for completed jobs"
        )

    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Use PNG, JPEG, or WEBP."
        )

    content = await image.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image size must be 2MB or less"
        )

    import base64
    encoded = base64.b64encode(content).decode('utf-8')
    job.preview_image = f"data:{image.content_type};base64,{encoded}"
    db.add(job)
    db.commit()
    db.refresh(job)

    return JobResponse.model_validate(job)


@router.get("/{job_id}/stream")
async def stream_job_progress(
        job_id: str,
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_optional_user),
        request: Request = None,
):
    import asyncio
    from fastapi.responses import StreamingResponse

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    logger.info(
        "Access check: job.user_id=%s, current_user.id=%s, current_user.role=%s",
        job.user_id,
        getattr(current_user, 'id', None),
        getattr(current_user, 'role', None)
    )

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
        redis = get_redis()
        logger.info("Starting SSE stream for job %s", job_id)

        try:
            while True:
                try:
                    if request is not None and await request.is_disconnected():
                        logger.info("Client disconnected from stream for job %s", job_id)
                        break

                    with SessionLocal() as session:
                        job_fresh = session.query(Job).filter(
                            Job.id == job_id).first()

                        if not job_fresh:
                            payload = {"id": job_id, "error": "Job not found"}
                            yield f"data: {json.dumps(payload)}\n\n"
                            break

                        # ИСПРАВЛЕНИЕ: добавлены optimizer и mapper в SSE-ответ
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
                            "optimizer": job_fresh.optimizer,  # ← ДОБАВЛЕНО
                            "mapper": job_fresh.mapper,        # ← ДОБАВЛЕНО
                            "molecule": job_fresh.molecule_preset_id,  # ← ДОБАВЛЕНО для совместимости
                        }

                        redis_key = f"job:{job_id}:partial_results"
                        partial_results = []
                        result_json_list = redis.lrange(redis_key, 0, -1)
                        if result_json_list:
                            for result_json in result_json_list:
                                partial_results.append(json.loads(result_json))
                            redis.ltrim(redis_key, len(result_json_list), -1)

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

            try:
                with SessionLocal() as session:
                    job_latest = session.query(Job).filter(
                        Job.id == job_id).first()
                    if job_latest:
                        # ИСПРАВЛЕНИЕ: финальный пакет тоже содержит optimizer/mapper
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
                            "optimizer": job_latest.optimizer,  # ← ДОБАВЛЕНО
                            "mapper": job_latest.mapper,        # ← ДОБАВЛЕНО
                            "molecule": job_latest.molecule_preset_id,  # ← ДОБАВЛЕНО
                        }
                        yield f"data: {json.dumps(final_dict)}\n\n"
            except Exception:
                logger.exception("Final fetch failed for job %s", job_id)

        finally:
            logger.info("Ending SSE stream for job %s", job_id)
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
