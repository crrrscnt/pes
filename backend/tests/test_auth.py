import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, String
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
from app.models import User
from app.security import hash_password

# Test database
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
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def test_user(client):
    # ensure client fixture (and DB tables) are created before we add a user
    db = TestingSessionLocal()
    user = User(
        email="test@example.com",
        hashed_password=hash_password("password123"),
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()
    db.close()


def test_register_user(client):
    response = client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "Registration successful" in response.json()["message"]


def test_register_existing_user(client, test_user):
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_login_success(client, test_user):
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "test@example.com"


def test_login_invalid_credentials(client):
    response = client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


def test_anonymous_h2_only(client):
    # ensure no session cookie is set (test client is module-scoped)
    client.cookies.clear()

    response = client.post("/api/jobs", json={
        "molecule": "LiH",
        "atom_name": "Li",
        "optimizer": "SLSQP",
        "mapper": "Parity"
    })
    assert response.status_code == 403
    assert "Anonymous users can only compute H2 molecules" in response.json()[
        "detail"]


def test_anonymous_h2_allowed(client):
    client.cookies.clear()

    response = client.post("/api/jobs", json={
        "molecule": "H2",
        "atom_name": "H",
        "optimizer": "SLSQP",
        "mapper": "Parity"
    })
    assert response.status_code == 200
    assert "id" in response.json()
