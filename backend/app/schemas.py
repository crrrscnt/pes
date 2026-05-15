from pydantic import BaseModel, EmailStr, Field
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


# JobRound schema
class JobRoundResponse(BaseModel):
    id: uuid.UUID
    arm_id: str
    round_number: int
    reward: Optional[float] = None
    avg_error_ha: Optional[float] = None
    context_vector: Optional[List[float]] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# Job schemas
class JobCreate(BaseModel):
    molecule: str
    optimizer: str = "SLSQP"
    mapper: str = "Parity"
    precision_multiplier: int = 1
    use_linucb: bool = False


class JobResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    molecule: str = Field(validation_alias="molecule_preset_id")
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
    use_linucb: bool = False
    rounds: Optional[List[JobRoundResponse]] = None
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
    pass


class ExpertRequestResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    request_date: datetime
    status: str
    model_config = {"from_attributes": True}


class ExpertRequestUpdate(BaseModel):
    action: str


# Constants for validation
OPTIMIZERS = ["SLSQP", "COBYLA", "SPSA"]
MAPPERS = ["JordanWigner", "BravyiKitaev", "Parity"]