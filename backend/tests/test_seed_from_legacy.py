import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.db import SessionLocal
from app.models import KnowledgeItem
from app.services import vector_store
from scripts.seed_from_legacy import seed_page


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    embeddings = DeterministicFakeEmbedding(size=32)
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: embeddings)
    vector_store.clear_cache()
    yield
    vector_store.clear_cache()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "Học phí.txt").write_text("Học phí 15 triệu.", encoding="utf-8")
    (tmp_path / "Ngành nghề.txt").write_text("CNTT, Kế toán.", encoding="utf-8")
    (tmp_path / "notes.md").write_text("ignore me", encoding="utf-8")
    return tmp_path


def test_seeding_imports_every_txt_file(db, data_dir):
    page, count = seed_page(db, "111000111", "Legacy Page", "tok", data_dir)

    titles = {item.title for item in db.query(KnowledgeItem).all()}
    assert count == 2
    assert titles == {"Học phí", "Ngành nghề"}
    assert all(item.page_id == page.id for item in db.query(KnowledgeItem).all())


def test_imported_items_are_marked_with_the_imported_source(db, data_dir):
    seed_page(db, "111000111", "Legacy Page", "tok", data_dir)

    assert {item.source for item in db.query(KnowledgeItem).all()} == {"imported"}


def test_seeding_twice_does_not_duplicate_items(db, data_dir):
    seed_page(db, "111000111", "Legacy Page", "tok", data_dir)

    _, second_count = seed_page(db, "111000111", "Legacy Page", "tok", data_dir)

    assert second_count == 0
    assert db.query(KnowledgeItem).count() == 2


def test_seeded_content_is_searchable(db, data_dir):
    page, _ = seed_page(db, "111000111", "Legacy Page", "tok", data_dir)

    results = vector_store.search(db, page.id, "học phí", k=2)

    assert any("15 triệu" in chunk for chunk in results)


def test_missing_data_directory_imports_nothing(db, tmp_path):
    page, count = seed_page(db, "111000111", "Legacy Page", "tok", tmp_path / "nope")

    assert count == 0
    assert page.id is not None
