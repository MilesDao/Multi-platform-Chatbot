import re

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import (
    Conversation,
    KnowledgeItem,
    Message,
    Page,
    Suggestion,
    User,
    utcnow,
)
from app.services import vector_store
from app.services.chatbot import build_llm

MIN_QUESTION_LENGTH = 5
MAX_QUESTION_LENGTH = 300

MINING_PROMPT = """Bạn là chuyên viên đào tạo chatbot tuyển sinh.

Dưới đây là các câu khách đã nhắn cho fanpage. Hãy gom các câu hỏi giống nhau thành một
nhóm, và với mỗi nhóm hãy viết:
- "question": câu hỏi đại diện, viết lại cho rõ ràng, ngắn gọn.
- "answer": câu trả lời mẫu, CHỈ dựa trên phần "KIẾN THỨC HIỆN CÓ" bên dưới.
- "occurrences": số câu trong danh sách thuộc nhóm đó.

QUY TẮC:
- Bỏ qua lời chào, cảm ơn, và các câu không phải câu hỏi.
- Nếu KIẾN THỨC HIỆN CÓ không đủ để trả lời một nhóm, BỎ QUA nhóm đó.
- Tối đa 10 nhóm.

KIẾN THỨC HIỆN CÓ:
{knowledge}

CÁC CÂU KHÁCH ĐÃ NHẮN:
{questions}
"""


class SuggestedEntry(BaseModel):
    question: str = Field(description="Câu hỏi đại diện của nhóm")
    answer: str = Field(description="Câu trả lời mẫu dựa trên kiến thức hiện có")
    occurrences: int = Field(description="Số câu hỏi thuộc nhóm này", default=1)


class SuggestionBatch(BaseModel):
    entries: list[SuggestedEntry] = Field(default_factory=list)


def build_miner(model: str = ""):
    """Structured-output runnable returning a SuggestionBatch. Monkeypatched in tests."""
    return build_llm(model=model, temperature=0).with_structured_output(SuggestionBatch)


def normalize(text: str) -> str:
    """Key used for duplicate detection: lowercase, whitespace collapsed."""
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def collect_questions(db: Session, page_id: int, limit: int = 200) -> list[str]:
    """Recent inbound messages that look like they could be questions."""
    rows = (
        db.query(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(Conversation.page_id == page_id, Message.direction == "in")
        .order_by(Message.id.desc())
        .limit(limit)
        .all()
    )
    questions: list[str] = []
    for message in reversed(rows):
        text = (message.text or "").strip()
        if MIN_QUESTION_LENGTH <= len(text) <= MAX_QUESTION_LENGTH:
            questions.append(text)
    return questions


def _existing_keys(db: Session, page_id: int) -> set[str]:
    """Normalized questions we must not suggest again."""
    knowledge_titles = (
        db.query(KnowledgeItem.title)
        .filter(KnowledgeItem.page_id == page_id, KnowledgeItem.is_active.is_(True))
        .all()
    )
    open_suggestions = (
        db.query(Suggestion.question)
        .filter(Suggestion.page_id == page_id, Suggestion.status == "pending")
        .all()
    )
    return {normalize(row[0]) for row in knowledge_titles} | {
        normalize(row[0]) for row in open_suggestions
    }


def _knowledge_digest(db: Session, page_id: int, limit: int = 40) -> str:
    items = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.page_id == page_id, KnowledgeItem.is_active.is_(True))
        .order_by(KnowledgeItem.id)
        .limit(limit)
        .all()
    )
    if not items:
        return "(chưa có kiến thức nào)"
    return "\n\n".join(f"### {item.title}\n{item.content}" for item in items)


def mine_suggestions(db: Session, page_id: int, limit: int = 200) -> list[Suggestion]:
    """Draft knowledge entries from past inbound messages. Never raises."""
    questions = collect_questions(db, page_id, limit)
    if not questions:
        return []

    prompt = MINING_PROMPT.format(
        knowledge=_knowledge_digest(db, page_id),
        questions="\n".join(f"- {question}" for question in questions),
    )
    page = db.get(Page, page_id)
    model = (page.llm_model if page else "") or ""
    try:
        batch = build_miner(model).invoke(prompt)
    except Exception as exc:  # provider or parsing failure
        print(f"Suggestion mining failed for page {page_id}: {exc}")
        return []
    if batch is None:  # structured output can come back empty when parsing fails
        return []

    seen = _existing_keys(db, page_id)
    created: list[Suggestion] = []
    for entry in batch.entries:
        question = (entry.question or "").strip()
        answer = (entry.answer or "").strip()
        key = normalize(question)
        if not question or not answer or key in seen:
            continue
        seen.add(key)
        suggestion = Suggestion(
            page_id=page_id,
            question=question,
            answer=answer,
            occurrences=max(1, entry.occurrences),
            status="pending",
        )
        db.add(suggestion)
        created.append(suggestion)

    if created:
        db.commit()
        for suggestion in created:
            db.refresh(suggestion)
    return created


def approve_suggestion(
    db: Session,
    suggestion: Suggestion,
    user: User,
    title: str | None = None,
    answer: str | None = None,
) -> KnowledgeItem:
    """Promote a suggestion into the page's knowledge base and reindex."""
    item = KnowledgeItem(
        page_id=suggestion.page_id,
        title=(title or suggestion.question).strip(),
        content=(answer or suggestion.answer).strip(),
        source="learned",
        is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    suggestion.status = "approved"
    suggestion.reviewed_at = utcnow()
    suggestion.reviewed_by_id = user.id
    suggestion.knowledge_item_id = item.id
    if title is not None:
        suggestion.question = item.title
    if answer is not None:
        suggestion.answer = item.content
    db.commit()

    vector_store.build_index(db, suggestion.page_id)
    return item


def reject_suggestion(db: Session, suggestion: Suggestion, user: User) -> Suggestion:
    suggestion.status = "rejected"
    suggestion.reviewed_at = utcnow()
    suggestion.reviewed_by_id = user.id
    db.commit()
    db.refresh(suggestion)
    return suggestion
