"""API-level tests for the machine registry CRUD + bulk import endpoints."""

import io
import uuid

import openpyxl


async def _make_plant(client, admin_headers) -> dict:
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
    return resp.json()


async def test_machine_crud(client, admin_headers):
    plant = await _make_plant(client, admin_headers)

    resp = await client.post(
        "/assets/machines",
        json={"plant_id": plant["id"], "name": "VI 12 parts inspection system"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    machine = resp.json()
    assert machine["machine_type"] == "VISUAL_INSPECTION"
    assert machine["status"] == "active"

    resp = await client.get(f"/assets/machines/{machine['id']}", headers=admin_headers)
    assert resp.status_code == 200

    resp = await client.get(
        "/assets/machines", params={"plant_id": plant["id"]}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.patch(
        f"/assets/machines/{machine['id']}", json={"status": "maintenance"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "maintenance"


async def test_machine_create_requires_write_role(client, admin_headers):
    plant = await _make_plant(client, admin_headers)
    resp = await client.post(
        "/assets/machines",
        json={"plant_id": str(uuid.uuid4()), "name": "Nonexistent plant"},
        headers=admin_headers,
    )
    assert resp.status_code == 404

    resp = await client.post("/assets/machines", json={"plant_id": plant["id"], "name": "No auth"})
    assert resp.status_code == 401


async def test_machine_list_requires_auth(client):
    resp = await client.get("/assets/machines")
    assert resp.status_code == 401


async def test_bulk_import_machines(client, admin_headers):
    plant = await _make_plant(client, admin_headers)
    resp = await client.post(
        "/admin/lines",
        json={"plant_id": plant["id"], "line_number": 1, "name": "Line 1"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(["plant_code", "line_number", "name", "hostname"])
    sheet.append([plant["code"], 1, "VI 10 inspection", "vi10-host"])
    sheet.append([plant["code"], 99, "VI bad line", "vi-bad"])  # line 99 doesn't exist
    sheet.append(["UNKNOWN-CODE", "", "VI unknown plant", ""])  # unknown plant_code
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    resp = await client.post(
        "/assets/machines/bulk-import",
        files={
            "file": (
                "machines.xlsx",
                buf,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 1
    assert len(body["errors"]) == 2

    resp = await client.get(
        "/assets/machines", params={"plant_id": plant["id"]}, headers=admin_headers
    )
    names = [m["name"] for m in resp.json()]
    assert "VI 10 inspection" in names
