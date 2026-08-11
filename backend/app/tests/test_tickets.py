"""API-level tests for ticket create/list/patch/comments and SLA population."""

import uuid


def _phone() -> str:
    return f"+9198{uuid.uuid4().int % 10**8:08d}"


async def _operator_headers(client) -> dict:
    resp = await client.post("/auth/login-phone", json={"phone": _phone()})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _make_machine(client, admin_headers) -> dict:
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
    return {"machine": machine, "plant": plant}


async def test_ticket_create_list_patch_and_comment(client, admin_headers):
    ctx = await _make_machine(client, admin_headers)
    machine = ctx["machine"]
    op_headers = await _operator_headers(client)

    resp = await client.post(
        "/tickets",
        json={"machine_id": machine["id"], "title": "Camera frozen", "priority": "critical"},
        headers=op_headers,
    )
    assert resp.status_code == 201
    ticket = resp.json()
    assert ticket["status"] == "new"
    assert ticket["ticket_number"].startswith("TKT-")
    assert ticket["first_response_due_at"] is not None
    assert ticket["resolution_due_at"] is not None

    # Operator sees their own ticket in the list.
    resp = await client.get("/tickets", headers=op_headers)
    assert resp.status_code == 200
    assert any(t["id"] == ticket["id"] for t in resp.json())

    # A second, unrelated operator does not see it.
    other_op_headers = await _operator_headers(client)
    resp = await client.get("/tickets", headers=other_op_headers)
    assert resp.status_code == 200
    assert all(t["id"] != ticket["id"] for t in resp.json())

    # Admin sees it and can patch status.
    resp = await client.patch(
        f"/tickets/{ticket['id']}", json={"status": "in_progress"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    # Non-write role (operator) cannot patch.
    resp = await client.patch(
        f"/tickets/{ticket['id']}", json={"status": "resolved"}, headers=op_headers
    )
    assert resp.status_code == 403

    # Comments: reporter can add a public comment, sees it back.
    resp = await client.post(
        f"/tickets/{ticket['id']}/comments", json={"body": "still broken"}, headers=op_headers
    )
    assert resp.status_code == 201

    resp = await client.get(f"/tickets/{ticket['id']}/comments", headers=op_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_ticket_create_requires_auth(client):
    resp = await client.post("/tickets", json={"machine_id": str(uuid.uuid4()), "title": "x"})
    assert resp.status_code == 401


async def test_ticket_not_found(client, admin_headers):
    resp = await client.get(f"/tickets/{uuid.uuid4()}", headers=admin_headers)
    assert resp.status_code == 404
