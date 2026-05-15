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

    jobs = relationship("Job", back_populates="user")


class MoleculePreset(Base):
    __tablename__ = "molecule_presets"

    id = Column(String(20), primary_key=True)
    name = Column(String(50), nullable=False)
    distance_min = Column(Float, nullable=False)
    distance_max = Column(Float, nullable=False)
    step = Column(Float, default=0.1, nullable=False)
    reference_distance = Column(Float, nullable=False)
    cached_context = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    jobs = relationship("Job", back_populates="molecule_preset")


class LinUCBArm(Base):
    __tablename__ = "linucb_arms"

    arm_id = Column(String(50), primary_key=True)
    mapper = Column(String(20), nullable=False)
    optimizer = Column(String(20), nullable=False)
    n_pulls = Column(Integer, default=0, nullable=False)
    total_reward = Column(Float, default=0.0, nullable=False)
    a_matrix = Column(JSONB, nullable=False)
    b_vector = Column(JSONB, nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(), server_default=func.now())

    rounds = relationship("JobRound", back_populates="arm")


class JobRound(Base):
    __tablename__ = "job_rounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False,
                    index=True)
    arm_id = Column(String(50), ForeignKey("linucb_arms.arm_id"),
                    nullable=False)
    round_number = Column(Integer, nullable=False)
    reward = Column(Float, nullable=True)
    avg_error_ha = Column(Float, nullable=True)
    context_vector = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="rounds")
    arm = relationship("LinUCBArm", back_populates="rounds")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
                     index=True)

    molecule_preset_id = Column(String(20), ForeignKey("molecule_presets.id"),
                                nullable=False)

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
    is_public = Column(Boolean, default=True, nullable=False)
    precision_multiplier = Column(Integer, default=1, nullable=False)
    preview_image = Column(Text, nullable=True)

    use_linucb = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="jobs")
    molecule_preset = relationship("MoleculePreset", back_populates="jobs")
    rounds = relationship("JobRound", back_populates="job",
                          order_by="JobRound.round_number")

    __table_args__ = (
        Index('idx_jobs_status', 'status'),
        Index('idx_jobs_created_at', 'created_at'),
        Index('idx_jobs_user_status', 'user_id', 'status'),
        Index('idx_jobs_public', 'is_public', 'status'),
    )