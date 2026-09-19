import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.db import SessionLocal
from app.models import KnowledgeItem, Page, Suggestion, User
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
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def page(db) -> Page:
    page = Page(fb_page_id="500000000000001", name="Learn Page", access_token_encrypted="x")
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


@pytest.fixture
def reviewer(db) -> User:
    user = User(email="reviewer@hateco.vn", password_hash="h", role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def stub_miner(monkeypatch, *entries: dict) -> None:
    batch = learning.SuggestionBatch(
        entries=[learning.SuggestedEntry(**entry) for entry in entries]
    )

    class StubMiner:
        def invoke(self, _prompt):
            return batch

    monkeypatch.setattr(learning, "build_miner", lambda model="": StubMiner())


def test_normalize_collapses_case_and_whitespace():
    assert learning.normalize("  Học   PHÍ bao nhiêu? ") == "học phí bao nhiêu?"


def test_collect_questions_returns_inbound_text_only(db, page):
    conversation_service.log_message(db, page.id, "psid-1", "in", "Học phí bao nhiêu?")
    conversation_service.log_message(db, page.id, "psid-1", "out", "15 triệu em nhé")

    assert learning.collect_questions(db, page.id) == ["Học phí bao nhiêu?"]


def test_collect_questions_skips_empty_and_overlong_messages(db, page):
    conversation_service.log_message(db, page.id, "psid-1", "in", "  ")
    conversation_service.log_message(db, page.id, "psid-1", "in", "ok")
    conversation_service.log_message(db, page.id, "psid-1", "in", "x" * 400)
    conversation_service.log_message(db, page.id, "psid-1", "in", "Trường ở đâu ạ?")

    assert learning.collect_questions(db, page.id) == ["Trường ở đâu ạ?"]


def test_mining_creates_pending_suggestions(db, page, monkeypatch):
    conversation_service.log_message(db, page.id, "psid-1", "in", "Học phí bao nhiêu?")
    stub_miner(
        monkeypatch,
        {"question": "Học phí bao nhiêu?", "answer": "15 triệu mỗi kỳ.", "occurrences": 4},
    )

    created = learning.mine_suggestions(db, page.id)

    assert len(created) == 1
    assert created[0].status == "pending"
    assert created[0].occurrences == 4


def test_mining_with_no_questions_creates_nothing(db, page, monkeypatch):
    stub_miner(
        monkeypatch, {"question": "Bất kỳ", "answer": "Không nên tạo", "occurrences": 1}
    )

    assert learning.mine_suggestions(db, page.id) == []


def test_mining_skips_questions_already_in_the_knowledge_base(db, page, monkeypatch):
    conversation_service.log_message(db, page.id, "psid-1", "in", "Học phí bao nhiêu?")
    db.add(
        KnowledgeItem(page_id=page.id, title="Học phí bao nhiêu?", content="15 triệu.")
    )
    db.commit()
    stub_miner(
        monkeypatch,
        {"question": "  học phí BAO NHIÊU? ", "answer": "15 triệu.", "occurrences": 3},
    )

    assert learning.mine_suggestions(db, page.id) == []


def test_mining_twice_does_not_duplicate_a_pending_suggestion(db, page, monkeypatch):
    conversation_service.log_message(db, page.id, "psid-1", "in", "Học phí bao nhiêu?")
    stub_miner(
        monkeypatch,
        {"question": "Học phí bao nhiêu?", "answer": "15 triệu.", "occurrences": 3},
    )
    learning.mine_suggestions(db, page.id)

    learning.mine_suggestions(db, page.id)

    assert db.query(Suggestion).count() == 1


def test_suggestions_are_scoped_to_their_page(db, page, monkeypatch):
    other = Page(fb_page_id="500000000000002", name="Other", access_token_encrypted="x")
    db.add(other)
    db.commit()
    db.refresh(other)
    conversation_service.log_message(db, page.id, "psid-1", "in", "Học phí bao nhiêu?")
    stub_miner(
        monkeypatch,
        {"question": "Học phí bao nhiêu?", "answer": "15 triệu.", "occurrences": 2},
    )

    learning.mine_suggestions(db, page.id)

    assert db.query(Suggestion).filter(Suggestion.page_id == other.id).count() == 0


def test_miner_failure_creates_nothing_and_does_not_raise(db, page, monkeypatch):
    conversation_service.log_message(db, page.id, "psid-1", "in", "Học phí bao nhiêu?")

    class ExplodingMiner:
        def invoke(self, _prompt):
            raise RuntimeError("LLM is down")

    monkeypatch.setattr(learning, "build_miner", lambda model="": ExplodingMiner())

    assert learning.mine_suggestions(db, page.id) == []


def test_miner_returning_nothing_creates_nothing_and_does_not_raise(
    db, page, monkeypatch
):
    conversation_service.log_message(db, page.id, "psid-1", "in", "Học phí bao nhiêu?")

    class UnparsableMiner:
        def invoke(self, _prompt):
            return None

    monkeypatch.setattr(learning, "build_miner", lambda model="": UnparsableMiner())

    assert learning.mine_suggestions(db, page.id) == []


def test_approving_creates_a_learned_knowledge_item(db, page, reviewer):
    suggestion = Suggestion(
        page_id=page.id, question="Học phí bao nhiêu?", answer="15 triệu.", occurrences=3
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)

    item = learning.approve_suggestion(db, suggestion, reviewer)

    assert item.source == "learned"
    assert item.title == "Học phí bao nhiêu?"
    assert item.content == "15 triệu."
    assert suggestion.status == "approved"
    assert suggestion.knowledge_item_id == item.id
    assert suggestion.reviewed_by_id == reviewer.id


def test_approving_with_edits_uses_the_edited_text(db, page, reviewer):
    suggestion = Suggestion(
        page_id=page.id, question="Học phí?", answer="15 triệu.", occurrences=1
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)

    item = learning.approve_suggestion(
        db, suggestion, reviewer, title="Học phí hệ chính quy", answer="20 triệu mỗi kỳ."
    )

    assert item.title == "Học phí hệ chính quy"
    assert item.content == "20 triệu mỗi kỳ."


def test_approved_knowledge_becomes_searchable(db, page, reviewer):
    suggestion = Suggestion(
        page_id=page.id, question="Học phí bao nhiêu?", answer="15 triệu.", occurrences=1
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)

    learning.approve_suggestion(db, suggestion, reviewer)

    assert "15 triệu." in vector_store.search(db, page.id, "học phí", k=1)[0]


def test_rejecting_marks_the_suggestion_and_adds_no_knowledge(db, page, reviewer):
    suggestion = Suggestion(
        page_id=page.id, question="Câu hỏi lạ", answer="Trả lời sai", occurrences=1
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)

    learning.reject_suggestion(db, suggestion, reviewer)

    assert suggestion.status == "rejected"
    assert suggestion.reviewed_by_id == reviewer.id
    assert db.query(KnowledgeItem).count() == 0
