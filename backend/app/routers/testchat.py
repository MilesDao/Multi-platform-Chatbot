from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import page_editor
from app.models import Page
from app.services import chatbot

router = APIRouter(prefix="/api/pages/{page_id}", tags=["testchat"])


class TestChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class TestChatOut(BaseModel):
    answer: str
    context: list[str]


@router.post("/test-chat", response_model=TestChatOut)
def test_chat(
    payload: TestChatIn,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
) -> TestChatOut:
    """Answer as this page would, without touching Facebook or the conversation log."""
    answer, context = chatbot.generate_answer(db, page, payload.message)
    return TestChatOut(answer=answer, context=context)
