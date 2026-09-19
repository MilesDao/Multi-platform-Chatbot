import time

from fastapi import APIRouter, BackgroundTasks, Request, Response

from app.config import settings
from app.db import SessionLocal
from app.models import Page
from app.security import decrypt_token
from app.services import chatbot, conversations, messenger

router = APIRouter(tags=["webhook"])

MAX_TYPING_DELAY_SECONDS = 3.0
CHARS_PER_SECOND = 50


def typing_delay_seconds(text: str) -> float:
    """Human-like pause proportional to answer length, capped at 3 seconds."""
    return min(MAX_TYPING_DELAY_SECONDS, len(text) / CHARS_PER_SECOND)


def handle_event(fb_page_id: str, event: dict) -> None:
    """Process one inbound Messenger event.

    A plain `def` so FastAPI runs it in the threadpool: the LLM call and the typing
    pause must not block the event loop for other students.
    """
    psid = str(event.get("sender", {}).get("id", ""))
    message = event.get("message", {})
    text = message.get("text", "") or ""
    attachments = message.get("attachments", []) or []
    if not psid:
        return

    db = SessionLocal()
    try:
        page = db.query(Page).filter(Page.fb_page_id == fb_page_id).one_or_none()
        if page is None:
            print(f"Webhook event for unknown page {fb_page_id} ignored")
            return

        conversations.log_message(db, page.id, psid, "in", text, attachments)

        if not page.is_active:
            print(f"Page {fb_page_id} is inactive; logged without replying")
            return

        access_token = decrypt_token(page.access_token_encrypted)
        messenger.send_typing(access_token, psid)

        answer, _context = chatbot.generate_answer(db, page, text)

        time.sleep(typing_delay_seconds(answer))
        messenger.send_text(access_token, psid, answer)
        conversations.log_message(db, page.id, psid, "out", answer)
    finally:
        db.close()


@router.get("/webhook")
async def verify_webhook(request: Request) -> Response:
    """Facebook calls this once to verify the callback URL."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge") or ""

    if not mode or not token:
        return Response(content="Bad Request", status_code=400)
    if mode == "subscribe" and token == settings.verify_token:
        return Response(content=challenge, status_code=200)
    return Response(content="Forbidden", status_code=403)


@router.post("/webhook")
async def receive_webhook(
    request: Request, background_tasks: BackgroundTasks
) -> Response:
    body = await request.json()
    if body.get("object") != "page":
        return Response(content="Not Found", status_code=404)

    for entry in body.get("entry", []):
        fb_page_id = str(entry.get("id", ""))
        for event in entry.get("messaging", []):
            message = event.get("message")
            if not message or message.get("is_echo"):
                continue
            background_tasks.add_task(handle_event, fb_page_id, event)

    return Response(content="EVENT_RECEIVED", status_code=200)
