"""API-level tests for the admin registry CRUD endpoints (companies, plants,
lines, users, plant access).
"""

import uuid

from app.core.security import hash_password
from app.db.enums import UserRole
from app.db.models import User


async def test_company_plant_line_crud(client, admin_headers):
    resp = await client.post(
        "/admin/companies",
        json={"code": f"CO-{uuid.uuid4().hex[:6]}", "name": "Test Co"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    company = resp.json()

    resp = await client.post(
        "/admin/plants",
        json={
            "company_id": company["id"],
            "code": f"PL-{uuid.uuid4().hex[:6]}",
            "name": "Test Plant",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    plant = resp.json()

    resp = await client.post(
        "/admin/lines",
        json={"plant_id": plant["id"], "line_number": 1, "name": "Line 1"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["line_number"] == 1

    # Duplicate line_number for the same plant is rejected.
    resp = await client.post(
        "/admin/lines",
        json={"plant_id": plant["id"], "line_number": 1, "name": "dup"},
        headers=admin_headers,
    )
    assert resp.status_code == 409

    resp = await client.get(f"/admin/plants/{plant['id']}", headers=admin_headers)
    assert resp.status_code == 200

    resp = await client.patch(
        f"/admin/plants/{plant['id']}", json={"is_active": False}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_admin_requires_admin_role(client):
    resp = await client.get("/admin/companies")
    assert resp.status_code == 401


async def test_non_admin_staff_forbidden(client, db_session):
    email = f"support-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name="Support",
        role=UserRole.support_l2,
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post("/auth/login", json={"email": email, "password": "password123"})
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = await client.get("/admin/companies", headers=headers)
    assert resp.status_code == 403


async def test_user_management_and_plant_access(client, admin_headers):
    resp = await client.post(
        "/admin/companies",
        json={"code": f"CO-{uuid.uuid4().hex[:6]}", "name": "Co"},
        headers=admin_headers,
    )
    company = resp.json()
    resp = await client.post(
        "/admin/plants",
        json={"company_id": company["id"], "code": f"PL-{uuid.uuid4().hex[:6]}", "name": "Plant"},
        headers=admin_headers,
    )
    plant = resp.json()

    resp = await client.post(
        "/admin/users",
        json={
            "email": f"user-{uuid.uuid4().hex[:6]}@example.com",
            "full_name": "New Support",
            "role": "support_l2",
            "password": "password123",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    user = resp.json()
    assert user["role"] == "support_l2"

    resp = await client.post(
        f"/admin/users/{user['id']}/plant-access",
        json={"plant_id": plant["id"]},
        headers=admin_headers,
    )
    assert resp.status_code == 204

    resp = await client.get(f"/admin/users/{user['id']}/plant-access", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.delete(
        f"/admin/users/{user['id']}/plant-access/{plant['id']}", headers=admin_headers
    )
    assert resp.status_code == 204

    resp = await client.get(f"/admin/users/{user['id']}/plant-access", headers=admin_headers)
    assert resp.json() == []
