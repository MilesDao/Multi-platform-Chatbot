import pytest

from app.db import SessionLocal
from app.models import Conversation, Message
from app.routers import webhook
from app.services import chatbot, messenger


def build_payload(fb_page_id: str, psid: str, text: str) -> dict:
    return {
        "object": "page",
        "entry": [
            {
                "id": fb_page_id,
                "messaging": [
                    {"sender": {"id": psid}, "message": {"text": text}},
                ],
            }
        ],
    }


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Capture outbound Messenger calls and stub the LLM."""
    outbox: list[dict] = []

    monkeypatch.setattr(
        messenger,
        "send_text",
        lambda token, psid, text: outbox.append(
            {"token": token, "psid": psid, "text": text}
        )
        or True,
    )
    monkeypatch.setattr(messenger, "send_typing", lambda token, psid: True)
    monkeypatch.setattr(
        chatbot, "generate_answer", lambda db, page, question: ("Chào em!", ["ctx"])
    )
    monkeypatch.setattr(webhook, "typing_delay_seconds", lambda text: 0.0)
    return outbox


def test_verification_echoes_the_challenge(client):
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": "1158201444",
        },
    )

    assert response.status_code == 200
    assert response.text == "1158201444"


def test_verification_rejects_a_wrong_token(client):
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "1158201444",
        },
    )

    assert response.status_code == 403


def test_message_is_logged_and_answered(client, admin_token, auth, sent):
    client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={
            "fb_page_id": "300000000000001",
            "name": "Webhook Page",
            "access_token": "EAAG-webhook-token",
        },
    )

    response = client.post(
        "/webhook", json=build_payload("300000000000001", "psid-9", "Học phí bao nhiêu?")
    )

    session = SessionLocal()
    try:
        directions = [m.direction for m in session.query(Message).order_by(Message.id)]
    finally:
        session.close()

    assert response.status_code == 200
    assert directions == ["in", "out"]
    assert sent[0]["text"] == "Chào em!"
    assert sent[0]["token"] == "EAAG-webhook-token"


def test_events_route_to_the_matching_page(client, admin_token, auth, sent):
    first = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "300000000000001", "name": "One", "access_token": "tok-1"},
    ).json()["id"]
    client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "300000000000002", "name": "Two", "access_token": "tok-2"},
    )

    client.post("/webhook", json=build_payload("300000000000001", "psid-9", "Chào"))

    session = SessionLocal()
    try:
        conversation = session.query(Conversation).one()
    finally:
        session.close()

    assert conversation.page_id == first
    assert sent[0]["token"] == "tok-1"


def test_unknown_page_is_ignored(client, sent):
    response = client.post(
        "/webhook", json=build_payload("999999999999999", "psid-9", "Chào")
    )

    session = SessionLocal()
    try:
        message_count = session.query(Message).count()
    finally:
        session.close()

    assert response.status_code == 200
    assert message_count == 0
    assert sent == []


def test_inactive_page_logs_but_does_not_reply(client, admin_token, auth, sent):
    page_id = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "300000000000003", "name": "Off", "access_token": "tok-3"},
    ).json()["id"]
    client.patch(
        f"/api/pages/{page_id}", headers=auth(admin_token), json={"is_active": False}
    )

    client.post("/webhook", json=build_payload("300000000000003", "psid-9", "Chào"))

    session = SessionLocal()
    try:
        directions = [m.direction for m in session.query(Message).all()]
    finally:
        session.close()

    assert directions == ["in"]
    assert sent == []


def test_echo_messages_are_ignored(client, admin_token, auth, sent):
    client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "300000000000004", "name": "Echo", "access_token": "tok-4"},
    )
    payload = build_payload("300000000000004", "psid-9", "Chào")
    payload["entry"][0]["messaging"][0]["message"]["is_echo"] = True

    client.post("/webhook", json=payload)

    session = SessionLocal()
    try:
        message_count = session.query(Message).count()
    finally:
        session.close()

    assert message_count == 0


def test_typing_delay_is_capped_at_three_seconds():
    assert webhook.typing_delay_seconds("x" * 50) == 1.0
    assert webhook.typing_delay_seconds("x" * 10_000) == 3.0
