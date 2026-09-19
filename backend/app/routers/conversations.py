import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import page_viewer
from app.models import Conversation, Message, Page

router = APIRouter(prefix="/api/pages/{page_id}", tags=["conversations"])

PREVIEW_LENGTH = 120


class ConversationOut(BaseModel):
    id: int
    psid: str
    started_at: datetime
    last_message_at: datetime
    message_count: int
    last_message_preview: str


class MessageOut(BaseModel):
    id: int
    direction: str
    text: str
    attachments: list
    created_at: datetime


class ConversationDetailOut(BaseModel):
    id: int
    psid: str
    started_at: datetime
    last_message_at: datetime
    messages: list[MessageOut]


def _to_message_out(message: Message) -> MessageOut:
    try:
        attachments = json.loads(message.attachments_json or "[]")
    except json.JSONDecodeError:
        attachments = []
    return MessageOut(
        id=message.id,
        direction=message.direction,
        text=message.text,
        attachments=attachments if isinstance(attachments, list) else [],
        created_at=message.created_at,
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    page: Page = Depends(page_viewer),
    db: Session = Depends(get_db),
) -> list[ConversationOut]:
    query = db.query(Conversation).filter(Conversation.page_id == page.id)
    if q.strip():
        pattern = f"%{q.strip()}%"
        matching_ids = (
            db.query(Message.conversation_id)
            .filter(Message.text.ilike(pattern))
            .distinct()
        )
        query = query.filter(
            or_(Conversation.psid.ilike(pattern), Conversation.id.in_(matching_ids))
        )

    rows = (
        query.order_by(Conversation.last_message_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    summaries: list[ConversationOut] = []
    for conversation in rows:
        count = (
            db.query(func.count(Message.id))
            .filter(Message.conversation_id == conversation.id)
            .scalar()
            or 0
        )
        last = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.id.desc())
            .first()
        )
        summaries.append(
            ConversationOut(
                id=conversation.id,
                psid=conversation.psid,
                started_at=conversation.started_at,
                last_message_at=conversation.last_message_at,
                message_count=count,
                last_message_preview=(last.text[:PREVIEW_LENGTH] if last else ""),
            )
        )
    return summaries


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: int,
    page: Page = Depends(page_viewer),
    db: Session = Depends(get_db),
) -> ConversationDetailOut:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.page_id == page.id)
        .one_or_none()
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return ConversationDetailOut(
        id=conversation.id,
        psid=conversation.psid,
        started_at=conversation.started_at,
        last_message_at=conversation.last_message_at,
        messages=[_to_message_out(message) for message in conversation.messages],
    )
