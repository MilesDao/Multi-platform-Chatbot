# Hateco Chatbot Admin Console — Specification

**Date:** 2026-09-18
**Status:** Approved for planning

## 1. Problem

The current system (`main.py`, `chatbot_engine.py`, `lead_manager.py`, `config.py`) serves
exactly one Facebook Page. Its knowledge base is a folder of `.txt` files read once at
process start. Its answering instructions are a Python string literal, and that literal
also tries to extract enrollment paperwork (CCCD, transcript photos, phone number, major,
address) out of the conversation — a job that belongs to a human counsellor on a phone
call, not a chatbot. Changing anything requires editing code and restarting the server,
and there is no record of what the bot has been saying.

## 2. Goal

The chatbot's actual job: answer questions from students and parents that counsellors
can't take outside office hours, then point them to call in for real consultation and to
finalize enrollment. It is a **Q&A and hand-off tool**, not an intake form — it never
collects or stores applicant paperwork or personal details.

A web admin console where an operator can:

1. Register every Facebook Page connected to the chatbot and manage them side by side.
2. Curate a separate knowledge base per page.
3. Write the answering instructions (system prompt) and the phone hand-off message per page.
4. Read the conversations each page has had.
5. Let the system mine those conversations for recurring questions, review the drafted
   answers, and promote the good ones into the page's knowledge base — so the next
   conversation is answered better than the last.

## 3. Users and roles

Multi-user with two levels.

**Global role** on `User.role`:
- `admin` — creates and deactivates users, creates pages, has full access to every page
  regardless of membership.
- `member` — sees only pages they are a member of.

**Per-page role** on `PageMembership.role`, ranked `viewer` < `editor` < `owner`:
- `viewer` — read knowledge, conversations, suggestions.
- `editor` — everything a viewer can do, plus create/edit/delete knowledge, edit the
  system prompt and hand-off message, run mining, approve/reject suggestions, use the
  test chat.
- `owner` — everything an editor can do, plus edit page settings (name, access token,
  active flag), manage that page's members, and delete the page.

A global `admin` is treated as `owner` on every page.

The first user is created through a one-time bootstrap endpoint that refuses to run once
any user exists.

## 4. Functional requirements

### 4.1 Page management
- Register a page with: Facebook Page ID, display name, Page Access Token.
- The Page Access Token is encrypted at rest (Fernet) and is **never** returned by the API.
  Responses expose only a boolean `has_access_token`.
- Pages can be deactivated. An inactive page's webhook events are logged but not answered.
- Facebook Page ID is unique across the system.

### 4.2 Content per page
- A page owns a list of knowledge items, each `{title, content, source, is_active}`.
- `source` is one of `manual` (typed by a human), `learned` (promoted from a suggestion),
  `imported` (from the legacy `data/*.txt` seed).
- Only `is_active` items are retrievable.
- Editing, activating, or deleting an item rebuilds that page's vector index immediately.

### 4.3 Instructions per page
- Each page has a free-text `system_prompt` and an optional `llm_model` override.
- A page with an empty `system_prompt` falls back to a shipped default persona: a friendly
  Vietnamese admissions counsellor who answers from the page's knowledge and does **not**
  ask for or collect enrollment paperwork.
- Each page also has a `closing_message`: a short, operator-written line pointing the
  student to call in for further consultation and to finalize enrollment (e.g. a hotline
  number). When set, it is appended verbatim after every generated answer, so the hand-off
  is consistent regardless of what the LLM says. When empty, nothing is appended.

### 4.4 Conversation logging
- Every inbound and outbound message is persisted with its page, PSID, direction, text,
  attachment metadata, and timestamp.
- Conversations are listable per page, newest activity first, searchable by message text
  and by PSID, and openable as a full transcript.

### 4.5 Learning loop (review queue)
The learning loop is **human-gated**. Nothing reaches a knowledge base without approval.

1. An editor triggers mining for a page (on demand, from the UI).
2. The miner collects recent inbound messages for that page, keeps question-shaped ones,
   and asks the LLM — given the page's existing active knowledge as grounding — to group
   them into distinct recurring questions and draft an answer for each, with an
   `occurrences` count.
3. Drafts whose question duplicates an existing active knowledge item title or an existing
   pending suggestion (case-insensitive, whitespace-normalized) are discarded.
4. The rest are stored as `Suggestion` rows with status `pending`.
5. In the UI the editor sees each pending suggestion with its question, drafted answer, and
   occurrence count, and can **approve** (optionally after editing the question/answer),
   or **reject**.
6. Approval creates a `KnowledgeItem` with `source='learned'`, links it to the suggestion,
   records reviewer and timestamp, and rebuilds the page index.

### 4.6 Webhook
- One webhook URL serves all pages. Events are routed by `entry[].id` to the matching
  `Page` row; unknown or inactive pages are ignored after logging.
- Webhook verification uses one app-level `VERIFY_TOKEN`.
- Message handling: typing indicator, RAG answer (with the page's closing message
  appended, per §4.3), length-proportional delay (max 3s), reply. No personal data is
  extracted or persisted beyond the conversation log itself.

### 4.7 Test chat
- An editor can send a message to a page from the console and see the generated answer plus
  the exact retrieved context chunks, without touching Facebook.

## 5. Non-functional requirements

- Backend: FastAPI, SQLAlchemy 2.x ORM, SQLite. Vectors stay in per-page FAISS index
  directories on disk, rebuilt from the database — the database is the source of truth.
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS v4, single-page app calling the
  JSON API. Dev server on `http://localhost:5173`, API on `http://localhost:8000`.
- Auth: JWT bearer tokens, HS256, 24h expiry. Passwords hashed with bcrypt.
- All application state lives in the database; no module-level mutable state survives a
  restart except the FAISS index cache, which is rebuildable.
- Every backend feature ships with pytest tests that run with no network access: LLM calls
  and embedding models are injected and stubbed in tests.
- The legacy `data/*.txt` files are imported by a seed script, not deleted.

## 6. Out of scope

- Collecting, extracting, or storing applicant paperwork or personal details (ID photos,
  transcript photos, phone number, major, address) or any other enrollment-intake data.
  The bot answers questions and hands off to a phone consultation; it does not run
  enrollment intake, and there is no "lead" concept or per-student state at all.
- OCR or classification of attachments — the bot does not process images.
- Scheduled/automatic mining — mining is triggered manually from the UI.
- Facebook OAuth page-connect flow — tokens are pasted in by the operator.
- Analytics dashboards and charts.
- Multi-language UI — the console is in English, the bot answers in Vietnamese.

## 7. Global constraints

- Python 3.11+.
- Node 20+.
- SQLAlchemy 2.x declarative style (`DeclarativeBase`, `Mapped`, `mapped_column`).
- Tailwind CSS v4 via `@tailwindcss/vite` — no `tailwind.config.js`, no PostCSS config.
- All API routes are prefixed `/api`, except `GET /webhook` and `POST /webhook`.
- Page Access Tokens must never appear in an API response, a log line, or the frontend.
- Bot-facing copy stays Vietnamese; console UI copy is English.
- No test may make a real network call.
