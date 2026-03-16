import uuid
import pytest
from sqlalchemy.types import TypeDecorator, CHAR, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
# Defer importing application modules until after we monkeypatch
# postgresql types so model imports pick up the test-friendly types.
from app.database import get_db, Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses Postgresql's UUID type, otherwise stores as CHAR(36) on other DBs
    and converts python uuid.UUID <-> string for binding.
    """
    impl = CHAR
    cache_ok = True

    def __init__(self, as_uuid: bool = False):
        # accept as_uuid kwarg used by postgresql.UUID(...) and keep it
        # for compatibility, but do not forward it to the underlying impl
        self.as_uuid = as_uuid
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            # use native Postgres UUID type when running against Postgres
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # For Postgres let the native UUID type handle the value
        if dialect.name == "postgresql":
            return value
        # Store UUID as string in SQLite/others
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return uuid.UUID(value)


# Monkeypatch exported names from sqlalchemy.dialects.postgresql so that
# modules that do `from sqlalchemy.dialects.postgresql import UUID, JSONB`
# get types that work on SQLite in tests.
postgresql.UUID = GUID
postgresql.JSONB = Text

# Now import the application object (models will import postgresql.UUID/JSONB
# which we've already replaced above)
from app.main import app

# Shared SQLite test database configuration and TestClient fixture
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL,
                       connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False,
                                   bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    # create all tables once per test module and drop after
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
