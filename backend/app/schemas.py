from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime
from .models import UserRole, JobStatus
import uuid
import enum


# User schemas
class UserRole(str, enum.Enum):
    USER = "user"
    EXPERT = "expert"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    is_active: bool
    expert_request_status: str
    expert_request_date: Optional[datetime] = None

    # class Config:
    #     from_attributes = True
    # Pydantic v2 uses `model_config`; keep a v2-compatible config in addition to v1 Config
    # so that editor/linters expecting v2 style will see it. This allows attribute-based
    # population (formerly from_orm).
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# Auth schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user: UserResponse
    message: str = "Login successful"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    message: str = "Registration successful"


# Job schemas
class JobCreate(BaseModel):
    molecule: str
    atom_name: str
    optimizer: str
    mapper: str
    precision_multiplier: int = 1
    # LinUCB: если True, optimizer и mapper выбираются автоматически
    use_linucb: bool = False


class JobResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    molecule: str
    atom_name: str
    optimizer: str
    mapper: str
    status: JobStatus
    progress: int
    error_message: Optional[str]
    results: Optional[Dict[str, Any]]
    job_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    is_public: bool
    precision_multiplier: int
    preview_image: Optional[str]
    # LinUCB поля (только если use_linucb=True)
    use_linucb: bool = False
    linucb_arm_id: Optional[str] = None
    linucb_reward: Optional[float] = None

    # class Config:
    #     from_attributes = True
    # See note above for v2-compatible configuration
    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    per_page: int


# Admin schemas
class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    per_page: int


class ExpertRequestCreate(BaseModel):
    """Запрос на получение статуса expert"""
    pass  # Пустой, ID берется из current_user


class ExpertRequestResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    request_date: datetime
    status: str

    model_config = {"from_attributes": True}


class ExpertRequestUpdate(BaseModel):
    """Одобрение/отклонение запроса админом"""
    action: str


# Molecule configuration
MOLECULE_PARAMS = {
    "H2": ("H2", "H"),
    "LiH": ("LiH", "Li"),
    "BH": ("BH", "B"),
    "BeH": ("BeH", "Be"),
    "CH": ("CH", "C"),
    "NH": ("NH", "N"),
    "OH": ("OH", "O"),
    "FH": ("FH", "F"),
}

OPTIMIZERS = ["SLSQP", "COBYLA", "SPSA"]
MAPPERS = ["JordanWigner", "BravyiKitaev", "Parity"]
