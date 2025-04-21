from fastapi.testclient import TestClient
from myapp.app import app
import uuid
from datetime import datetime, timedelta
import pytest
import logging
from unittest.mock import patch

client = TestClient(app)


def get_auth_token(role: str = "employee"):
    response = client.post("/dummyLogin", json={"role": role})
    return response.json()["token"]


def create_pvz(token: str, city: str = "Москва"):
    return client.post(
        "/pvz", json={"city": city}, headers={"Authorization": f"Bearer {token}"}
    )


def create_reception(token: str, pvz_id: str):
    return client.post(
        "/receptions",
        json={"pvzId": pvz_id},
        headers={"Authorization": f"Bearer {token}"},
    )


def add_product(token: str, pvz_id: str, product_type: str = "электроника"):
    return client.post(
        "/products",
        json={"type": product_type, "pvzId": pvz_id},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_dummy_login():
    response = client.post("/dummyLogin", json={"role": "employee"})
    assert response.status_code == 200
    assert "token" in response.json()

    response = client.post("/dummyLogin", json={"role": "moderator"})
    assert response.status_code == 200
    assert "token" in response.json()

    response = client.post("/dummyLogin", json={"role": "invalid"})
    assert response.status_code == 400


def test_register():
    email = f"test_{uuid.uuid4()}@example.com"
    response = client.post(
        "/register", json={"email": email, "password": "password", "role": "employee"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == email
    assert response.json()["role"] == "employee"

    response = client.post(
        "/register", json={"email": email, "password": "password", "role": "employee"}
    )
    assert response.status_code == 400


def test_login():
    email = f"test_{uuid.uuid4()}@example.com"
    password = "password"
    client.post(
        "/register", json={"email": email, "password": password, "role": "employee"}
    )

    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200
    assert "token" in response.json()

    response = client.post("/login", json={"email": email, "password": "wrong"})
    assert response.status_code == 401


def test_create_pvz():
    moderator_token = get_auth_token("moderator")
    employee_token = get_auth_token("employee")

    response = create_pvz(moderator_token)
    assert response.status_code == 201
    assert response.json()["city"] == "Москва"

    response = create_pvz(employee_token)
    assert response.status_code == 403

    response = client.post(
        "/pvz",
        json={"city": "Новосибирск"},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 400


def test_get_pvz_list():
    moderator_token = get_auth_token("moderator")

    response = create_pvz(moderator_token)
    pvz_id = response.json()["id"]

    employee_token = get_auth_token("employee")
    reception_response = create_reception(employee_token, pvz_id)
    reception_id = reception_response.json()["id"]

    add_product(employee_token, pvz_id)

    response = client.get(
        "/pvz", headers={"Authorization": f"Bearer {moderator_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) > 0

    end_date = datetime.now().isoformat()
    start_date = (datetime.now() - timedelta(days=1)).isoformat()
    response = client.get(
        "/pvz",
        params={"startDate": start_date, "endDate": end_date},
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert response.status_code == 200


def test_create_reception():
    moderator_token = get_auth_token("moderator")
    employee_token = get_auth_token("employee")

    pvz_response = create_pvz(moderator_token)
    pvz_id = pvz_response.json()["id"]

    response = create_reception(employee_token, pvz_id)
    assert response.status_code == 201
    assert response.json()["status"] == "in_progress"

    response = create_reception(employee_token, pvz_id)
    assert response.status_code == 400

    response = create_reception(moderator_token, pvz_id)
    assert response.status_code == 403


def test_close_reception():
    moderator_token = get_auth_token("moderator")
    employee_token = get_auth_token("employee")

    pvz_response = create_pvz(moderator_token)
    pvz_id = pvz_response.json()["id"]

    create_reception(employee_token, pvz_id)

    response = client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "close"

    response = client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_add_product():
    moderator_token = get_auth_token("moderator")
    employee_token = get_auth_token("employee")

    pvz_response = create_pvz(moderator_token)
    pvz_id = pvz_response.json()["id"]

    create_reception(employee_token, pvz_id)

    response = add_product(employee_token, pvz_id)
    assert response.status_code == 201
    assert response.json()["type"] == "электроника"

    response = client.post(
        "/products",
        json={"type": "invalid", "pvzId": pvz_id},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_delete_product():
    moderator_token = get_auth_token("moderator")
    employee_token = get_auth_token("employee")

    pvz_response = create_pvz(moderator_token)
    pvz_id = pvz_response.json()["id"]

    create_reception(employee_token, pvz_id)

    add_product(employee_token, pvz_id)
    add_product(employee_token, pvz_id, "одежда")

    response = client.post(
        f"/pvz/{pvz_id}/delete_last_product",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["product"]["type"] == "одежда"

    response = client.post(
        f"/pvz/{pvz_id}/delete_last_product",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["product"]["type"] == "электроника"

    response = client.post(
        f"/pvz/{pvz_id}/delete_last_product",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400


def test_full_workflow():
    moderator_token = get_auth_token("moderator")
    pvz_response = create_pvz(moderator_token, "Казань")
    assert pvz_response.status_code == 201
    pvz_id = pvz_response.json()["id"]

    employee_token = get_auth_token("employee")
    reception_response = create_reception(employee_token, pvz_id)
    assert reception_response.status_code == 201
    reception_id = reception_response.json()["id"]

    for i in range(50):
        product_type = (
            "электроника" if i % 3 == 0 else "одежда" if i % 3 == 1 else "обувь"
        )
        response = add_product(employee_token, pvz_id, product_type)
        assert response.status_code == 201

    response = client.get(
        "/pvz", headers={"Authorization": f"Bearer {moderator_token}"}
    )
    assert response.status_code == 200
    pvz_data = next(p for p in response.json() if p["pvz"]["id"] == pvz_id)
    assert len(pvz_data["receptions"][0]["products"]) == 50

    response = client.post(
        f"/pvz/{pvz_id}/close_last_reception",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "close"

    response = add_product(employee_token, pvz_id)
    assert response.status_code == 400

    response = client.post(
        f"/pvz/{pvz_id}/delete_last_product",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400
