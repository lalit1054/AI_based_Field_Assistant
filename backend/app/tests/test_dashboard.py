"""API-level tests for the aggregate dashboard stats endpoint."""

import uuid

from app.db.models import MachineHealth


def _phone() -> str:
    return f"+9198{uuid.uuid4().int % 10**8:08d}"


async def _make_machine(client, admin_headers, plant_code: str) -> dict:
    resp = await client.post(
        "/admin/companies",
        json={"code": f"CO-{uuid.uuid4().hex[:6]}", "name": "Co"},
        headers=admin_headers,
    )
    company = resp.json()
    resp = await client.post(
        "/admin/plants",
        json={"company_id": company["id"], "code": plant_code, "name": "Plant"},
        headers=admin_headers,
    )
    plant = resp.json()
    resp = await client.post(
        "/assets/machines",
        json={"plant_id": plant["id"], "name": "VI 12 parts inspection system"},
        headers=admin_headers,
    )
    return {"machine": resp.json(), "plant": plant}


async def test_dashboard_stats_counts_and_recent_tickets(client, admin_headers, db_session):
    ctx = await _make_machine(client, admin_headers, f"DEV-{uuid.uuid4().hex[:6]}")
    machine = ctx["machine"]

    db_session.add(MachineHealth(machine_id=uuid.UUID(machine["id"]), is_online=True))
    await db_session.commit()

    resp = await client.post("/auth/login-phone", json={"phone": _phone()})
    op_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    resp = await client.post(
        "/tickets",
        json={"machine_id": machine["id"], "title": "Broken thing"},
        headers=op_headers,
    )
    assert resp.status_code == 201

    resp = await client.get("/dashboard/stats", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["plants_count"] >= 1
    assert body["machines_count"] >= 1
    assert body["machines_online"] >= 1
    assert body["open_tickets_count"] >= 1
    assert any(t["machine_id"] == machine["id"] for t in body["recent_tickets"])


async def test_dashboard_stats_scoped_to_plant(client, admin_headers):
    ctx_a = await _make_machine(client, admin_headers, f"A-{uuid.uuid4().hex[:6]}")
    ctx_b = await _make_machine(client, admin_headers, f"B-{uuid.uuid4().hex[:6]}")

    resp = await client.get(
        "/dashboard/stats", params={"plant_id": ctx_a["plant"]["id"]}, headers=admin_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["machines_count"] == 1

    resp = await client.get(
        "/dashboard/stats", params={"plant_id": ctx_b["plant"]["id"]}, headers=admin_headers
    )
    assert resp.json()["machines_count"] == 1


async def test_dashboard_stats_requires_auth(client):
    resp = await client.get("/dashboard/stats")
    assert resp.status_code == 401
