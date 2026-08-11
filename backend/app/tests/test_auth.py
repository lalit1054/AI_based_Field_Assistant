"""API-level tests for the phone + staff-login auth flow, hitting the real
FastAPI app (in-process, via ASGI transport) against the Alembic-migrated
test database — not just the ORM layer.
"""

import uuid

from app.core.security import hash_password
from app.db.enums import UserRole
from app.db.models import User


def _phone() -> str:
    return f"+9198{uuid.uuid4().int % 10**8:08d}"


async def test_phone_login_full_cycle(client):
    phone = _phone()

    resp = await client.post("/auth/login-phone", json={"phone": phone})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["phone"] == phone
    assert body["user"]["role"] == "operator"
    access_token = body["access_token"]
    refresh_token = body["refresh_token"]

    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == phone

    # Logging in again with the same phone reuses the same user.
    resp = await client.post("/auth/login-phone", json={"phone": phone})
    assert resp.status_code == 200
    assert resp.json()["user"]["phone"] == phone

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    rotated = resp.json()
    assert rotated["access_token"] != access_token
    assert rotated["refresh_token"] != refresh_token

    # The old refresh token was revoked by rotation.
    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401

    resp = await client.post("/auth/logout", json={"refresh_token": rotated["refresh_token"]})
    assert resp.status_code == 204

    resp = await client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert resp.status_code == 401


async def test_staff_login_success_and_failure(client, db_session):
    email = f"staff-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name="Test Admin",
        role=UserRole.admin,
        password_hash=hash_password("s3cret-pass"),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post("/auth/login", json={"email": email, "password": "s3cret-pass"})
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "admin"

    resp = await client.post("/auth/login", json={"email": email, "password": "wrong"})
    assert resp.status_code == 401


async def test_staff_login_rejects_phone_only_user(client):
    phone = _phone()
    await client.post("/auth/login-phone", json={"phone": phone})

    resp = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401

    resp = await client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401
