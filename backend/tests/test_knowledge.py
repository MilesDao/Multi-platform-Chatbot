import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.services import vector_store


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    embeddings = DeterministicFakeEmbedding(size=32)
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: embeddings)
    vector_store.clear_cache()
    yield
    vector_store.clear_cache()


def test_editor_can_create_a_knowledge_item(client, admin_token, auth, page_id):
    response = client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(admin_token),
        json={"title": "Học phí", "content": "15 triệu mỗi kỳ."},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Học phí"
    assert body["source"] == "manual"
    assert body["is_active"] is True


def test_creating_knowledge_makes_it_searchable(client, admin_token, auth, page_id):
    client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(admin_token),
        json={"title": "Học phí", "content": "15 triệu mỗi kỳ."},
    )

    from app.db import SessionLocal

    session = SessionLocal()
    try:
        results = vector_store.search(session, page_id, "học phí", k=1)
    finally:
        session.close()

    assert "15 triệu mỗi kỳ." in results[0]


def test_listing_knowledge_returns_items_for_that_page_only(
    client, admin_token, auth, page_id
):
    client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(admin_token),
        json={"title": "A", "content": "Nội dung A"},
    )
    other = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "555555555555555", "name": "Other", "access_token": "t"},
    ).json()["id"]
    client.post(
        f"/api/pages/{other}/knowledge",
        headers=auth(admin_token),
        json={"title": "B", "content": "Nội dung B"},
    )

    response = client.get(f"/api/pages/{page_id}/knowledge", headers=auth(admin_token))

    assert [item["title"] for item in response.json()] == ["A"]


def test_updating_a_knowledge_item_changes_its_content(
    client, admin_token, auth, page_id
):
    item_id = client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(admin_token),
        json={"title": "Học phí", "content": "15 triệu."},
    ).json()["id"]

    response = client.patch(
        f"/api/pages/{page_id}/knowledge/{item_id}",
        headers=auth(admin_token),
        json={"content": "20 triệu."},
    )

    assert response.status_code == 200
    assert response.json()["content"] == "20 triệu."


def test_deleting_a_knowledge_item_removes_it(client, admin_token, auth, page_id):
    item_id = client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(admin_token),
        json={"title": "Tạm", "content": "Xoá tôi đi."},
    ).json()["id"]

    response = client.delete(
        f"/api/pages/{page_id}/knowledge/{item_id}", headers=auth(admin_token)
    )
    listing = client.get(f"/api/pages/{page_id}/knowledge", headers=auth(admin_token))

    assert response.status_code == 204
    assert listing.json() == []


def test_viewer_cannot_create_knowledge(
    client, admin_token, member_token, auth, page_id, member_user
):
    client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "viewer"},
    )

    response = client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(member_token),
        json={"title": "Nope", "content": "Không được."},
    )

    assert response.status_code == 403


def test_knowledge_item_from_another_page_returns_404(client, admin_token, auth, page_id):
    other = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "666666666666666", "name": "Other", "access_token": "t"},
    ).json()["id"]
    foreign_item = client.post(
        f"/api/pages/{other}/knowledge",
        headers=auth(admin_token),
        json={"title": "B", "content": "Nội dung B"},
    ).json()["id"]

    response = client.patch(
        f"/api/pages/{page_id}/knowledge/{foreign_item}",
        headers=auth(admin_token),
        json={"content": "hijack"},
    )

    assert response.status_code == 404
