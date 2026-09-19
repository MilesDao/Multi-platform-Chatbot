import pytest

from app.db import SessionLocal
from app.services import conversations as conversation_service


@pytest.fixture
def seeded(page_id) -> int:
    session = SessionLocal()
    try:
        conversation_service.log_message(session, page_id, "psid-a", "in", "Học phí bao nhiêu?")
        conversation_service.log_message(session, page_id, "psid-a", "out", "15 triệu em nhé")
        conversation_service.log_message(session, page_id, "psid-b", "in", "Trường ở đâu ạ?")
    finally:
        session.close()
    return page_id


def test_listing_conversations_returns_both_threads(client, admin_token, auth, seeded):
    response = client.get(
        f"/api/pages/{seeded}/conversations", headers=auth(admin_token)
    )

    assert response.status_code == 200
    assert {c["psid"] for c in response.json()} == {"psid-a", "psid-b"}


def test_conversation_summary_includes_counts_and_preview(
    client, admin_token, auth, seeded
):
    rows = client.get(
        f"/api/pages/{seeded}/conversations", headers=auth(admin_token)
    ).json()
    thread_a = next(c for c in rows if c["psid"] == "psid-a")

    assert thread_a["message_count"] == 2
    assert thread_a["last_message_preview"] == "15 triệu em nhé"


def test_search_filters_by_message_text(client, admin_token, auth, seeded):
    response = client.get(
        f"/api/pages/{seeded}/conversations",
        headers=auth(admin_token),
        params={"q": "Trường ở đâu"},
    )

    assert [c["psid"] for c in response.json()] == ["psid-b"]


def test_search_also_matches_the_psid(client, admin_token, auth, seeded):
    response = client.get(
        f"/api/pages/{seeded}/conversations",
        headers=auth(admin_token),
        params={"q": "psid-a"},
    )

    assert [c["psid"] for c in response.json()] == ["psid-a"]


def test_transcript_returns_messages_in_order(client, admin_token, auth, seeded):
    listing = client.get(
        f"/api/pages/{seeded}/conversations", headers=auth(admin_token)
    ).json()
    thread_a = next(c for c in listing if c["psid"] == "psid-a")

    response = client.get(
        f"/api/pages/{seeded}/conversations/{thread_a['id']}", headers=auth(admin_token)
    )

    assert response.status_code == 200
    assert [m["text"] for m in response.json()["messages"]] == [
        "Học phí bao nhiêu?",
        "15 triệu em nhé",
    ]


def test_transcript_from_another_page_returns_404(client, admin_token, auth, seeded):
    other = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "444444444444444", "name": "Other", "access_token": "t"},
    ).json()["id"]
    listing = client.get(
        f"/api/pages/{seeded}/conversations", headers=auth(admin_token)
    ).json()

    response = client.get(
        f"/api/pages/{other}/conversations/{listing[0]['id']}", headers=auth(admin_token)
    )

    assert response.status_code == 404


def test_outsider_cannot_read_conversations(client, member_token, auth, seeded):
    response = client.get(
        f"/api/pages/{seeded}/conversations", headers=auth(member_token)
    )

    assert response.status_code == 403
