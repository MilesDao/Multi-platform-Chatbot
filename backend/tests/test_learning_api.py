import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.db import SessionLocal
from app.models import KnowledgeItem
from app.services import conversations as conversation_service
from app.services import learning, vector_store


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    embeddings = DeterministicFakeEmbedding(size=32)
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: embeddings)
    vector_store.clear_cache()
    yield
    vector_store.clear_cache()


@pytest.fixture
def with_history(page_id) -> int:
    session = SessionLocal()
    try:
        conversation_service.log_message(
            session, page_id, "psid-1", "in", "Học phí bao nhiêu?"
        )
    finally:
        session.close()
    return page_id


@pytest.fixture
def stub_miner(monkeypatch):
    batch = learning.SuggestionBatch(
        entries=[
            learning.SuggestedEntry(
                question="Học phí bao nhiêu?", answer="15 triệu mỗi kỳ.", occurrences=5
            )
        ]
    )

    class StubMiner:
        def invoke(self, _prompt):
            return batch

    monkeypatch.setattr(learning, "build_miner", lambda model="": StubMiner())


def test_mining_returns_the_created_suggestions(
    client, admin_token, auth, with_history, stub_miner
):
    response = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert body["suggestions"][0]["question"] == "Học phí bao nhiêu?"
    assert body["suggestions"][0]["occurrences"] == 5


def test_pending_suggestions_are_listed(
    client, admin_token, auth, with_history, stub_miner
):
    client.post(f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token))

    response = client.get(
        f"/api/pages/{with_history}/suggestions",
        headers=auth(admin_token),
        params={"status": "pending"},
    )

    assert [s["status"] for s in response.json()] == ["pending"]


def test_approving_adds_a_learned_knowledge_item(
    client, admin_token, auth, with_history, stub_miner
):
    suggestion_id = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token)
    ).json()["suggestions"][0]["id"]

    response = client.post(
        f"/api/pages/{with_history}/suggestions/{suggestion_id}/approve",
        headers=auth(admin_token),
        json={},
    )
    knowledge = client.get(
        f"/api/pages/{with_history}/knowledge", headers=auth(admin_token)
    ).json()

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert [item["source"] for item in knowledge] == ["learned"]
    assert knowledge[0]["content"] == "15 triệu mỗi kỳ."


def test_approving_with_edits_stores_the_edited_answer(
    client, admin_token, auth, with_history, stub_miner
):
    suggestion_id = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token)
    ).json()["suggestions"][0]["id"]

    client.post(
        f"/api/pages/{with_history}/suggestions/{suggestion_id}/approve",
        headers=auth(admin_token),
        json={"title": "Học phí hệ chính quy", "answer": "20 triệu mỗi kỳ."},
    )

    session = SessionLocal()
    try:
        item = session.query(KnowledgeItem).one()
        assert item.title == "Học phí hệ chính quy"
        assert item.content == "20 triệu mỗi kỳ."
    finally:
        session.close()


def test_rejecting_leaves_the_knowledge_base_empty(
    client, admin_token, auth, with_history, stub_miner
):
    suggestion_id = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token)
    ).json()["suggestions"][0]["id"]

    response = client.post(
        f"/api/pages/{with_history}/suggestions/{suggestion_id}/reject",
        headers=auth(admin_token),
    )
    knowledge = client.get(
        f"/api/pages/{with_history}/knowledge", headers=auth(admin_token)
    ).json()

    assert response.json()["status"] == "rejected"
    assert knowledge == []


def test_viewer_cannot_mine(
    client, admin_token, member_token, auth, with_history, member_user, stub_miner
):
    client.put(
        f"/api/pages/{with_history}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "viewer"},
    )

    response = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(member_token)
    )

    assert response.status_code == 403


def test_suggestion_from_another_page_returns_404(
    client, admin_token, auth, with_history, stub_miner
):
    suggestion_id = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token)
    ).json()["suggestions"][0]["id"]
    other = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "777777777777777", "name": "Other", "access_token": "t"},
    ).json()["id"]

    response = client.post(
        f"/api/pages/{other}/suggestions/{suggestion_id}/approve",
        headers=auth(admin_token),
        json={},
    )

    assert response.status_code == 404
