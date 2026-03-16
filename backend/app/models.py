from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, \
    Float, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid
import enum


class UserRole(str, enum.Enum):
    USER = "user"
    EXPERT = "expert"
    ADMIN = "admin"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.USER, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    expert_request_status = Column(
        SQLEnum("none", "pending", "approved", "rejected",
                name="expert_request_status"),
        default="none",
        nullable=False
    )
    expert_request_date = Column(DateTime(timezone=True), nullable=True)
    expert_approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                                nullable=True)
    expert_approved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    jobs = relationship("Job", back_populates="user")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
                     index=True)
    molecule = Column(String(50), nullable=False)
    atom_name = Column(String(10), nullable=False)
    optimizer = Column(String(20), nullable=False)
    mapper = Column(String(20), nullable=False)
    status = Column(
        SQLEnum(JobStatus, values_callable=lambda x: [e.value for e in x]),
        default=JobStatus.QUEUED, nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    results = Column(JSONB, nullable=True)
    job_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                        index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    is_public = Column(Boolean, default=True,
                       nullable=False)  # Видимость для других
    precision_multiplier = Column(Integer, default=1, nullable=False)  # 1 или 2
    preview_image = Column(Text, nullable=True)


    # ── LinUCB ──────────────────────────────────────────────────────────────
    # True = LinUCB выбирает mapper+optimizer автоматически
    use_linucb       = Column(Boolean, default=False, nullable=False)
    # Идентификатор выбранной руки, e.g. "Parity_SLSQP"
    linucb_arm_id    = Column(String(50), nullable=True)
    # Контекстный вектор x (сохраняется для обновления модели после расчёта)
    linucb_context   = Column(JSONB, nullable=True)
    # Полученная награда r ∈ (0,1] (заполняется после завершения)
    linucb_reward    = Column(Float, nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobs")

    # Indexes
    __table_args__ = (
        Index('idx_jobs_status', 'status'),
        Index('idx_jobs_created_at', 'created_at'),
        Index('idx_jobs_user_status', 'user_id', 'status'),
        Index('idx_jobs_public', 'is_public', 'status'),
    )

class LinUCBArm(Base):
    """
    Хранит состояние одной «руки» LinUCB-бандита.

    Одна строка на каждую комбинацию (mapper × optimizer) — итого 9 строк.
    A_matrix и b_vector — параметры линейной модели LinUCB.
    Обновляются инкрементально после каждого завершённого job.
    """
    __tablename__ = "linucb_arms"

    arm_id       = Column(String(50), primary_key=True)  # "Parity_SLSQP" etc.
    mapper       = Column(String(20), nullable=False)
    optimizer    = Column(String(20), nullable=False)
    n_pulls      = Column(Integer, default=0, nullable=False)
    total_reward = Column(Float, default=0.0, nullable=False)
    # d×d матрица как JSON (список списков)
    a_matrix     = Column(JSONB, nullable=False)
    # d-вектор как JSON (список чисел)
    b_vector     = Column(JSONB, nullable=False)
    updated_at   = Column(DateTime(timezone=True),
                          onupdate=func.now(), server_default=func.now())
