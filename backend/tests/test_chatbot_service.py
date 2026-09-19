import pytest

from app.db import SessionLocal
from app.models import KnowledgeItem, Page
from app.services import chatbot, vector_store


class StubLLM:
    """Records the prompt it was given and returns a canned message."""

    def __init__(self, content: str = "Chào em, trường trả lời như sau."):
        self.content = content
        self.last_prompt: str | None = None

    def invoke(self, prompt: str):
        self.last_prompt = prompt
        return type("AIMessage", (), {"content": self.content})()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def stub_llm(monkeypatch) -> StubLLM:
    llm = StubLLM()
    monkeypatch.setattr(chatbot, "build_llm", lambda model="", temperature=0.7: llm)
    return llm


@pytest.fixture(autouse=True)
def fake_context(monkeypatch):
    monkeypatch.setattr(
        vector_store, "search", lambda db, page_id, query, k=3: ["Học phí 15 triệu."]
    )


def make_page(db, **kwargs) -> Page:
    page = Page(
        fb_page_id=kwargs.pop("fb_page_id", "800000000000001"),
        name="Chat Page",
        access_token_encrypted="x",
        **kwargs,
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def test_generate_answer_returns_the_llm_content_and_the_context(db, stub_llm):
    page = make_page(db)

    answer, context = chatbot.generate_answer(db, page, "Học phí bao nhiêu?")

    assert answer == "Chào em, trường trả lời như sau."
    assert context == ["Học phí 15 triệu."]


def test_prompt_contains_the_question_and_the_context(db, stub_llm):
    page = make_page(db)

    chatbot.generate_answer(db, page, "Học phí bao nhiêu?")

    assert "Học phí bao nhiêu?" in stub_llm.last_prompt
    assert "Học phí 15 triệu." in stub_llm.last_prompt


def test_page_system_prompt_is_used_when_set(db, stub_llm):
    page = make_page(db, system_prompt="Bạn là trợ lý của trung tâm ngoại ngữ.")

    chatbot.generate_answer(db, page, "Xin chào")

    assert "Bạn là trợ lý của trung tâm ngoại ngữ." in stub_llm.last_prompt
    assert chatbot.DEFAULT_SYSTEM_PROMPT not in stub_llm.last_prompt


def test_default_system_prompt_is_used_when_page_prompt_is_blank(db, stub_llm):
    page = make_page(db, system_prompt="   ")

    chatbot.generate_answer(db, page, "Xin chào")

    assert chatbot.DEFAULT_SYSTEM_PROMPT in stub_llm.last_prompt


def test_page_model_override_is_passed_to_the_llm_factory(db, monkeypatch):
    captured: dict[str, str] = {}

    def fake_build_llm(model: str = "", temperature: float = 0.7):
        captured["model"] = model
        return StubLLM()

    monkeypatch.setattr(chatbot, "build_llm", fake_build_llm)
    page = make_page(db, llm_model="anthropic/claude-sonnet-5")

    chatbot.generate_answer(db, page, "Xin chào")

    assert captured["model"] == "anthropic/claude-sonnet-5"
