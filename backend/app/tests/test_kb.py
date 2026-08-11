"""API-level tests for KB document ingestion and known_errors CRUD."""

import uuid


def _phone() -> str:
    return f"+9198{uuid.uuid4().int % 10**8:08d}"


async def test_kb_document_ingest_and_list(client, admin_headers):
    resp = await client.post(
        "/kb/documents",
        json={
            "title": "Camera troubleshooting runbook",
            "doc_type": "runbook",
            "machine_type": "VISUAL_INSPECTION",
            "content": "x" * 2500,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    doc = resp.json()
    assert doc["chunk_count"] >= 3  # 2500 chars / (1000-100 step) ≈ 3 chunks

    resp = await client.get("/kb/documents", headers=admin_headers)
    assert resp.status_code == 200
    assert any(d["id"] == doc["id"] for d in resp.json())

    resp = await client.get(f"/kb/documents/{doc['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["chunk_count"] == doc["chunk_count"]


async def test_kb_document_create_requires_write_role(client):
    resp = await client.post("/auth/login-phone", json={"phone": _phone()})
    op_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = await client.post(
        "/kb/documents",
        json={"title": "x", "doc_type": "faq", "content": "hello"},
        headers=op_headers,
    )
    assert resp.status_code == 403


async def test_known_error_crud_and_operator_masking(client, admin_headers):
    resp = await client.post(
        "/kb/known-errors",
        json={
            "machine_type": "VISUAL_INSPECTION",
            "category": "camera_image",
            "title": "Camera disconnected",
            "error_signature": "camera disconnected",
            "probable_cause": "Loose cable",
            "operator_fix_steps": "Reseat the camera cable.",
            "engineer_fix_steps": "Check GigE link negotiation in the switch logs.",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    known_error = resp.json()
    assert known_error["engineer_fix_steps"] is not None

    resp = await client.post("/auth/login-phone", json={"phone": _phone()})
    op_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = await client.get(f"/kb/known-errors/{known_error['id']}", headers=op_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["engineer_fix_steps"] is None
    assert body["operator_fix_steps"] == "Reseat the camera cable."
    assert body["hit_count"] == 1

    resp = await client.get(f"/kb/known-errors/{known_error['id']}", headers=admin_headers)
    assert resp.json()["engineer_fix_steps"] is not None
    assert resp.json()["hit_count"] == 2

    resp = await client.patch(
        f"/kb/known-errors/{known_error['id']}", json={"is_active": False}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp = await client.patch(
        f"/kb/known-errors/{known_error['id']}", json={"is_active": True}, headers=op_headers
    )
    assert resp.status_code == 403
