from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
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
    """
    Публичная галерея jobs:
    - anonymous: видит анонимные + user jobs
    - user: видит анонимные + user jobs
    - expert: видит анонимные + user + expert jobs
    - admin: видит все
    """

    # Строим запрос с LEFT JOIN один раз
    query = db.query(Job).outerjoin(User, Job.user_id == User.id)

    # Базовые фильтры
    query = query.filter(
        Job.is_public == True,
        Job.status == JobStatus.COMPLETED
    )

    # Фильтрация по ролям с учётом анонимных jobs
    if not current_user:  # anonymous
        # Видит: анонимные jobs (user_id = NULL) + jobs от role='user'
        query = query.filter(
            or_(
                Job.user_id.is_(None),
                User.role == "user"
            )
        )
    elif current_user.role == "user":
        # Видит: анонимные jobs + jobs от role='user'
        query = query.filter(
            or_(
                Job.user_id.is_(None),
                User.role == "user"
            )
        )
    elif current_user.role == "expert":
        # Видит анонимные jobs + user + expert jobs
        query = query.filter(
            or_(
                Job.user_id.is_(None),
                User.role.in_(["user", "expert"])
            )
        )
    # admin видит все (no filter)

    # Фильтр по молекуле
    if molecule_filter:
        query = query.filter(Job.molecule == molecule_filter)

    # Подсчет total ДО применения сортировки
    total = query.count()

    # Сортировка с использованием COALESCE для NULL значений
    # Это гарантирует правильную работу с PostgreSQL
    if sort_by == "date":
        # Используем COALESCE для обработки NULL значений
        # NULL completed_at будут в конце
        query = query.order_by(
            func.coalesce(Job.completed_at, Job.created_at).desc()
        )
    elif sort_by == "oldest":
        # старые сверху (completed_at ASC, created_at ASC)
        query = query.order_by(
            func.coalesce(Job.completed_at, Job.created_at).asc()
        )

    # Пагинация
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
    """Получить детали публичного job"""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.is_public == True,
        Job.status == JobStatus.COMPLETED
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # ИСПРАВЛЕНИЕ: Проверка прав доступа с учётом анонимных jobs
    if job.user_id is None:
        # Анонимный job - доступен всем
        pass
    else:
        # Job принадлежит зарегистрированному пользователю
        # Загружаем информацию о пользователе, создавшем job
        job_owner = db.query(User).filter(User.id == job.user_id).first()

        if not job_owner:
            # Если пользователь удалён, но job остался - разрешаем доступ
            pass
        else:
            job_user_role = job_owner.role

            # Проверяем права доступа на основе роли текущего пользователя
            if not current_user:
                # Анонимный пользователь может видеть только jobs от 'user'
                if job_user_role != "user":
                    raise HTTPException(status_code=403, detail="Access denied")
            elif current_user.role == "user":
                # User может видеть только jobs от 'user'
                if job_user_role not in ["user"]:
                    raise HTTPException(status_code=403, detail="Access denied")
            elif current_user.role == "expert":
                # Expert может видеть jobs от 'user' и 'expert', но не от 'admin'
                if job_user_role not in ["user", "expert"]:
                    raise HTTPException(status_code=403, detail="Access denied")
            # Admin может видеть все (нет проверки)

    return JobResponse.model_validate(job)
