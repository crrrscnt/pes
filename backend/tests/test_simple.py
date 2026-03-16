import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint(client):
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_register_endpoint_exists(client):
    """Test that the register endpoint exists"""
    response = client.post("/api/auth/register", json={
        "email": "test2@example.com",
        "password": "password123"
    })
    # Should return 200 for successful registration
    assert response.status_code == 200
    assert "message" in response.json()


def test_login_endpoint_exists(client):
    """Test that the login endpoint exists"""
    # login with the user created earlier in this module's tests
    response = client.post("/api/auth/login", json={
        "email": "test2@example.com",
        "password": "password123"
    })
    # Should return 200 for successful login
    assert response.status_code == 200
    assert "user" in response.json()
