"""API-level tests for presigned upload/download and attachment confirmation."""

import uuid


def _phone() -> str:
    return f"+9198{uuid.uuid4().int % 10**8:08d}"


async def _make_ticket(client, admin_headers) -> dict:
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
        "/assets/machines",
        json={"plant_id": plant["id"], "name": "VI 12 parts inspection system"},
        headers=admin_headers,
    )
    machine = resp.json()

    resp = await client.post("/auth/login-phone", json={"phone": _phone()})
    op_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    resp = await client.post(
        "/tickets", json={"machine_id": machine["id"], "title": "Broken"}, headers=op_headers
    )
    return resp.json()


async def test_presign_confirm_and_fetch_attachment(client, admin_headers):
    ticket = await _make_ticket(client, admin_headers)

    resp = await client.post(
        "/uploads/presign",
        json={
            "kind": "photo",
            "filename": "camera.jpg",
            "content_type": "image/jpeg",
            "ticket_id": ticket["id"],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["upload_url"].startswith("http")
    assert body["bucket"] == "attachments"
    object_key = body["object_key"]

    resp = await client.post(
        "/uploads/attachments",
        json={
            "kind": "photo",
            "object_key": object_key,
            "file_name": "camera.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 12345,
            "ticket_id": ticket["id"],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    attachment = resp.json()
    assert attachment["object_key"] == object_key
    assert attachment["download_url"].startswith("http")

    resp = await client.get(f"/uploads/attachments/{attachment['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["file_name"] == "camera.jpg"


async def test_presign_requires_ticket_or_session(client, admin_headers):
    resp = await client.post(
        "/uploads/presign",
        json={"kind": "photo", "filename": "x.jpg", "content_type": "image/jpeg"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


async def test_presign_unknown_ticket_404(client, admin_headers):
    resp = await client.post(
        "/uploads/presign",
        json={
            "kind": "photo",
            "filename": "x.jpg",
            "content_type": "image/jpeg",
            "ticket_id": str(uuid.uuid4()),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 404


async def test_presign_requires_auth(client):
    resp = await client.post(
        "/uploads/presign",
        json={
            "kind": "photo",
            "filename": "x.jpg",
            "content_type": "image/jpeg",
            "ticket_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 401
