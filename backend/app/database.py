from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings
import logging

# Настроить логирование SQLAlchemy
if not settings.debug:
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Create database engine
engine = create_engine(
    settings.database_url,
    # echo=settings.debug
    echo=settings.sql_echo
    # Отключение логов SQL в продакшене + .env + config.py
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
