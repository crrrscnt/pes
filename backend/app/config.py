from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://pes_user:dev_password@localhost:5432/pes_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    session_ttl_seconds: int = 604800  # 7 days

    # CORS
    frontend_url: str = "http://localhost:5173"

    # Worker
    worker_concurrency: int = 2

    # Compute
    per_task_timeout: int = 14400

    # Environment
    environment: str = "development"
    debug: bool = False  # True
    sql_echo: bool = False  # Отключение логов SQL в продакшене + .env + database.py

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
