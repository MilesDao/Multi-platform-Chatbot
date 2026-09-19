import pytest

from app.services import chatbot


@pytest.fixture(autouse=True)
def stub_answer(monkeypatch):
    monkeypatch.setattr(
        chatbot,
        "generate_answer",
        lambda db, page, question: (f"Trả lời cho: {question}", ["Học phí 15 triệu."]),
    )


def test_test_chat_returns_the_answer_and_the_context(client, admin_token, auth, page_id):
    response = client.post(
        f"/api/pages/{page_id}/test-chat",
        headers=auth(admin_token),
        json={"message": "Học phí bao nhiêu?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Trả lời cho: Học phí bao nhiêu?",
        "context": ["Học phí 15 triệu."],
    }


def test_test_chat_does_not_log_a_conversation(client, admin_token, auth, page_id):
    client.post(
        f"/api/pages/{page_id}/test-chat",
        headers=auth(admin_token),
        json={"message": "Học phí bao nhiêu?"},
    )

    listing = client.get(
        f"/api/pages/{page_id}/conversations", headers=auth(admin_token)
    )

    assert listing.json() == []


def test_empty_message_is_rejected(client, admin_token, auth, page_id):
    response = client.post(
        f"/api/pages/{page_id}/test-chat", headers=auth(admin_token), json={"message": ""}
    )

    assert response.status_code == 422


def test_viewer_cannot_use_test_chat(
    client, admin_token, member_token, auth, page_id, member_user
):
    client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "viewer"},
    )

    response = client.post(
        f"/api/pages/{page_id}/test-chat",
        headers=auth(member_token),
        json={"message": "Xin chào"},
    )

    assert response.status_code == 403
