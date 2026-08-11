"""API-level tests for chat session lifecycle and canned-reply messages."""

import uuid


def _phone() -> str:
    return f"+9198{uuid.uuid4().int % 10**8:08d}"


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


async def test_chat_session_and_canned_reply(client, admin_headers):
    machine = await _make_machine(client, admin_headers)

    resp = await client.post("/auth/login-phone", json={"phone": _phone()})
    op_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = await client.post(
        "/chat/sessions", json={"machine_id": machine["id"]}, headers=op_headers
    )
    assert resp.status_code == 201
    session = resp.json()
    assert session["status"] == "active"

    resp = await client.post(
        f"/chat/sessions/{session['id']}/messages",
        json={"content": "the camera feed is frozen"},
        headers=op_headers,
    )
    assert resp.status_code == 201
    messages = resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert "camera" in messages[1]["content"].lower() or "cable" in messages[1]["content"].lower()

    resp = await client.get(f"/chat/sessions/{session['id']}/messages", headers=op_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Another operator cannot see or post into this session.
    resp = await client.post("/auth/login-phone", json={"phone": _phone()})
    other_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    resp = await client.get(f"/chat/sessions/{session['id']}/messages", headers=other_headers)
    assert resp.status_code == 403

    # Admin (staff) can see any session.
    resp = await client.get(f"/chat/sessions/{session['id']}/messages", headers=admin_headers)
    assert resp.status_code == 200


async def test_chat_fallback_reply_for_unmatched_message(client, admin_headers):
    machine = await _make_machine(client, admin_headers)
    resp = await client.post("/auth/login-phone", json={"phone": _phone()})
    op_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    resp = await client.post(
        "/chat/sessions", json={"machine_id": machine["id"]}, headers=op_headers
    )
    session_id = resp.json()["id"]

    resp = await client.post(
        f"/chat/sessions/{session_id}/messages",
        json={"content": "completely unrelated gibberish"},
        headers=op_headers,
    )
    assert resp.status_code == 201
    assert "ticket" in resp.json()[1]["content"].lower()


async def test_chat_session_requires_auth(client):
    resp = await client.post("/chat/sessions", json={"machine_id": str(uuid.uuid4())})
    assert resp.status_code == 401
