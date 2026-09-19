import json

from sqlalchemy.orm import Session

from app.models import Conversation, Message, utcnow

VALID_DIRECTIONS = {"in", "out"}


def get_or_create_conversation(db: Session, page_id: int, psid: str) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.page_id == page_id, Conversation.psid == psid)
        .one_or_none()
    )
    if conversation is None:
        conversation = Conversation(page_id=page_id, psid=psid)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    return conversation


def log_message(
    db: Session,
    page_id: int,
    psid: str,
    direction: str,
    text: str,
    attachments: list | None = None,
) -> Message:
    """Persist one message and bump the conversation's activity timestamp."""
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"direction must be one of {sorted(VALID_DIRECTIONS)}")

    conversation = get_or_create_conversation(db, page_id, psid)
    message = Message(
        conversation_id=conversation.id,
        direction=direction,
        text=text or "",
        attachments_json=json.dumps(attachments or [], ensure_ascii=False),
    )
    db.add(message)
    conversation.last_message_at = utcnow()
    db.commit()
    db.refresh(message)
    return message
