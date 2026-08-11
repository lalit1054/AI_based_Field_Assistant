"""API-level tests for heartbeat ingest (agent-key auth) and health reads."""

import uuid

AGENT_KEY = "dev-agent-key-change-me"


async def _make_machine(client, admin_headers, plant_code: str = "DEV-PLANT") -> dict:
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
    return resp.json()


async def test_heartbeat_ingest_and_read(client, admin_headers):
    machine = await _make_machine(client, admin_headers)

    resp = await client.post(
        "/health/heartbeat",
        json={"machine_id": machine["id"], "is_online": True, "cpu_percent": 42.5},
        headers={"x-plant-code": "DEV-PLANT", "x-agent-key": AGENT_KEY},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["machine_id"] == machine["id"]
    assert body["is_online"] is True
    assert body["cpu_percent"] == 42.5

    resp = await client.get(f"/health/machines/{machine['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_online"] is True

    resp = await client.get("/health/machines", headers=admin_headers)
    assert resp.status_code == 200
    assert any(h["machine_id"] == machine["id"] for h in resp.json())


async def test_heartbeat_rejects_bad_agent_key(client, admin_headers):
    machine = await _make_machine(
        client, admin_headers, plant_code=f"BADKEY-{uuid.uuid4().hex[:6]}"
    )

    resp = await client.post(
        "/health/heartbeat",
        json={"machine_id": machine["id"]},
        headers={"x-plant-code": "DEV-PLANT", "x-agent-key": "wrong-key"},
    )
    assert resp.status_code == 401


async def test_heartbeat_rejects_mismatched_plant(client, admin_headers):
    machine = await _make_machine(client, admin_headers, plant_code="OTHER-PLANT")

    resp = await client.post(
        "/health/heartbeat",
        json={"machine_id": machine["id"]},
        headers={"x-plant-code": "DEV-PLANT", "x-agent-key": AGENT_KEY},
    )
    assert resp.status_code == 403


async def test_health_unknown_machine_404(client, admin_headers):
    resp = await client.get(f"/health/machines/{uuid.uuid4()}", headers=admin_headers)
    assert resp.status_code == 404
