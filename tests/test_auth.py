import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_dummy_login_employee():
    response = client.post("/dummyLogin", json={"role": "employee"})
    assert response.status_code == 200
    assert "token" in response.json()


def test_dummy_login_moderator():
    response = client.post("/dummyLogin", json={"role": "moderator"})
    assert response.status_code == 200
    assert "token" in response.json()


def test_dummy_login_invalid_role():
    response = client.post("/dummyLogin", json={"role": "invalid"})
    assert response.status_code == 400


def test_register_employee():
    response = client.post(
        "/register",
        json={
            "email": "employee@example.com",
            "password": "password123",
            "role": "employee",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "employee@example.com"
    assert data["role"] == "employee"
    assert "token" in data


def test_register_moderator():
    response = client.post(
        "/register",
        json={
            "email": "moderator@example.com",
            "password": "password123",
            "role": "moderator",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "moderator@example.com"
    assert data["role"] == "moderator"
    assert "token" in data


def test_register_invalid_role():
    response = client.post(
        "/register",
        json={
            "email": "invalid@example.com",
            "password": "password123",
            "role": "invalid",
        },
    )
    assert response.status_code == 400


def test_login_success():
    client.post(
        "/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "role": "employee",
        },
    )

    response = client.post(
        "/login", json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "token" in response.json()


def test_login_invalid_credentials():
    response = client.post(
        "/login", json={"email": "nonexistent@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
