import json

import pytest

from app.db import SessionLocal
from app.models import Conversation, Page
from app.services import conversations


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def page(db) -> Page:
    page = Page(fb_page_id="700000000000001", name="Log Page", access_token_encrypted="x")
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def test_first_message_creates_the_conversation(db, page):
    conversations.log_message(db, page.id, "psid-1", "in", "Xin chào")

    assert db.query(Conversation).count() == 1


def test_second_message_reuses_the_same_conversation(db, page):
    conversations.log_message(db, page.id, "psid-1", "in", "Xin chào")
    conversations.log_message(db, page.id, "psid-1", "out", "Chào em")

    conversation = db.query(Conversation).one()
    assert db.query(Conversation).count() == 1
    assert len(conversation.messages) == 2


def test_different_psids_get_different_conversations(db, page):
    conversations.log_message(db, page.id, "psid-1", "in", "A")
    conversations.log_message(db, page.id, "psid-2", "in", "B")

    assert db.query(Conversation).count() == 2


def test_attachments_are_stored_as_json(db, page):
    message = conversations.log_message(
        db,
        page.id,
        "psid-1",
        "in",
        "",
        attachments=[{"type": "image", "payload": {"url": "http://x/y.jpg"}}],
    )

    assert json.loads(message.attachments_json)[0]["type"] == "image"


def test_logging_advances_last_message_at(db, page):
    conversations.log_message(db, page.id, "psid-1", "in", "A")
    conversation = db.query(Conversation).one()
    original = conversation.last_message_at

    conversations.log_message(db, page.id, "psid-1", "out", "B")
    db.refresh(conversation)

    assert conversation.last_message_at >= original


def test_invalid_direction_is_rejected(db, page):
    with pytest.raises(ValueError):
        conversations.log_message(db, page.id, "psid-1", "sideways", "A")
