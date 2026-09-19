import shutil

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.config import settings
from app.db import SessionLocal
from app.models import KnowledgeItem, Page
from app.services import vector_store


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    """No model download, no network: deterministic vectors."""
    embeddings = DeterministicFakeEmbedding(size=32)
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: embeddings)
    vector_store.clear_cache()
    shutil.rmtree(settings.index_dir, ignore_errors=True)
    yield
    vector_store.clear_cache()
    shutil.rmtree(settings.index_dir, ignore_errors=True)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def make_page(db, fb_page_id="900000000000001") -> Page:
    page = Page(fb_page_id=fb_page_id, name="Vector Page", access_token_encrypted="x")
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def test_empty_page_still_builds_a_searchable_index(db):
    page = make_page(db)

    results = vector_store.search(db, page.id, "bất kỳ câu hỏi nào")

    assert results == [vector_store.EMPTY_PLACEHOLDER]


def test_search_returns_active_knowledge_text(db):
    page = make_page(db)
    db.add(
        KnowledgeItem(
            page_id=page.id, title="Học phí", content="Học phí là 15 triệu mỗi kỳ."
        )
    )
    db.commit()
    vector_store.build_index(db, page.id)

    results = vector_store.search(db, page.id, "học phí bao nhiêu", k=1)

    assert "Học phí là 15 triệu mỗi kỳ." in results[0]


def test_inactive_knowledge_is_not_indexed(db):
    page = make_page(db)
    db.add(
        KnowledgeItem(
            page_id=page.id,
            title="Bí mật",
            content="Nội dung đã tắt.",
            is_active=False,
        )
    )
    db.commit()
    vector_store.build_index(db, page.id)

    results = vector_store.search(db, page.id, "bí mật")

    assert results == [vector_store.EMPTY_PLACEHOLDER]


def test_each_page_has_its_own_index(db):
    page_a = make_page(db, "900000000000002")
    page_b = make_page(db, "900000000000003")
    db.add(KnowledgeItem(page_id=page_a.id, title="A", content="Chỉ trang A biết."))
    db.add(KnowledgeItem(page_id=page_b.id, title="B", content="Chỉ trang B biết."))
    db.commit()
    vector_store.build_index(db, page_a.id)
    vector_store.build_index(db, page_b.id)

    results_b = vector_store.search(db, page_b.id, "trang nào biết", k=5)

    assert all("trang A" not in chunk for chunk in results_b)


def test_rebuilding_picks_up_new_knowledge(db):
    page = make_page(db)
    vector_store.build_index(db, page.id)
    db.add(KnowledgeItem(page_id=page.id, title="Mới", content="Thông tin vừa thêm."))
    db.commit()

    vector_store.build_index(db, page.id)
    results = vector_store.search(db, page.id, "thông tin", k=1)

    assert "Thông tin vừa thêm." in results[0]
