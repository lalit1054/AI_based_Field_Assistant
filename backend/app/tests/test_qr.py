"""API-level tests for QR token issuance, public resolution, and sticker PDFs."""

import uuid


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
    return resp.json()


async def test_qr_token_issue_resolve_and_sticker(client, admin_headers):
    machine = await _make_machine(client, admin_headers)

    resp = await client.post(f"/qr/machines/{machine['id']}/tokens", headers=admin_headers)
    assert resp.status_code == 201
    token = resp.json()["token"]

    resp = await client.get(f"/a/{token}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["machine_id"] == machine["id"]

    resp = await client.get(f"/qr/machines/{machine['id']}/sticker.pdf", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"

    # Rotating issues a new token and invalidates the old one.
    resp = await client.post(f"/qr/machines/{machine['id']}/tokens", headers=admin_headers)
    new_token = resp.json()["token"]
    assert new_token != token

    resp = await client.get(f"/a/{token}")
    assert resp.status_code == 404

    resp = await client.get(f"/a/{new_token}")
    assert resp.status_code == 200


async def test_resolve_unknown_token(client):
    resp = await client.get("/a/does-not-exist")
    assert resp.status_code == 404


async def test_sticker_requires_an_issued_token(client, admin_headers):
    machine = await _make_machine(client, admin_headers)
    resp = await client.get(f"/qr/machines/{machine['id']}/sticker.pdf", headers=admin_headers)
    assert resp.status_code == 404


async def test_sticker_export_bulk(client, admin_headers):
    machine1 = await _make_machine(client, admin_headers)
    machine2 = await _make_machine(client, admin_headers)
    await client.post(f"/qr/machines/{machine1['id']}/tokens", headers=admin_headers)
    await client.post(f"/qr/machines/{machine2['id']}/tokens", headers=admin_headers)

    resp = await client.post(
        "/qr/stickers/export",
        json={"machine_ids": [machine1["id"], machine2["id"]]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


async def test_qr_token_issue_requires_write_role(client, admin_headers):
    machine = await _make_machine(client, admin_headers)
    resp = await client.post(f"/qr/machines/{machine['id']}/tokens")
    assert resp.status_code == 401
