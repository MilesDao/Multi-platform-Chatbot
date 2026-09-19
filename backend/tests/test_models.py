import pytest
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import (
    Conversation,
    KnowledgeItem,
    Message,
    Page,
    PageMembership,
    User,
    role_rank,
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_page_facebook_id_is_unique(db):
    db.add(Page(fb_page_id="111", name="First", access_token_encrypted="x"))
    db.commit()

    db.add(Page(fb_page_id="111", name="Duplicate", access_token_encrypted="y"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_deleting_a_page_removes_its_knowledge(db):
    page = Page(fb_page_id="222", name="Second", access_token_encrypted="x")
    db.add(page)
    db.commit()
    db.add(KnowledgeItem(page_id=page.id, title="Hoc phi", content="15 trieu"))
    db.commit()

    db.delete(page)
    db.commit()

    assert db.query(KnowledgeItem).count() == 0


def test_conversation_collects_messages_in_order(db):
    page = Page(fb_page_id="333", name="Third", access_token_encrypted="x")
    db.add(page)
    db.commit()
    conversation = Conversation(page_id=page.id, psid="psid-1")
    db.add(conversation)
    db.commit()
    db.add(Message(conversation_id=conversation.id, direction="in", text="Xin chao"))
    db.add(Message(conversation_id=conversation.id, direction="out", text="Chao em"))
    db.commit()
    db.refresh(conversation)

    assert [m.direction for m in conversation.messages] == ["in", "out"]


def test_membership_is_unique_per_user_and_page(db):
    page = Page(fb_page_id="444", name="Fourth", access_token_encrypted="x")
    user = User(email="a@b.com", password_hash="h", role="member")
    db.add_all([page, user])
    db.commit()
    db.add(PageMembership(page_id=page.id, user_id=user.id, role="editor"))
    db.commit()

    db.add(PageMembership(page_id=page.id, user_id=user.id, role="viewer"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_role_rank_orders_viewer_below_editor_below_owner():
    assert role_rank("viewer") < role_rank("editor") < role_rank("owner")
    assert role_rank("nonsense") == 0
