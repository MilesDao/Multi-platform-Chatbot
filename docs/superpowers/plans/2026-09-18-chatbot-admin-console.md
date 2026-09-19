# Hateco Chatbot Admin Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single-page Hateco Facebook chatbot into a multi-page product with a web console for managing pages, per-page knowledge and instructions, conversation history, and a human-reviewed learning loop that promotes mined answers into each page's knowledge base.

**Architecture:** A FastAPI backend (`backend/app`) backed by SQLite through SQLAlchemy 2.x becomes the source of truth for pages, knowledge, conversations and suggestions. Per-page FAISS indexes on disk are derived caches rebuilt from knowledge rows. A React + Vite + Tailwind SPA (`frontend/`) talks to the JSON API with a JWT bearer token. One webhook URL serves every page, routed by the Facebook Page ID in the payload. The bot is a pure Q&A + hand-off tool — it never collects or stores applicant paperwork; each page's `closing_message` is appended after every generated answer to point students to call in for consultation and enrollment.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x, SQLite, PyJWT, bcrypt, cryptography (Fernet), LangChain + FAISS + HuggingFace embeddings, OpenRouter via `langchain-openai`, pytest; React 18, TypeScript, Vite, Tailwind CSS v4, React Router 7, Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-09-18-chatbot-admin-console.md`

## Global Constraints

- Python 3.11+; Node 20+.
- SQLAlchemy 2.x declarative style only: `DeclarativeBase`, `Mapped[...]`, `mapped_column(...)`.
- Tailwind CSS v4 via the `@tailwindcss/vite` plugin. No `tailwind.config.js`, no `postcss.config.js`.
- All API routes are prefixed `/api`, except `GET /webhook` and `POST /webhook`.
- Page Access Tokens are encrypted at rest with Fernet and must never appear in an API response, a log line, or the frontend. Page responses expose only `has_access_token: bool`.
- Role ranking is `viewer` (1) < `editor` (2) < `owner` (3). A `User.role == "admin"` is treated as `owner` on every page.
- Bot-facing copy is Vietnamese. Console UI copy is English.
- No test may make a real network call. LLM clients and embedding models are obtained through module-level factory functions so tests can monkeypatch them.
- The frontend dev server runs on `http://localhost:5173`; the API on `http://localhost:8000`.
- Every task ends with a commit. Commit messages use Conventional Commits (`feat:`, `test:`, `chore:`, `refactor:`).

---

## File Structure

### Backend — `backend/`

| File | Responsibility |
|---|---|
| `app/config.py` | `Settings` (pydantic-settings) + the `settings` singleton. Paths, secrets, model names. |
| `app/db.py` | SQLAlchemy `engine`, `SessionLocal`, `Base`, `get_db()` dependency, `init_db()`. |
| `app/models.py` | All ORM models. One file — they are small and always change together. |
| `app/security.py` | Password hashing, JWT encode/decode, Fernet token encryption. No FastAPI imports. |
| `app/deps.py` | FastAPI dependencies: `get_current_user`, `require_admin`, `page_viewer/editor/owner`. |
| `app/main.py` | App factory, CORS, lifespan, router registration, `/api/health`. |
| `app/routers/auth.py` | Bootstrap, login, `/me`. Owns its request/response models. |
| `app/routers/users.py` | Admin-only user CRUD. |
| `app/routers/pages.py` | Page CRUD + page settings. |
| `app/routers/members.py` | Per-page membership management. |
| `app/routers/knowledge.py` | Knowledge item CRUD + index rebuild triggers. |
| `app/routers/conversations.py` | Conversation list/search/transcript. |
| `app/routers/learning.py` | Mine trigger, suggestion list, approve, reject. |
| `app/routers/testchat.py` | Console-only answer generation. |
| `app/routers/webhook.py` | Facebook verification + multi-page event routing. |
| `app/services/vector_store.py` | Per-page FAISS build/load/search/invalidate. |
| `app/services/chatbot.py` | LLM factory + per-page prompt assembly + `generate_answer` (appends the page's `closing_message`). |
| `app/services/messenger.py` | Graph API send helpers. |
| `app/services/conversations.py` | Conversation/message persistence helpers. |
| `app/services/learning.py` | Mining, dedupe, approve/reject. |
| `scripts/seed_from_legacy.py` | One-shot import of the legacy `data/*.txt` into a page. |
| `tests/` | pytest suite mirroring the above. |

Routers own their own Pydantic request/response models — the models change whenever the
endpoint changes, so they live together. There is no central `schemas.py`.

### Frontend — `frontend/src/`

| File | Responsibility |
|---|---|
| `lib/api.ts` | `apiFetch` wrapper: base URL, bearer header, error unwrapping. |
| `lib/auth.tsx` | `AuthProvider`, `useAuth()`, token persistence in `localStorage`. |
| `components/ProtectedRoute.tsx` | Redirects to `/login` when unauthenticated. |
| `components/Layout.tsx` | Top bar, nav, sign-out. |
| `components/Tabs.tsx` | Presentational tab strip used by the page detail screen. |
| `components/TestChatPanel.tsx` | Send a message to a page, show the answer + retrieved chunks. |
| `pages/LoginPage.tsx` | Login form. |
| `pages/PagesListPage.tsx` | List + create Facebook pages. |
| `pages/PageDetailPage.tsx` | Loads one page, renders the tab shell. |
| `pages/UsersPage.tsx` | Admin-only user management. |
| `pages/tabs/KnowledgeTab.tsx` | Knowledge item CRUD. |
| `pages/tabs/InstructionsTab.tsx` | System prompt + closing message + model + test chat. |
| `pages/tabs/ConversationsTab.tsx` | Conversation list + transcript. |
| `pages/tabs/LearningTab.tsx` | Mine button + suggestion review queue. |
| `pages/tabs/MembersTab.tsx` | Page membership management. |
| `pages/tabs/SettingsTab.tsx` | Page rename, token rotation, active flag, delete. |

---

## Task 1: Project foundation

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `requirements.txt` (replaces the existing broken one at repo root)
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_health.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `app.config.settings` (a `Settings` instance with `database_url: str`, `secret_key: str`, `token_encryption_key: str`, `verify_token: str`, `openrouter_api_key: str`, `openrouter_base_url: str`, `llm_model: str`, `embedding_model: str`, `index_dir: Path`, `access_token_expire_minutes: int`, `cors_origins: list[str]`); `app.db.Base`, `app.db.engine`, `app.db.SessionLocal`, `app.db.get_db()`, `app.db.init_db()`; `app.main.app`.

- [ ] **Step 1: Initialise the git repository**

This directory is not yet a git repository. Run from the repo root:

```bash
git init
git config user.name "Hateco Dev"
git config user.email "dev@hateco.local"
```

- [ ] **Step 2: Write `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
.venv/
venv/
.env
.pytest_cache/
backend/var/
node_modules/
frontend/dist/
.DS_Store
```

- [ ] **Step 3: Write `requirements.txt`**

The existing `requirements.txt` has a corrupted last line (UTF-16 leakage:
`s e n t e n c e - t r a n s f o r m e r s`). Replace the whole file:

```text
fastapi
uvicorn[standard]
requests
pydantic
pydantic-settings
sqlalchemy>=2.0
PyJWT
bcrypt
cryptography
langchain
langchain-core
langchain-openai
langchain-community
langchain-huggingface
faiss-cpu
sentence-transformers
python-dotenv
tiktoken
pytest
httpx
```

- [ ] **Step 4: Write `.env.example`**

```dotenv
# App-level Facebook webhook verification token (one per Facebook App, not per page)
VERIFY_TOKEN=hateco_secret_verify_token_123

# JWT signing secret - change this
SECRET_KEY=change-me-to-a-long-random-string

# Fernet key for encrypting Page Access Tokens at rest.
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY=

# OpenRouter
OPENROUTER_API_KEY=
LLM_MODEL=google/gemini-2.5-flash
```

- [ ] **Step 5: Install dependencies**

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

On macOS/Linux use `.venv/bin/python` instead of `.venv/Scripts/python`.
Every `pytest` command in this plan assumes the virtualenv is active.

- [ ] **Step 6: Write `backend/pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
filterwarnings =
    ignore::DeprecationWarning
```

- [ ] **Step 7: Write the failing test**

Create `backend/tests/__init__.py` as an empty file.

Create `backend/tests/conftest.py`. The environment variables must be set **before**
`app.config` is imported, so they come first in the file:

```python
import os
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

TEST_DIR = Path(tempfile.mkdtemp(prefix="hateco-test-"))

os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_DIR / 'test.db').as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["INDEX_DIR"] = str(TEST_DIR / "indexes")
os.environ["OPENROUTER_API_KEY"] = "test-openrouter-key"
os.environ["VERIFY_TOKEN"] = "test-verify-token"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test starts from an empty schema."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
```

Create `backend/tests/test_health.py`:

```python
def test_health_endpoint_reports_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 8: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_health.py -v
```

Expected: collection error — `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 9: Write `backend/app/config.py`**

Create `backend/app/__init__.py` as an empty file, then `backend/app/config.py`:

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
VAR_DIR = BACKEND_DIR / "var"
VAR_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{(VAR_DIR / 'hateco.db').as_posix()}"
    secret_key: str = "change-me"
    token_encryption_key: str = ""
    verify_token: str = "hateco_secret_verify_token_123"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "google/gemini-2.5-flash"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    index_dir: Path = VAR_DIR / "indexes"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
settings.index_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 10: Write `backend/app/db.py`**

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base for every ORM model."""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 11: Write `backend/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="Hateco Chatbot Console", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
```

- [ ] **Step 12: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_health.py -v
```

Expected: 1 passed.

- [ ] **Step 13: Commit**

```bash
git add .gitignore .env.example requirements.txt backend/
git commit -m "feat: scaffold FastAPI backend with config, database and health check"
```

---

## Task 2: Database models

**Files:**
- Create: `backend/app/models.py`
- Modify: `backend/app/db.py` (make `init_db()` import the models before `create_all`)
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `app.db.Base`.
- Produces: ORM classes `User`, `Page`, `PageMembership`, `KnowledgeItem`, `Conversation`, `Message`, `Suggestion` in `app.models`, plus `role_rank(role: str) -> int`, `ROLE_ORDER: dict[str, int]` and `utcnow() -> datetime`. `Page` carries a `closing_message: str` column: a short operator-written line appended after every generated answer to point students to call in (see Task 12).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_models.py -v
```

Expected: collection error — `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 3: Write `backend/app/models.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ROLE_ORDER: dict[str, int] = {"viewer": 1, "editor": 2, "owner": 3}


def role_rank(role: str) -> int:
    """Rank of a per-page role. Unknown roles rank 0 so they never pass a check."""
    return ROLE_ORDER.get(role, 0)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    memberships: Mapped[list["PageMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fb_page_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    access_token_encrypted: Mapped[str] = mapped_column(Text, default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    closing_message: Mapped[str] = mapped_column(Text, default="")
    llm_model: Mapped[str] = mapped_column(String(128), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    memberships: Mapped[list["PageMembership"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )
    knowledge_items: Mapped[list["KnowledgeItem"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )


class PageMembership(Base):
    __tablename__ = "page_memberships"
    __table_args__ = (UniqueConstraint("page_id", "user_id", name="uq_page_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16), default="viewer")

    page: Mapped["Page"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16), default="manual")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    page: Mapped["Page"] = relationship(back_populates="knowledge_items")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("page_id", "psid", name="uq_page_psid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), index=True
    )
    psid: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    page: Mapped["Page"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    direction: Mapped[str] = mapped_column(String(3))  # "in" or "out"
    text: Mapped[str] = mapped_column(Text, default="")
    attachments_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), index=True
    )
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    knowledge_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="SET NULL"), nullable=True
    )

    page: Mapped["Page"] = relationship(back_populates="suggestions")
```

- [ ] **Step 4: Wire models into `init_db()`**

In `backend/app/db.py`, replace the `init_db` function so the model module is imported
before `create_all` runs:

```python
def init_db() -> None:
    from app import models  # noqa: F401  (registers the mappers)

    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_models.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py backend/app/db.py backend/tests/test_models.py
git commit -m "feat: add ORM models for pages, users, knowledge, conversations and suggestions"
```

---

## Task 3: Security primitives

**Files:**
- Create: `backend/app/security.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Consumes: `app.config.settings` (`secret_key`, `token_encryption_key`, `access_token_expire_minutes`).
- Produces: `hash_password(password: str) -> str`, `verify_password(plain: str, hashed: str) -> bool`, `create_access_token(subject: str, expires_minutes: int | None = None) -> str`, `decode_access_token(token: str) -> str | None`, `encrypt_token(plaintext: str) -> str`, `decrypt_token(ciphertext: str) -> str`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_security.py`:

```python
from app.security import (
    create_access_token,
    decode_access_token,
    decrypt_token,
    encrypt_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_not_the_password_but_verifies():
    hashed = hash_password("s3cret-pass")

    assert hashed != "s3cret-pass"
    assert verify_password("s3cret-pass", hashed) is True
    assert verify_password("wrong-pass", hashed) is False


def test_access_token_round_trips_the_subject():
    token = create_access_token("42")

    assert decode_access_token(token) == "42"


def test_expired_access_token_decodes_to_none():
    token = create_access_token("42", expires_minutes=-1)

    assert decode_access_token(token) is None


def test_tampered_access_token_decodes_to_none():
    assert decode_access_token("not-a-jwt") is None


def test_page_access_token_encryption_round_trips():
    ciphertext = encrypt_token("EAAG-super-secret-page-token")

    assert ciphertext != "EAAG-super-secret-page-token"
    assert decrypt_token(ciphertext) == "EAAG-super-secret-page-token"


def test_decrypting_empty_string_returns_empty_string():
    assert decrypt_token("") == ""
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_security.py -v
```

Expected: collection error — `ModuleNotFoundError: No module named 'app.security'`.

- [ ] **Step 3: Write `backend/app/security.py`**

```python
import base64
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    minutes = (
        settings.access_token_expire_minutes
        if expires_minutes is None
        else expires_minutes
    )
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode(
        {"sub": subject, "exp": expires_at}, settings.secret_key, algorithm=JWT_ALGORITHM
    )


def decode_access_token(token: str) -> str | None:
    """Return the token subject, or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    return str(subject) if subject is not None else None


def _fernet() -> Fernet:
    """Fernet keyed by TOKEN_ENCRYPTION_KEY, falling back to a key derived from SECRET_KEY."""
    configured = settings.token_encryption_key.strip()
    if configured:
        return Fernet(configured.encode("utf-8"))
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_security.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/security.py backend/tests/test_security.py
git commit -m "feat: add password hashing, JWT and page-token encryption"
```

---

## Task 4: Authentication API

**Files:**
- Create: `backend/app/deps.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py` (register the auth router)
- Modify: `backend/tests/conftest.py` (add the `admin_token` / `member_token` fixtures)
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `app.models.User`, `app.security.*`, `app.db.get_db`.
- Produces:
  - `app.deps.get_current_user(...) -> User` (FastAPI dependency, 401 on bad/missing token or inactive user)
  - `app.deps.require_admin(...) -> User` (403 unless `user.role == "admin"`)
  - `app.deps.bearer_scheme` — the `HTTPBearer(auto_error=False)` instance
  - Endpoints: `POST /api/auth/bootstrap`, `POST /api/auth/login`, `GET /api/auth/me`
  - Response shape `UserOut`: `{id: int, email: str, role: str, is_active: bool}`
  - Response shape `TokenOut`: `{access_token: str, token_type: "bearer", user: UserOut}`
  - Test fixtures `admin_token: str`, `member_user_id: int`, `member_token: str`, `auth(token) -> dict` header helper.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_auth.py`:

```python
def test_bootstrap_creates_the_first_admin(client):
    response = client.post(
        "/api/auth/bootstrap",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "boss@hateco.vn"
    assert body["user"]["role"] == "admin"
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_bootstrap_refuses_once_a_user_exists(client):
    client.post(
        "/api/auth/bootstrap",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )

    response = client.post(
        "/api/auth/bootstrap",
        json={"email": "second@hateco.vn", "password": "hunter2hunter2"},
    )

    assert response.status_code == 409


def test_login_returns_a_token_for_valid_credentials(client):
    client.post(
        "/api/auth/bootstrap",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_rejects_a_wrong_password(client):
    client.post(
        "/api/auth/bootstrap",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "boss@hateco.vn", "password": "not-the-password"},
    )

    assert response.status_code == 401


def test_me_returns_the_current_user(client, admin_token, auth):
    response = client.get("/api/auth/me", headers=auth(admin_token))

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_me_without_a_token_is_unauthorised(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
```

Append these fixtures to `backend/tests/conftest.py`:

```python
ADMIN_EMAIL = "admin@hateco.vn"
ADMIN_PASSWORD = "admin-password-123"
MEMBER_EMAIL = "member@hateco.vn"
MEMBER_PASSWORD = "member-password-123"


@pytest.fixture
def auth():
    """Build an Authorization header dict from a bearer token."""

    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    return _auth


@pytest.fixture
def admin_token(client) -> str:
    response = client.post(
        "/api/auth/bootstrap",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


@pytest.fixture
def member_user(client, admin_token, auth) -> dict:
    """A non-admin user. Created directly in the database so this fixture does not
    depend on the users router, which arrives in Task 5."""
    from app.db import SessionLocal
    from app.models import User
    from app.security import hash_password

    session = SessionLocal()
    try:
        user = User(
            email=MEMBER_EMAIL,
            password_hash=hash_password(MEMBER_PASSWORD),
            role="member",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return {"id": user.id, "email": user.email}
    finally:
        session.close()


@pytest.fixture
def member_token(client, member_user) -> str:
    response = client.post(
        "/api/auth/login",
        json={"email": MEMBER_EMAIL, "password": MEMBER_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_auth.py -v
```

Expected: all 6 fail with 404 Not Found (the routes do not exist yet); the fixtures
raise `AssertionError` on the bootstrap response.

- [ ] **Step 3: Write `backend/app/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise CREDENTIALS_ERROR
    subject = decode_access_token(credentials.credentials)
    if subject is None:
        raise CREDENTIALS_ERROR
    user = db.get(User, int(subject)) if subject.isdigit() else None
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )
    return user
```

- [ ] **Step 4: Write `backend/app/routers/auth.py`**

Create `backend/app/routers/__init__.py` as an empty file, then:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class CredentialsIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _token_response(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(str(user.id)),
        user=UserOut.model_validate(user),
    )


@router.post("/bootstrap", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def bootstrap(payload: CredentialsIn, db: Session = Depends(get_db)) -> TokenOut:
    """Create the very first admin. Refuses once any user exists."""
    if db.query(User).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bootstrap already completed",
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
def login(payload: CredentialsIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
        )
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
```

`EmailStr` needs the `email-validator` package. Add `email-validator` to
`requirements.txt` and install it:

```bash
python -m pip install email-validator
```

- [ ] **Step 5: Register the router in `backend/app/main.py`**

Add the import at the top of `backend/app/main.py`:

```python
from app.routers import auth
```

and register it inside `create_app()`, immediately before `return application`:

```python
    application.include_router(auth.router)
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_auth.py -v
```

Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/deps.py backend/app/routers backend/app/main.py \
        backend/tests/conftest.py backend/tests/test_auth.py requirements.txt
git commit -m "feat: add JWT auth with bootstrap, login and current-user endpoints"
```

---

## Task 5: User administration API

**Files:**
- Create: `backend/app/routers/users.py`
- Modify: `backend/app/main.py` (register the users router)
- Test: `backend/tests/test_users.py`

**Interfaces:**
- Consumes: `app.deps.require_admin`, `app.deps.get_current_user`, `app.models.User`, `app.security.hash_password`, `app.routers.auth.UserOut`.
- Produces: `GET /api/users`, `POST /api/users`, `PATCH /api/users/{user_id}`, `DELETE /api/users/{user_id}`. All admin-only. `DELETE` deactivates rather than removing rows, so audit trails on suggestions survive.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_users.py`:

```python
def test_admin_can_create_a_user(client, admin_token, auth):
    response = client.post(
        "/api/users",
        headers=auth(admin_token),
        json={"email": "new@hateco.vn", "password": "another-pass-1", "role": "member"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new@hateco.vn"
    assert response.json()["role"] == "member"


def test_created_user_can_log_in(client, admin_token, auth):
    client.post(
        "/api/users",
        headers=auth(admin_token),
        json={"email": "new@hateco.vn", "password": "another-pass-1", "role": "member"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "new@hateco.vn", "password": "another-pass-1"},
    )

    assert response.status_code == 200


def test_duplicate_email_is_rejected(client, admin_token, auth):
    client.post(
        "/api/users",
        headers=auth(admin_token),
        json={"email": "new@hateco.vn", "password": "another-pass-1", "role": "member"},
    )

    response = client.post(
        "/api/users",
        headers=auth(admin_token),
        json={"email": "new@hateco.vn", "password": "another-pass-2", "role": "member"},
    )

    assert response.status_code == 409


def test_member_cannot_list_users(client, member_token, auth):
    response = client.get("/api/users", headers=auth(member_token))

    assert response.status_code == 403


def test_admin_can_deactivate_a_user(client, admin_token, auth, member_user):
    response = client.delete(f"/api/users/{member_user['id']}", headers=auth(admin_token))

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_deactivated_user_cannot_log_in(client, admin_token, auth, member_user):
    client.delete(f"/api/users/{member_user['id']}", headers=auth(admin_token))

    response = client.post(
        "/api/auth/login",
        json={"email": member_user["email"], "password": "member-password-123"},
    )

    assert response.status_code == 403


def test_admin_cannot_deactivate_themselves(client, admin_token, auth):
    me = client.get("/api/auth/me", headers=auth(admin_token)).json()

    response = client.delete(f"/api/users/{me['id']}", headers=auth(admin_token))

    assert response.status_code == 400
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_users.py -v
```

Expected: 7 failures — 404/405 because `/api/users` does not exist.

- [ ] **Step 3: Write `backend/app/routers/users.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models import User
from app.routers.auth import UserOut
from app.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])

VALID_GLOBAL_ROLES = {"admin", "member"}


class UserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = "member"


class UserUpdateIn(BaseModel):
    role: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None


def _validate_role(role: str) -> None:
    if role not in VALID_GLOBAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role must be one of {sorted(VALID_GLOBAL_ROLES)}",
        )


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    _validate_role(payload.role)
    exists = db.query(User).filter(User.email == payload.email).one_or_none()
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.role is not None:
        _validate_role(payload.role)
        user.role = payload.role
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=UserOut)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> User:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
```

- [ ] **Step 4: Register the router in `backend/app/main.py`**

Change the routers import line to:

```python
from app.routers import auth, users
```

and add inside `create_app()`, after the auth router line:

```python
    application.include_router(users.router)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_users.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Run the whole suite**

```bash
cd backend && python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/users.py backend/app/main.py backend/tests/test_users.py
git commit -m "feat: add admin-only user management API"
```

---

## Task 6: Pages API and per-page authorization

**Files:**
- Create: `backend/app/routers/pages.py`
- Modify: `backend/app/deps.py` (add `authorize_page`, `page_viewer`, `page_editor`, `page_owner`)
- Modify: `backend/app/main.py` (register the pages router)
- Modify: `backend/tests/conftest.py` (add the `page_id` fixture)
- Test: `backend/tests/test_pages.py`

**Interfaces:**
- Consumes: `app.models.Page`, `app.models.PageMembership`, `app.models.role_rank`, `app.security.encrypt_token`, `app.deps.get_current_user`.
- Produces:
  - `app.deps.authorize_page(db: Session, user: User, page_id: int, min_role: str) -> Page`
  - `app.deps.page_viewer`, `app.deps.page_editor`, `app.deps.page_owner` — FastAPI dependencies that read `page_id` from the path and return the `Page`
  - `PageOut`: `{id, fb_page_id, name, system_prompt, llm_model, is_active, has_access_token, my_role, knowledge_count, created_at}`
  - Endpoints: `GET /api/pages`, `POST /api/pages`, `GET /api/pages/{page_id}`, `PATCH /api/pages/{page_id}`, `DELETE /api/pages/{page_id}`
  - Test fixture `page_id: int` — a page created by the admin, Facebook Page ID `"100000000000001"`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_pages.py`:

```python
NEW_PAGE = {
    "fb_page_id": "222222222222222",
    "name": "Hateco Tuyen Sinh",
    "access_token": "EAAG-secret-token",
}


def test_admin_can_create_a_page(client, admin_token, auth):
    response = client.post("/api/pages", headers=auth(admin_token), json=NEW_PAGE)

    assert response.status_code == 201
    body = response.json()
    assert body["fb_page_id"] == "222222222222222"
    assert body["has_access_token"] is True


def test_page_response_never_leaks_the_access_token(client, admin_token, auth):
    response = client.post("/api/pages", headers=auth(admin_token), json=NEW_PAGE)

    assert "EAAG-secret-token" not in response.text
    assert "access_token" not in response.json()


def test_duplicate_facebook_page_id_is_rejected(client, admin_token, auth):
    client.post("/api/pages", headers=auth(admin_token), json=NEW_PAGE)

    response = client.post("/api/pages", headers=auth(admin_token), json=NEW_PAGE)

    assert response.status_code == 409


def test_admin_sees_every_page(client, admin_token, auth, page_id):
    response = client.get("/api/pages", headers=auth(admin_token))

    assert response.status_code == 200
    assert [p["id"] for p in response.json()] == [page_id]


def test_member_without_membership_sees_no_pages(client, member_token, auth, page_id):
    response = client.get("/api/pages", headers=auth(member_token))

    assert response.status_code == 200
    assert response.json() == []


def test_member_without_membership_cannot_open_a_page(
    client, member_token, auth, page_id
):
    response = client.get(f"/api/pages/{page_id}", headers=auth(member_token))

    assert response.status_code == 403


def test_member_with_viewer_membership_can_read_but_not_edit(
    client, admin_token, member_token, auth, page_id, member_user
):
    from app.db import SessionLocal
    from app.models import PageMembership

    session = SessionLocal()
    session.add(
        PageMembership(page_id=page_id, user_id=member_user["id"], role="viewer")
    )
    session.commit()
    session.close()

    read = client.get(f"/api/pages/{page_id}", headers=auth(member_token))
    write = client.patch(
        f"/api/pages/{page_id}", headers=auth(member_token), json={"name": "Renamed"}
    )

    assert read.status_code == 200
    assert read.json()["my_role"] == "viewer"
    assert write.status_code == 403


def test_owner_can_rename_a_page(client, admin_token, auth, page_id):
    response = client.patch(
        f"/api/pages/{page_id}", headers=auth(admin_token), json={"name": "Renamed"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_updating_the_access_token_keeps_it_hidden(client, admin_token, auth, page_id):
    response = client.patch(
        f"/api/pages/{page_id}",
        headers=auth(admin_token),
        json={"access_token": "EAAG-rotated-token"},
    )

    assert response.status_code == 200
    assert "EAAG-rotated-token" not in response.text
    assert response.json()["has_access_token"] is True


def test_admin_can_delete_a_page(client, admin_token, auth, page_id):
    response = client.delete(f"/api/pages/{page_id}", headers=auth(admin_token))

    assert response.status_code == 204
    assert client.get("/api/pages", headers=auth(admin_token)).json() == []
```

Append this fixture to `backend/tests/conftest.py`:

```python
@pytest.fixture
def page_id(client, admin_token, auth) -> int:
    response = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={
            "fb_page_id": "100000000000001",
            "name": "Hateco Test Page",
            "access_token": "EAAG-fixture-token",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_pages.py -v
```

Expected: 10 failures — 404/405 because `/api/pages` does not exist.

- [ ] **Step 3: Add page authorization to `backend/app/deps.py`**

Append to `backend/app/deps.py`:

```python
from collections.abc import Callable

from app.models import Page, PageMembership, role_rank


def authorize_page(db: Session, user: User, page_id: int, min_role: str) -> Page:
    """Return the page if the user holds at least `min_role` on it.

    A global admin is treated as `owner` on every page. Raises 404 when the page
    does not exist and 403 when the user's role is not high enough.
    """
    page = db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    if user.role == "admin":
        return page
    membership = (
        db.query(PageMembership)
        .filter(PageMembership.page_id == page_id, PageMembership.user_id == user.id)
        .one_or_none()
    )
    if membership is None or role_rank(membership.role) < role_rank(min_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires page role '{min_role}'",
        )
    return page


def effective_page_role(db: Session, user: User, page_id: int) -> str:
    """The role string to show in the UI: 'owner' for admins, else the membership role."""
    if user.role == "admin":
        return "owner"
    membership = (
        db.query(PageMembership)
        .filter(PageMembership.page_id == page_id, PageMembership.user_id == user.id)
        .one_or_none()
    )
    return membership.role if membership else "none"


def _page_dependency(min_role: str) -> Callable[..., Page]:
    def dependency(
        page_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> Page:
        return authorize_page(db, user, page_id, min_role)

    return dependency


page_viewer = _page_dependency("viewer")
page_editor = _page_dependency("editor")
page_owner = _page_dependency("owner")
```

- [ ] **Step 4: Write `backend/app/routers/pages.py`**

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import effective_page_role, get_current_user, page_owner, page_viewer
from app.models import KnowledgeItem, Page, PageMembership, User
from app.security import encrypt_token

router = APIRouter(prefix="/api/pages", tags=["pages"])


class PageCreateIn(BaseModel):
    fb_page_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    access_token: str = ""
    system_prompt: str = ""
    closing_message: str = ""
    llm_model: str = ""


class PageUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    access_token: str | None = None
    system_prompt: str | None = None
    closing_message: str | None = None
    llm_model: str | None = None
    is_active: bool | None = None


class PageOut(BaseModel):
    id: int
    fb_page_id: str
    name: str
    system_prompt: str
    closing_message: str
    llm_model: str
    is_active: bool
    has_access_token: bool
    my_role: str
    knowledge_count: int
    created_at: datetime


def to_page_out(db: Session, page: Page, user: User) -> PageOut:
    knowledge_count = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.page_id == page.id, KnowledgeItem.is_active.is_(True))
        .count()
    )
    return PageOut(
        id=page.id,
        fb_page_id=page.fb_page_id,
        name=page.name,
        system_prompt=page.system_prompt,
        closing_message=page.closing_message,
        llm_model=page.llm_model,
        is_active=page.is_active,
        has_access_token=bool(page.access_token_encrypted),
        my_role=effective_page_role(db, user, page.id),
        knowledge_count=knowledge_count,
        created_at=page.created_at,
    )


@router.get("", response_model=list[PageOut])
def list_pages(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[PageOut]:
    query = db.query(Page)
    if user.role != "admin":
        query = query.join(PageMembership, PageMembership.page_id == Page.id).filter(
            PageMembership.user_id == user.id
        )
    return [to_page_out(db, page, user) for page in query.order_by(Page.id).all()]


@router.post("", response_model=PageOut, status_code=status.HTTP_201_CREATED)
def create_page(
    payload: PageCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PageOut:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )
    exists = (
        db.query(Page).filter(Page.fb_page_id == payload.fb_page_id).one_or_none()
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A page with this Facebook Page ID already exists",
        )
    page = Page(
        fb_page_id=payload.fb_page_id,
        name=payload.name,
        access_token_encrypted=encrypt_token(payload.access_token),
        system_prompt=payload.system_prompt,
        llm_model=payload.llm_model,
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    db.add(PageMembership(page_id=page.id, user_id=user.id, role="owner"))
    db.commit()
    return to_page_out(db, page, user)


@router.get("/{page_id}", response_model=PageOut)
def get_page(
    page: Page = Depends(page_viewer),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PageOut:
    return to_page_out(db, page, user)


@router.patch("/{page_id}", response_model=PageOut)
def update_page(
    payload: PageUpdateIn,
    page: Page = Depends(page_owner),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PageOut:
    if payload.name is not None:
        page.name = payload.name
    if payload.access_token is not None:
        page.access_token_encrypted = encrypt_token(payload.access_token)
    if payload.system_prompt is not None:
        page.system_prompt = payload.system_prompt
    if payload.closing_message is not None:
        page.closing_message = payload.closing_message
    if payload.llm_model is not None:
        page.llm_model = payload.llm_model
    if payload.is_active is not None:
        page.is_active = payload.is_active
    db.commit()
    db.refresh(page)
    return to_page_out(db, page, user)


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(
    page: Page = Depends(page_owner), db: Session = Depends(get_db)
) -> Response:
    db.delete(page)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Register the router in `backend/app/main.py`**

Change the routers import line to:

```python
from app.routers import auth, pages, users
```

and add inside `create_app()`:

```python
    application.include_router(pages.router)
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_pages.py -v
```

Expected: 10 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/pages.py backend/app/deps.py backend/app/main.py \
        backend/tests/conftest.py backend/tests/test_pages.py
git commit -m "feat: add pages API with per-page role authorization"
```

---

## Task 7: Page membership API

**Files:**
- Create: `backend/app/routers/members.py`
- Modify: `backend/app/main.py` (register the members router)
- Test: `backend/tests/test_members.py`

**Interfaces:**
- Consumes: `app.deps.page_viewer`, `app.deps.page_owner`, `app.models.PageMembership`, `app.models.User`.
- Produces: `GET /api/pages/{page_id}/members`, `PUT /api/pages/{page_id}/members`, `DELETE /api/pages/{page_id}/members/{user_id}`. `MemberOut`: `{user_id: int, email: str, role: str}`. `PUT` is an upsert so the frontend has one call for "add member" and "change role".

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_members.py`:

```python
def test_owner_can_add_a_member(client, admin_token, auth, page_id, member_user):
    response = client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "editor"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "editor"
    assert response.json()["email"] == member_user["email"]


def test_adding_the_same_member_twice_updates_the_role(
    client, admin_token, auth, page_id, member_user
):
    client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "viewer"},
    )

    response = client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "owner"},
    )
    listing = client.get(f"/api/pages/{page_id}/members", headers=auth(admin_token))

    assert response.status_code == 200
    assert response.json()["role"] == "owner"
    assert len([m for m in listing.json() if m["user_id"] == member_user["id"]]) == 1


def test_invalid_role_is_rejected(client, admin_token, auth, page_id, member_user):
    response = client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "superuser"},
    )

    assert response.status_code == 422


def test_member_can_list_but_not_change_members(
    client, admin_token, member_token, auth, page_id, member_user
):
    client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "viewer"},
    )

    listing = client.get(f"/api/pages/{page_id}/members", headers=auth(member_token))
    attempt = client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(member_token),
        json={"user_id": member_user["id"], "role": "owner"},
    )

    assert listing.status_code == 200
    assert attempt.status_code == 403


def test_owner_can_remove_a_member(client, admin_token, auth, page_id, member_user):
    client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "editor"},
    )

    response = client.delete(
        f"/api/pages/{page_id}/members/{member_user['id']}", headers=auth(admin_token)
    )
    listing = client.get(f"/api/pages/{page_id}/members", headers=auth(admin_token))

    assert response.status_code == 204
    assert member_user["id"] not in [m["user_id"] for m in listing.json()]


def test_adding_an_unknown_user_returns_404(client, admin_token, auth, page_id):
    response = client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": 99999, "role": "editor"},
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_members.py -v
```

Expected: 6 failures — 404/405, the members routes do not exist.

- [ ] **Step 3: Write `backend/app/routers/members.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import page_owner, page_viewer
from app.models import ROLE_ORDER, Page, PageMembership, User

router = APIRouter(prefix="/api/pages/{page_id}/members", tags=["members"])


class MemberIn(BaseModel):
    user_id: int
    role: str


class MemberOut(BaseModel):
    user_id: int
    email: str
    role: str


@router.get("", response_model=list[MemberOut])
def list_members(
    page: Page = Depends(page_viewer), db: Session = Depends(get_db)
) -> list[MemberOut]:
    rows = (
        db.query(PageMembership, User)
        .join(User, User.id == PageMembership.user_id)
        .filter(PageMembership.page_id == page.id)
        .order_by(User.email)
        .all()
    )
    return [
        MemberOut(user_id=user.id, email=user.email, role=membership.role)
        for membership, user in rows
    ]


@router.put("", response_model=MemberOut)
def upsert_member(
    payload: MemberIn,
    page: Page = Depends(page_owner),
    db: Session = Depends(get_db),
) -> MemberOut:
    if payload.role not in ROLE_ORDER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role must be one of {sorted(ROLE_ORDER)}",
        )
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    membership = (
        db.query(PageMembership)
        .filter(
            PageMembership.page_id == page.id,
            PageMembership.user_id == payload.user_id,
        )
        .one_or_none()
    )
    if membership is None:
        membership = PageMembership(
            page_id=page.id, user_id=payload.user_id, role=payload.role
        )
        db.add(membership)
    else:
        membership.role = payload.role
    db.commit()
    return MemberOut(user_id=user.id, email=user.email, role=payload.role)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: int,
    page: Page = Depends(page_owner),
    db: Session = Depends(get_db),
) -> Response:
    membership = (
        db.query(PageMembership)
        .filter(PageMembership.page_id == page.id, PageMembership.user_id == user_id)
        .one_or_none()
    )
    if membership is not None:
        db.delete(membership)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 4: Register the router in `backend/app/main.py`**

Change the routers import line to:

```python
from app.routers import auth, members, pages, users
```

and add inside `create_app()`:

```python
    application.include_router(members.router)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_members.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/members.py backend/app/main.py backend/tests/test_members.py
git commit -m "feat: add per-page membership management API"
```

---

## Task 8: Per-page vector store

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/vector_store.py`
- Test: `backend/tests/test_vector_store.py`

**Interfaces:**
- Consumes: `app.config.settings` (`embedding_model`, `index_dir`), `app.models.KnowledgeItem`.
- Produces:
  - `get_embeddings() -> Embeddings` — cached factory; tests monkeypatch this
  - `build_index(db: Session, page_id: int) -> FAISS` — rebuilds from active knowledge rows, saves to disk, refreshes the cache
  - `get_index(db: Session, page_id: int) -> FAISS` — memory cache → disk → build
  - `search(db: Session, page_id: int, query: str, k: int = 3) -> list[str]`
  - `invalidate(page_id: int) -> None`
  - `EMPTY_PLACEHOLDER: str`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_vector_store.py`:

```python
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.db import SessionLocal
from app.models import KnowledgeItem, Page
from app.services import vector_store


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    """No model download, no network: deterministic vectors."""
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


def make_page(db, fb_page_id="900000000000001") -> Page:
    page = Page(fb_page_id=fb_page_id, name="Vector Page", access_token_encrypted="x")
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def test_empty_page_still_builds_a_searchable_index(db):
    page = make_page(db)

    results = vector_store.search(db, page.id, "bất kỳ câu hỏi nào")

    assert results == [vector_store.EMPTY_PLACEHOLDER]


def test_search_returns_active_knowledge_text(db):
    page = make_page(db)
    db.add(
        KnowledgeItem(
            page_id=page.id, title="Học phí", content="Học phí là 15 triệu mỗi kỳ."
        )
    )
    db.commit()
    vector_store.build_index(db, page.id)

    results = vector_store.search(db, page.id, "học phí bao nhiêu", k=1)

    assert "Học phí là 15 triệu mỗi kỳ." in results[0]


def test_inactive_knowledge_is_not_indexed(db):
    page = make_page(db)
    db.add(
        KnowledgeItem(
            page_id=page.id,
            title="Bí mật",
            content="Nội dung đã tắt.",
            is_active=False,
        )
    )
    db.commit()
    vector_store.build_index(db, page.id)

    results = vector_store.search(db, page.id, "bí mật")

    assert results == [vector_store.EMPTY_PLACEHOLDER]


def test_each_page_has_its_own_index(db):
    page_a = make_page(db, "900000000000002")
    page_b = make_page(db, "900000000000003")
    db.add(KnowledgeItem(page_id=page_a.id, title="A", content="Chỉ trang A biết."))
    db.add(KnowledgeItem(page_id=page_b.id, title="B", content="Chỉ trang B biết."))
    db.commit()
    vector_store.build_index(db, page_a.id)
    vector_store.build_index(db, page_b.id)

    results_b = vector_store.search(db, page_b.id, "trang nào biết", k=5)

    assert all("trang A" not in chunk for chunk in results_b)


def test_rebuilding_picks_up_new_knowledge(db):
    page = make_page(db)
    vector_store.build_index(db, page.id)
    db.add(KnowledgeItem(page_id=page.id, title="Mới", content="Thông tin vừa thêm."))
    db.commit()

    vector_store.build_index(db, page.id)
    results = vector_store.search(db, page.id, "thông tin", k=1)

    assert "Thông tin vừa thêm." in results[0]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_vector_store.py -v
```

Expected: collection error — `ImportError: cannot import name 'vector_store' from 'app.services'`.

- [ ] **Step 3: Write `backend/app/services/vector_store.py`**

Create `backend/app/services/__init__.py` as an empty file, then:

```python
import shutil
import threading

from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeItem

EMPTY_PLACEHOLDER = "Chưa có thông tin nào được cấu hình cho trang này."

_lock = threading.Lock()
_embeddings: Embeddings | None = None
_cache: dict[int, FAISS] = {}


def get_embeddings() -> Embeddings:
    """Lazily build the sentence-transformers embedder. Tests monkeypatch this."""
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        _embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
    return _embeddings


def _index_path(page_id: int) -> str:
    return str(settings.index_dir / f"page_{page_id}")


def _knowledge_texts(db: Session, page_id: int) -> list[str]:
    items = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.page_id == page_id, KnowledgeItem.is_active.is_(True))
        .order_by(KnowledgeItem.id)
        .all()
    )
    texts = [f"{item.title}\n{item.content}".strip() for item in items if item.content.strip()]
    return texts or [EMPTY_PLACEHOLDER]


def build_index(db: Session, page_id: int) -> FAISS:
    """Rebuild a page's index from the database and persist it to disk."""
    store = FAISS.from_texts(_knowledge_texts(db, page_id), get_embeddings())
    store.save_local(_index_path(page_id))
    with _lock:
        _cache[page_id] = store
    return store


def get_index(db: Session, page_id: int) -> FAISS:
    with _lock:
        cached = _cache.get(page_id)
    if cached is not None:
        return cached

    path = settings.index_dir / f"page_{page_id}"
    if path.exists():
        store = FAISS.load_local(
            str(path), get_embeddings(), allow_dangerous_deserialization=True
        )
        with _lock:
            _cache[page_id] = store
        return store

    return build_index(db, page_id)


def search(db: Session, page_id: int, query: str, k: int = 3) -> list[str]:
    store = get_index(db, page_id)
    return [doc.page_content for doc in store.similarity_search(query, k=k)]


def invalidate(page_id: int) -> None:
    """Drop the in-memory index and the on-disk copy so the next read rebuilds."""
    with _lock:
        _cache.pop(page_id, None)
    path = settings.index_dir / f"page_{page_id}"
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def clear_cache() -> None:
    """Test helper: forget every cached index without touching disk."""
    with _lock:
        _cache.clear()
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_vector_store.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests/test_vector_store.py
git commit -m "feat: add per-page FAISS vector store built from knowledge rows"
```

---

## Task 9: Knowledge API

**Files:**
- Create: `backend/app/routers/knowledge.py`
- Modify: `backend/app/main.py` (register the knowledge router)
- Test: `backend/tests/test_knowledge.py`

**Interfaces:**
- Consumes: `app.deps.page_viewer`, `app.deps.page_editor`, `app.models.KnowledgeItem`, `app.services.vector_store.build_index`.
- Produces:
  - `KnowledgeOut`: `{id, page_id, title, content, source, is_active, created_at, updated_at}`
  - `GET /api/pages/{page_id}/knowledge`, `POST /api/pages/{page_id}/knowledge`, `PATCH /api/pages/{page_id}/knowledge/{item_id}`, `DELETE /api/pages/{page_id}/knowledge/{item_id}`
  - `app.routers.knowledge.VALID_SOURCES: set[str]` = `{"manual", "learned", "imported"}`
  - Every mutation calls `vector_store.build_index(db, page.id)` before returning.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_knowledge.py`:

```python
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.services import vector_store


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    embeddings = DeterministicFakeEmbedding(size=32)
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: embeddings)
    vector_store.clear_cache()
    yield
    vector_store.clear_cache()


def test_editor_can_create_a_knowledge_item(client, admin_token, auth, page_id):
    response = client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(admin_token),
        json={"title": "Học phí", "content": "15 triệu mỗi kỳ."},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Học phí"
    assert body["source"] == "manual"
    assert body["is_active"] is True


def test_creating_knowledge_makes_it_searchable(client, admin_token, auth, page_id):
    client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(admin_token),
        json={"title": "Học phí", "content": "15 triệu mỗi kỳ."},
    )

    from app.db import SessionLocal

    session = SessionLocal()
    try:
        results = vector_store.search(session, page_id, "học phí", k=1)
    finally:
        session.close()

    assert "15 triệu mỗi kỳ." in results[0]


def test_listing_knowledge_returns_items_for_that_page_only(
    client, admin_token, auth, page_id
):
    client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(admin_token),
        json={"title": "A", "content": "Nội dung A"},
    )
    other = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "555555555555555", "name": "Other", "access_token": "t"},
    ).json()["id"]
    client.post(
        f"/api/pages/{other}/knowledge",
        headers=auth(admin_token),
        json={"title": "B", "content": "Nội dung B"},
    )

    response = client.get(f"/api/pages/{page_id}/knowledge", headers=auth(admin_token))

    assert [item["title"] for item in response.json()] == ["A"]


def test_updating_a_knowledge_item_changes_its_content(
    client, admin_token, auth, page_id
):
    item_id = client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(admin_token),
        json={"title": "Học phí", "content": "15 triệu."},
    ).json()["id"]

    response = client.patch(
        f"/api/pages/{page_id}/knowledge/{item_id}",
        headers=auth(admin_token),
        json={"content": "20 triệu."},
    )

    assert response.status_code == 200
    assert response.json()["content"] == "20 triệu."


def test_deleting_a_knowledge_item_removes_it(client, admin_token, auth, page_id):
    item_id = client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(admin_token),
        json={"title": "Tạm", "content": "Xoá tôi đi."},
    ).json()["id"]

    response = client.delete(
        f"/api/pages/{page_id}/knowledge/{item_id}", headers=auth(admin_token)
    )
    listing = client.get(f"/api/pages/{page_id}/knowledge", headers=auth(admin_token))

    assert response.status_code == 204
    assert listing.json() == []


def test_viewer_cannot_create_knowledge(
    client, admin_token, member_token, auth, page_id, member_user
):
    client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "viewer"},
    )

    response = client.post(
        f"/api/pages/{page_id}/knowledge",
        headers=auth(member_token),
        json={"title": "Nope", "content": "Không được."},
    )

    assert response.status_code == 403


def test_knowledge_item_from_another_page_returns_404(client, admin_token, auth, page_id):
    other = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "666666666666666", "name": "Other", "access_token": "t"},
    ).json()["id"]
    foreign_item = client.post(
        f"/api/pages/{other}/knowledge",
        headers=auth(admin_token),
        json={"title": "B", "content": "Nội dung B"},
    ).json()["id"]

    response = client.patch(
        f"/api/pages/{page_id}/knowledge/{foreign_item}",
        headers=auth(admin_token),
        json={"content": "hijack"},
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_knowledge.py -v
```

Expected: 7 failures — 404/405, the knowledge routes do not exist.

- [ ] **Step 3: Write `backend/app/routers/knowledge.py`**

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import page_editor, page_viewer
from app.models import KnowledgeItem, Page
from app.services import vector_store

router = APIRouter(prefix="/api/pages/{page_id}/knowledge", tags=["knowledge"])

VALID_SOURCES = {"manual", "learned", "imported"}


class KnowledgeCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    source: str = "manual"
    is_active: bool = True


class KnowledgeUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class KnowledgeOut(BaseModel):
    id: int
    page_id: int
    title: str
    content: str
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def _get_item(db: Session, page: Page, item_id: int) -> KnowledgeItem:
    item = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.id == item_id, KnowledgeItem.page_id == page.id)
        .one_or_none()
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge item not found"
        )
    return item


@router.get("", response_model=list[KnowledgeOut])
def list_knowledge(
    page: Page = Depends(page_viewer), db: Session = Depends(get_db)
) -> list[KnowledgeItem]:
    return (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.page_id == page.id)
        .order_by(KnowledgeItem.id)
        .all()
    )


@router.post("", response_model=KnowledgeOut, status_code=status.HTTP_201_CREATED)
def create_knowledge(
    payload: KnowledgeCreateIn,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
) -> KnowledgeItem:
    if payload.source not in VALID_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"source must be one of {sorted(VALID_SOURCES)}",
        )
    item = KnowledgeItem(
        page_id=page.id,
        title=payload.title,
        content=payload.content,
        source=payload.source,
        is_active=payload.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    vector_store.build_index(db, page.id)
    return item


@router.patch("/{item_id}", response_model=KnowledgeOut)
def update_knowledge(
    item_id: int,
    payload: KnowledgeUpdateIn,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
) -> KnowledgeItem:
    item = _get_item(db, page, item_id)
    if payload.title is not None:
        item.title = payload.title
    if payload.content is not None:
        item.content = payload.content
    if payload.is_active is not None:
        item.is_active = payload.is_active
    db.commit()
    db.refresh(item)
    vector_store.build_index(db, page.id)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge(
    item_id: int,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
) -> Response:
    item = _get_item(db, page, item_id)
    db.delete(item)
    db.commit()
    vector_store.build_index(db, page.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 4: Register the router in `backend/app/main.py`**

Change the routers import line to:

```python
from app.routers import auth, knowledge, members, pages, users
```

and add inside `create_app()`:

```python
    application.include_router(knowledge.router)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_knowledge.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/knowledge.py backend/app/main.py backend/tests/test_knowledge.py
git commit -m "feat: add per-page knowledge API that reindexes on every change"
```

---

## Task 10: Chatbot answer service

**Files:**
- Create: `backend/app/services/chatbot.py`
- Test: `backend/tests/test_chatbot_service.py`

**Interfaces:**
- Consumes: `app.config.settings` (`llm_model`, `openrouter_api_key`, `openrouter_base_url`), `app.models.Page`, `app.services.vector_store.search`.
- Produces:
  - `DEFAULT_SYSTEM_PROMPT: str` — a Vietnamese Q&A-and-hand-off persona: answers from the page's knowledge, never solicits personal information or paperwork
  - `ANSWER_TEMPLATE: str`
  - `build_llm(model: str = "", temperature: float = 0.7) -> ChatOpenAI` — tests monkeypatch this
  - `build_prompt(page: Page, context_chunks: list[str], question: str) -> str`
  - `generate_answer(db: Session, page: Page, question: str) -> tuple[str, list[str]]` returning `(answer_text, context_chunks)`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_chatbot_service.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_chatbot_service.py -v
```

Expected: collection error — `ImportError: cannot import name 'chatbot' from 'app.services'`.

- [ ] **Step 3: Write `backend/app/services/chatbot.py`**

```python
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Page
from app.services import vector_store

DEFAULT_SYSTEM_PROMPT = """Bạn là nhân viên tư vấn tuyển sinh thân thiện, nhiệt tình của trường.
Nhiệm vụ của bạn là trả lời câu hỏi của học sinh và phụ huynh về tuyển sinh, đặc biệt là
ngoài giờ hành chính khi tư vấn viên chưa thể trả lời ngay.

YÊU CẦU QUAN TRỌNG VỀ CÁCH TRẢ LỜI:
- Trả lời ngắn gọn, thân thiện, xưng hô "cô" và "em" hoặc "trường" và "bạn".
- TUYỆT ĐỐI KHÔNG viết một đoạn văn dài dòng.
- BẮT BUỘC ngắt đoạn văn thành các câu ngắn (mỗi đoạn 1-2 câu). Dùng dấu xuống dòng giữa các ý.
- CHỈ trả lời dựa trên thông tin tham khảo được cung cấp, không bịa thêm.
- TUYỆT ĐỐI KHÔNG hỏi hoặc thu thập thông tin cá nhân của học sinh (CCCD, học bạ, số điện
  thoại, ngành, địa chỉ...). Nếu học sinh cần tư vấn sâu hơn hoặc muốn đăng ký, hãy khuyến
  khích các em gọi điện trực tiếp cho trường để được hỗ trợ."""

ANSWER_TEMPLATE = """{system_prompt}

THÔNG TIN THAM KHẢO CỦA TRANG (chỉ dùng thông tin này, không bịa thêm):
{context}

Câu hỏi của khách: {question}
Trả lời:"""


def build_llm(model: str = "", temperature: float = 0.7) -> ChatOpenAI:
    """Build an OpenRouter-backed chat model. Tests monkeypatch this function."""
    return ChatOpenAI(
        model=model or settings.llm_model,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=settings.openrouter_base_url,
        temperature=temperature,
        max_tokens=1000,
    )


def build_prompt(page: Page, context_chunks: list[str], question: str) -> str:
    system_prompt = (page.system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT
    return ANSWER_TEMPLATE.format(
        system_prompt=system_prompt,
        context="\n---\n".join(context_chunks),
        question=question,
    )


def generate_answer(db: Session, page: Page, question: str) -> tuple[str, list[str]]:
    """Answer one question for one page. Returns (answer, retrieved context chunks)."""
    context_chunks = vector_store.search(db, page.id, question, k=3)
    prompt = build_prompt(page, context_chunks, question)
    llm = build_llm(page.llm_model or "")
    response = llm.invoke(prompt)
    return str(response.content), context_chunks
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_chatbot_service.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/chatbot.py backend/tests/test_chatbot_service.py
git commit -m "feat: add per-page RAG answer service with overridable system prompt"
```

---

## Task 11: Conversation logging and Messenger client

**Files:**
- Create: `backend/app/services/messenger.py`
- Create: `backend/app/services/conversations.py`
- Test: `backend/tests/test_conversation_service.py`
- Test: `backend/tests/test_messenger.py`

**Interfaces:**
- Consumes: `app.models.Conversation`, `app.models.Message`, `app.models.utcnow`.
- Produces:
  - `app.services.messenger.GRAPH_URL: str`
  - `app.services.messenger.send_typing(access_token: str, psid: str) -> bool`
  - `app.services.messenger.send_text(access_token: str, psid: str, text: str) -> bool`
  - `app.services.conversations.get_or_create_conversation(db: Session, page_id: int, psid: str) -> Conversation`
  - `app.services.conversations.log_message(db: Session, page_id: int, psid: str, direction: str, text: str, attachments: list | None = None) -> Message`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_conversation_service.py`:

```python
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
```

Create `backend/tests/test_messenger.py`:

```python
import requests

from app.services import messenger


class FakeResponse:
    status_code = 200


def test_send_text_posts_the_message_payload(monkeypatch):
    calls = []

    def fake_post(url, params=None, json=None, timeout=None):
        calls.append({"url": url, "params": params, "json": json})
        return FakeResponse()

    monkeypatch.setattr(messenger.requests, "post", fake_post)

    result = messenger.send_text("token-abc", "psid-1", "Chào em")

    assert result is True
    assert calls[0]["url"] == messenger.GRAPH_URL
    assert calls[0]["params"] == {"access_token": "token-abc"}
    assert calls[0]["json"] == {
        "recipient": {"id": "psid-1"},
        "message": {"text": "Chào em"},
    }


def test_send_typing_posts_the_sender_action(monkeypatch):
    calls = []

    def fake_post(url, params=None, json=None, timeout=None):
        calls.append(json)
        return FakeResponse()

    monkeypatch.setattr(messenger.requests, "post", fake_post)

    messenger.send_typing("token-abc", "psid-1")

    assert calls[0] == {"recipient": {"id": "psid-1"}, "sender_action": "typing_on"}


def test_network_failure_returns_false_instead_of_raising(monkeypatch):
    def fake_post(url, params=None, json=None, timeout=None):
        raise requests.RequestException("boom")

    monkeypatch.setattr(messenger.requests, "post", fake_post)

    assert messenger.send_text("token-abc", "psid-1", "Chào em") is False


def test_missing_access_token_short_circuits(monkeypatch):
    def fake_post(url, params=None, json=None, timeout=None):
        raise AssertionError("must not call the Graph API without a token")

    monkeypatch.setattr(messenger.requests, "post", fake_post)

    assert messenger.send_text("", "psid-1", "Chào em") is False
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_conversation_service.py tests/test_messenger.py -v
```

Expected: two collection errors — `cannot import name 'conversations'` and
`cannot import name 'messenger'` from `app.services`.

- [ ] **Step 3: Write `backend/app/services/messenger.py`**

```python
import requests

GRAPH_URL = "https://graph.facebook.com/v19.0/me/messages"
REQUEST_TIMEOUT_SECONDS = 10


def _post(access_token: str, payload: dict) -> bool:
    """POST to the Send API. Returns True on success, never raises."""
    if not access_token:
        print("Messenger API skipped: page has no access token")
        return False
    try:
        response = requests.post(
            GRAPH_URL,
            params={"access_token": access_token},
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        print(f"Messenger API error: {exc}")
        return False
    if response.status_code >= 400:
        print(f"Messenger API returned {response.status_code}")
        return False
    return True


def send_typing(access_token: str, psid: str) -> bool:
    return _post(access_token, {"recipient": {"id": psid}, "sender_action": "typing_on"})


def send_text(access_token: str, psid: str, text: str) -> bool:
    return _post(
        access_token, {"recipient": {"id": psid}, "message": {"text": text}}
    )
```

- [ ] **Step 4: Write `backend/app/services/conversations.py`**

```python
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
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_conversation_service.py tests/test_messenger.py -v
```

Expected: 10 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/messenger.py backend/app/services/conversations.py \
        backend/tests/test_conversation_service.py backend/tests/test_messenger.py
git commit -m "feat: add conversation logging and Messenger send helpers"
```

---

## Task 12: Page closing message

The bot never collects personal information (see spec §6, Out of scope). Instead, each
page can carry a short, operator-written **closing message** — typically a hotline number
or a line like "gọi cho trường để được tư vấn thêm" — that is appended verbatim after
every generated answer, so the hand-off to a human is consistent no matter what the LLM
says.

**Files:**
- Modify: `backend/app/services/chatbot.py` (append `page.closing_message` in `generate_answer`)
- Modify: `backend/tests/test_chatbot_service.py` (add closing-message tests)

**Interfaces:**
- Consumes: `app.models.Page.closing_message` (added in Task 2), `app.services.chatbot.generate_answer` (Task 10).
- Produces: `generate_answer` now returns an answer with the page's closing message appended after a blank line when `closing_message` is non-empty; unchanged (just the LLM's answer) when it is empty or whitespace-only. The `(answer, context_chunks)` return shape from Task 10 is unchanged.

- [ ] **Step 1: Write the failing test**

Append these tests to `backend/tests/test_chatbot_service.py` (same file Task 10 created —
reuse its `db`, `stub_llm`, `fake_context` fixtures and `make_page` helper):

```python
def test_closing_message_is_appended_after_the_answer(db, stub_llm):
    page = make_page(db, closing_message="Gọi hotline 0123 456 789 để được tư vấn thêm nhé!")

    answer, _context = chatbot.generate_answer(db, page, "Học phí bao nhiêu?")

    assert answer == (
        "Chào em, trường trả lời như sau.\n\n"
        "Gọi hotline 0123 456 789 để được tư vấn thêm nhé!"
    )


def test_blank_closing_message_appends_nothing(db, stub_llm):
    page = make_page(db, closing_message="   ")

    answer, _context = chatbot.generate_answer(db, page, "Học phí bao nhiêu?")

    assert answer == "Chào em, trường trả lời như sau."


def test_empty_closing_message_appends_nothing(db, stub_llm):
    page = make_page(db)

    answer, _context = chatbot.generate_answer(db, page, "Học phí bao nhiêu?")

    assert answer == "Chào em, trường trả lời như sau."
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_chatbot_service.py -v
```

Expected: `test_closing_message_is_appended_after_the_answer` FAILS — the answer has no
closing message appended yet (the other two new tests already pass, since `generate_answer`
currently returns the bare LLM answer either way).

- [ ] **Step 3: Modify `backend/app/services/chatbot.py`**

Replace the `generate_answer` function with a version that appends the closing message:

```python
def generate_answer(db: Session, page: Page, question: str) -> tuple[str, list[str]]:
    """Answer one question for one page. Returns (answer, retrieved context chunks)."""
    context_chunks = vector_store.search(db, page.id, question, k=3)
    prompt = build_prompt(page, context_chunks, question)
    llm = build_llm(page.llm_model or "")
    response = llm.invoke(prompt)
    answer = str(response.content)

    closing_message = (page.closing_message or "").strip()
    if closing_message:
        answer = f"{answer}\n\n{closing_message}"

    return answer, context_chunks
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_chatbot_service.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/chatbot.py backend/tests/test_chatbot_service.py
git commit -m "feat: append the page's closing message after every generated answer"
```

---

## Task 13: Multi-page webhook

**Files:**
- Create: `backend/app/routers/webhook.py`
- Modify: `backend/app/main.py` (register the webhook router)
- Test: `backend/tests/test_webhook.py`

**Interfaces:**
- Consumes: `app.config.settings.verify_token`, `app.db.SessionLocal`, `app.models.Page`, `app.security.decrypt_token`, `app.services.chatbot.generate_answer`, `app.services.conversations.log_message`, `app.services.messenger.send_text`, `app.services.messenger.send_typing`.
- Produces:
  - `GET /webhook` — Facebook challenge verification
  - `POST /webhook` — routes each `entry` to its `Page` by `fb_page_id`
  - `app.routers.webhook.handle_event(fb_page_id: str, event: dict) -> None` — the background worker; opens its own `SessionLocal`
  - `app.routers.webhook.typing_delay_seconds(text: str) -> float` — `min(3.0, len(text) / 50)`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_webhook.py`:

```python
import pytest

from app.db import SessionLocal
from app.models import Conversation, Message
from app.routers import webhook
from app.services import chatbot, messenger


def build_payload(fb_page_id: str, psid: str, text: str) -> dict:
    return {
        "object": "page",
        "entry": [
            {
                "id": fb_page_id,
                "messaging": [
                    {"sender": {"id": psid}, "message": {"text": text}},
                ],
            }
        ],
    }


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Capture outbound Messenger calls and stub the LLM."""
    outbox: list[dict] = []

    monkeypatch.setattr(
        messenger,
        "send_text",
        lambda token, psid, text: outbox.append(
            {"token": token, "psid": psid, "text": text}
        )
        or True,
    )
    monkeypatch.setattr(messenger, "send_typing", lambda token, psid: True)
    monkeypatch.setattr(
        chatbot, "generate_answer", lambda db, page, question: ("Chào em!", ["ctx"])
    )
    monkeypatch.setattr(webhook, "typing_delay_seconds", lambda text: 0.0)
    return outbox


def test_verification_echoes_the_challenge(client):
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": "1158201444",
        },
    )

    assert response.status_code == 200
    assert response.text == "1158201444"


def test_verification_rejects_a_wrong_token(client):
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "1158201444",
        },
    )

    assert response.status_code == 403


def test_message_is_logged_and_answered(client, admin_token, auth, sent):
    client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={
            "fb_page_id": "300000000000001",
            "name": "Webhook Page",
            "access_token": "EAAG-webhook-token",
        },
    )

    response = client.post(
        "/webhook", json=build_payload("300000000000001", "psid-9", "Học phí bao nhiêu?")
    )

    session = SessionLocal()
    try:
        directions = [m.direction for m in session.query(Message).order_by(Message.id)]
    finally:
        session.close()

    assert response.status_code == 200
    assert directions == ["in", "out"]
    assert sent[0]["text"] == "Chào em!"
    assert sent[0]["token"] == "EAAG-webhook-token"


def test_events_route_to_the_matching_page(client, admin_token, auth, sent):
    first = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "300000000000001", "name": "One", "access_token": "tok-1"},
    ).json()["id"]
    client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "300000000000002", "name": "Two", "access_token": "tok-2"},
    )

    client.post("/webhook", json=build_payload("300000000000001", "psid-9", "Chào"))

    session = SessionLocal()
    try:
        conversation = session.query(Conversation).one()
    finally:
        session.close()

    assert conversation.page_id == first
    assert sent[0]["token"] == "tok-1"


def test_unknown_page_is_ignored(client, sent):
    response = client.post(
        "/webhook", json=build_payload("999999999999999", "psid-9", "Chào")
    )

    session = SessionLocal()
    try:
        message_count = session.query(Message).count()
    finally:
        session.close()

    assert response.status_code == 200
    assert message_count == 0
    assert sent == []


def test_inactive_page_logs_but_does_not_reply(client, admin_token, auth, sent):
    page_id = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "300000000000003", "name": "Off", "access_token": "tok-3"},
    ).json()["id"]
    client.patch(
        f"/api/pages/{page_id}", headers=auth(admin_token), json={"is_active": False}
    )

    client.post("/webhook", json=build_payload("300000000000003", "psid-9", "Chào"))

    session = SessionLocal()
    try:
        directions = [m.direction for m in session.query(Message).all()]
    finally:
        session.close()

    assert directions == ["in"]
    assert sent == []


def test_echo_messages_are_ignored(client, admin_token, auth, sent):
    client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "300000000000004", "name": "Echo", "access_token": "tok-4"},
    )
    payload = build_payload("300000000000004", "psid-9", "Chào")
    payload["entry"][0]["messaging"][0]["message"]["is_echo"] = True

    client.post("/webhook", json=payload)

    session = SessionLocal()
    try:
        message_count = session.query(Message).count()
    finally:
        session.close()

    assert message_count == 0


def test_typing_delay_is_capped_at_three_seconds():
    assert webhook.typing_delay_seconds("x" * 50) == 1.0
    assert webhook.typing_delay_seconds("x" * 10_000) == 3.0
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_webhook.py -v
```

Expected: collection error — `cannot import name 'webhook' from 'app.routers'`.

- [ ] **Step 3: Write `backend/app/routers/webhook.py`**

```python
import asyncio

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


async def handle_event(fb_page_id: str, event: dict) -> None:
    """Process one inbound Messenger event. Runs as a FastAPI background task."""
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

        await asyncio.sleep(typing_delay_seconds(answer))
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
```

Note: `handle_event` is referenced through the module (`webhook.typing_delay_seconds`)
so the monkeypatch in the tests takes effect — do not import these names directly into
another module's namespace.

- [ ] **Step 4: Register the router in `backend/app/main.py`**

Change the routers import line to:

```python
from app.routers import auth, knowledge, members, pages, users, webhook
```

and add inside `create_app()`:

```python
    application.include_router(webhook.router)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_webhook.py -v
```

Expected: 8 passed.

- [ ] **Step 6: Run the whole suite**

```bash
cd backend && python -m pytest -v
```

Expected: everything passes.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/webhook.py backend/app/main.py backend/tests/test_webhook.py
git commit -m "feat: route Facebook webhook events to the matching page"
```

---

## Task 14: Conversations read API

**Files:**
- Create: `backend/app/routers/conversations.py`
- Modify: `backend/app/main.py` (register the conversations router)
- Test: `backend/tests/test_conversations_api.py`

**Interfaces:**
- Consumes: `app.deps.page_viewer`, `app.models.Conversation`, `app.models.Message`.
- Produces:
  - `ConversationOut`: `{id, psid, started_at, last_message_at, message_count, last_message_preview}`
  - `MessageOut`: `{id, direction, text, attachments, created_at}` (`attachments` is the parsed JSON list)
  - `ConversationDetailOut`: `{id, psid, started_at, last_message_at, messages: list[MessageOut]}`
  - `GET /api/pages/{page_id}/conversations?q=&limit=&offset=`
  - `GET /api/pages/{page_id}/conversations/{conversation_id}`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_conversations_api.py`:

```python
import pytest

from app.db import SessionLocal
from app.services import conversations as conversation_service


@pytest.fixture
def seeded(page_id) -> int:
    session = SessionLocal()
    try:
        conversation_service.log_message(session, page_id, "psid-a", "in", "Học phí bao nhiêu?")
        conversation_service.log_message(session, page_id, "psid-a", "out", "15 triệu em nhé")
        conversation_service.log_message(session, page_id, "psid-b", "in", "Trường ở đâu ạ?")
    finally:
        session.close()
    return page_id


def test_listing_conversations_returns_both_threads(client, admin_token, auth, seeded):
    response = client.get(
        f"/api/pages/{seeded}/conversations", headers=auth(admin_token)
    )

    assert response.status_code == 200
    assert {c["psid"] for c in response.json()} == {"psid-a", "psid-b"}


def test_conversation_summary_includes_counts_and_preview(
    client, admin_token, auth, seeded
):
    rows = client.get(
        f"/api/pages/{seeded}/conversations", headers=auth(admin_token)
    ).json()
    thread_a = next(c for c in rows if c["psid"] == "psid-a")

    assert thread_a["message_count"] == 2
    assert thread_a["last_message_preview"] == "15 triệu em nhé"


def test_search_filters_by_message_text(client, admin_token, auth, seeded):
    response = client.get(
        f"/api/pages/{seeded}/conversations",
        headers=auth(admin_token),
        params={"q": "Trường ở đâu"},
    )

    assert [c["psid"] for c in response.json()] == ["psid-b"]


def test_search_also_matches_the_psid(client, admin_token, auth, seeded):
    response = client.get(
        f"/api/pages/{seeded}/conversations",
        headers=auth(admin_token),
        params={"q": "psid-a"},
    )

    assert [c["psid"] for c in response.json()] == ["psid-a"]


def test_transcript_returns_messages_in_order(client, admin_token, auth, seeded):
    listing = client.get(
        f"/api/pages/{seeded}/conversations", headers=auth(admin_token)
    ).json()
    thread_a = next(c for c in listing if c["psid"] == "psid-a")

    response = client.get(
        f"/api/pages/{seeded}/conversations/{thread_a['id']}", headers=auth(admin_token)
    )

    assert response.status_code == 200
    assert [m["text"] for m in response.json()["messages"]] == [
        "Học phí bao nhiêu?",
        "15 triệu em nhé",
    ]


def test_transcript_from_another_page_returns_404(client, admin_token, auth, seeded):
    other = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "444444444444444", "name": "Other", "access_token": "t"},
    ).json()["id"]
    listing = client.get(
        f"/api/pages/{seeded}/conversations", headers=auth(admin_token)
    ).json()

    response = client.get(
        f"/api/pages/{other}/conversations/{listing[0]['id']}", headers=auth(admin_token)
    )

    assert response.status_code == 404


def test_outsider_cannot_read_conversations(client, member_token, auth, seeded):
    response = client.get(
        f"/api/pages/{seeded}/conversations", headers=auth(member_token)
    )

    assert response.status_code == 403
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_conversations_api.py -v
```

Expected: 7 failures — 404, the conversation routes do not exist.

- [ ] **Step 3: Write `backend/app/routers/conversations.py`**

```python
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
```

- [ ] **Step 4: Register the router in `backend/app/main.py`**

Change the routers import line to:

```python
from app.routers import (
    auth,
    conversations,
    knowledge,
    members,
    pages,
    users,
    webhook,
)
```

and add inside `create_app()`:

```python
    application.include_router(conversations.router)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_conversations_api.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/conversations.py backend/app/main.py \
        backend/tests/test_conversations_api.py
git commit -m "feat: expose conversation transcripts and search over the API"
```

---

## Task 15: Learning service — mine, dedupe, approve

**Files:**
- Create: `backend/app/services/learning.py`
- Test: `backend/tests/test_learning_service.py`

**Interfaces:**
- Consumes: `app.models.Conversation`, `app.models.KnowledgeItem`, `app.models.Message`, `app.models.Suggestion`, `app.models.User`, `app.models.utcnow`, `app.services.chatbot.build_llm`, `app.services.vector_store.build_index`.
- Produces:
  - `SuggestedEntry(BaseModel)`: `question: str`, `answer: str`, `occurrences: int`
  - `SuggestionBatch(BaseModel)`: `entries: list[SuggestedEntry]`
  - `MIN_QUESTION_LENGTH = 5`, `MAX_QUESTION_LENGTH = 300`, `MINING_PROMPT: str`
  - `build_miner(model: str = "")` — structured-output runnable returning `SuggestionBatch`; tests monkeypatch this
  - `normalize(text: str) -> str` — lowercased, whitespace-collapsed, used for dedupe
  - `collect_questions(db: Session, page_id: int, limit: int = 200) -> list[str]`
  - `mine_suggestions(db: Session, page_id: int, limit: int = 200) -> list[Suggestion]`
  - `approve_suggestion(db: Session, suggestion: Suggestion, user: User, title: str | None = None, answer: str | None = None) -> KnowledgeItem`
  - `reject_suggestion(db: Session, suggestion: Suggestion, user: User) -> Suggestion`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_learning_service.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_learning_service.py -v
```

Expected: collection error — `cannot import name 'learning' from 'app.services'`.

- [ ] **Step 3: Write `backend/app/services/learning.py`**

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_learning_service.py -v
```

Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/learning.py backend/tests/test_learning_service.py
git commit -m "feat: mine past conversations into reviewable knowledge suggestions"
```

---

## Task 16: Learning API and test chat

**Files:**
- Create: `backend/app/routers/learning.py`
- Create: `backend/app/routers/testchat.py`
- Modify: `backend/app/main.py` (register both routers)
- Test: `backend/tests/test_learning_api.py`
- Test: `backend/tests/test_testchat_api.py`

**Interfaces:**
- Consumes: `app.deps.page_viewer`, `app.deps.page_editor`, `app.deps.get_current_user`, `app.services.learning.*`, `app.services.chatbot.generate_answer`.
- Produces:
  - `SuggestionOut`: `{id, page_id, question, answer, occurrences, status, created_at, reviewed_at, knowledge_item_id}`
  - `POST /api/pages/{page_id}/learning/mine` → `{"created": int, "suggestions": list[SuggestionOut]}`
  - `GET /api/pages/{page_id}/suggestions?status=pending`
  - `POST /api/pages/{page_id}/suggestions/{suggestion_id}/approve` body `{title?: str, answer?: str}` → `SuggestionOut`
  - `POST /api/pages/{page_id}/suggestions/{suggestion_id}/reject` → `SuggestionOut`
  - `POST /api/pages/{page_id}/test-chat` body `{message: str}` → `{"answer": str, "context": list[str]}`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_learning_api.py`:

```python
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.db import SessionLocal
from app.models import KnowledgeItem
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
def with_history(page_id) -> int:
    session = SessionLocal()
    try:
        conversation_service.log_message(
            session, page_id, "psid-1", "in", "Học phí bao nhiêu?"
        )
    finally:
        session.close()
    return page_id


@pytest.fixture
def stub_miner(monkeypatch):
    batch = learning.SuggestionBatch(
        entries=[
            learning.SuggestedEntry(
                question="Học phí bao nhiêu?", answer="15 triệu mỗi kỳ.", occurrences=5
            )
        ]
    )

    class StubMiner:
        def invoke(self, _prompt):
            return batch

    monkeypatch.setattr(learning, "build_miner", lambda model="": StubMiner())


def test_mining_returns_the_created_suggestions(
    client, admin_token, auth, with_history, stub_miner
):
    response = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert body["suggestions"][0]["question"] == "Học phí bao nhiêu?"
    assert body["suggestions"][0]["occurrences"] == 5


def test_pending_suggestions_are_listed(
    client, admin_token, auth, with_history, stub_miner
):
    client.post(f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token))

    response = client.get(
        f"/api/pages/{with_history}/suggestions",
        headers=auth(admin_token),
        params={"status": "pending"},
    )

    assert [s["status"] for s in response.json()] == ["pending"]


def test_approving_adds_a_learned_knowledge_item(
    client, admin_token, auth, with_history, stub_miner
):
    suggestion_id = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token)
    ).json()["suggestions"][0]["id"]

    response = client.post(
        f"/api/pages/{with_history}/suggestions/{suggestion_id}/approve",
        headers=auth(admin_token),
        json={},
    )
    knowledge = client.get(
        f"/api/pages/{with_history}/knowledge", headers=auth(admin_token)
    ).json()

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert [item["source"] for item in knowledge] == ["learned"]
    assert knowledge[0]["content"] == "15 triệu mỗi kỳ."


def test_approving_with_edits_stores_the_edited_answer(
    client, admin_token, auth, with_history, stub_miner
):
    suggestion_id = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token)
    ).json()["suggestions"][0]["id"]

    client.post(
        f"/api/pages/{with_history}/suggestions/{suggestion_id}/approve",
        headers=auth(admin_token),
        json={"title": "Học phí hệ chính quy", "answer": "20 triệu mỗi kỳ."},
    )

    session = SessionLocal()
    try:
        item = session.query(KnowledgeItem).one()
        assert item.title == "Học phí hệ chính quy"
        assert item.content == "20 triệu mỗi kỳ."
    finally:
        session.close()


def test_rejecting_leaves_the_knowledge_base_empty(
    client, admin_token, auth, with_history, stub_miner
):
    suggestion_id = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token)
    ).json()["suggestions"][0]["id"]

    response = client.post(
        f"/api/pages/{with_history}/suggestions/{suggestion_id}/reject",
        headers=auth(admin_token),
    )
    knowledge = client.get(
        f"/api/pages/{with_history}/knowledge", headers=auth(admin_token)
    ).json()

    assert response.json()["status"] == "rejected"
    assert knowledge == []


def test_viewer_cannot_mine(
    client, admin_token, member_token, auth, with_history, member_user, stub_miner
):
    client.put(
        f"/api/pages/{with_history}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "viewer"},
    )

    response = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(member_token)
    )

    assert response.status_code == 403


def test_suggestion_from_another_page_returns_404(
    client, admin_token, auth, with_history, stub_miner
):
    suggestion_id = client.post(
        f"/api/pages/{with_history}/learning/mine", headers=auth(admin_token)
    ).json()["suggestions"][0]["id"]
    other = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={"fb_page_id": "777777777777777", "name": "Other", "access_token": "t"},
    ).json()["id"]

    response = client.post(
        f"/api/pages/{other}/suggestions/{suggestion_id}/approve",
        headers=auth(admin_token),
        json={},
    )

    assert response.status_code == 404
```

Create `backend/tests/test_testchat_api.py`:

```python
import pytest

from app.services import chatbot


@pytest.fixture(autouse=True)
def stub_answer(monkeypatch):
    monkeypatch.setattr(
        chatbot,
        "generate_answer",
        lambda db, page, question: (f"Trả lời cho: {question}", ["Học phí 15 triệu."]),
    )


def test_test_chat_returns_the_answer_and_the_context(client, admin_token, auth, page_id):
    response = client.post(
        f"/api/pages/{page_id}/test-chat",
        headers=auth(admin_token),
        json={"message": "Học phí bao nhiêu?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Trả lời cho: Học phí bao nhiêu?",
        "context": ["Học phí 15 triệu."],
    }


def test_test_chat_does_not_log_a_conversation(client, admin_token, auth, page_id):
    client.post(
        f"/api/pages/{page_id}/test-chat",
        headers=auth(admin_token),
        json={"message": "Học phí bao nhiêu?"},
    )

    listing = client.get(
        f"/api/pages/{page_id}/conversations", headers=auth(admin_token)
    )

    assert listing.json() == []


def test_empty_message_is_rejected(client, admin_token, auth, page_id):
    response = client.post(
        f"/api/pages/{page_id}/test-chat", headers=auth(admin_token), json={"message": ""}
    )

    assert response.status_code == 422


def test_viewer_cannot_use_test_chat(
    client, admin_token, member_token, auth, page_id, member_user
):
    client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "viewer"},
    )

    response = client.post(
        f"/api/pages/{page_id}/test-chat",
        headers=auth(member_token),
        json={"message": "Xin chào"},
    )

    assert response.status_code == 403
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_learning_api.py tests/test_testchat_api.py -v
```

Expected: 11 failures — 404/405, neither route group exists.

- [ ] **Step 3: Write `backend/app/routers/learning.py`**

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, page_editor, page_viewer
from app.models import Page, Suggestion, User
from app.services import learning

router = APIRouter(prefix="/api/pages/{page_id}", tags=["learning"])

VALID_STATUSES = {"pending", "approved", "rejected"}


class SuggestionOut(BaseModel):
    id: int
    page_id: int
    question: str
    answer: str
    occurrences: int
    status: str
    created_at: datetime
    reviewed_at: datetime | None
    knowledge_item_id: int | None

    model_config = {"from_attributes": True}


class MineOut(BaseModel):
    created: int
    suggestions: list[SuggestionOut]


class ApproveIn(BaseModel):
    title: str | None = None
    answer: str | None = None


def _get_suggestion(db: Session, page: Page, suggestion_id: int) -> Suggestion:
    suggestion = (
        db.query(Suggestion)
        .filter(Suggestion.id == suggestion_id, Suggestion.page_id == page.id)
        .one_or_none()
    )
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found"
        )
    return suggestion


@router.post("/learning/mine", response_model=MineOut)
def mine(
    page: Page = Depends(page_editor), db: Session = Depends(get_db)
) -> MineOut:
    created = learning.mine_suggestions(db, page.id)
    return MineOut(
        created=len(created),
        suggestions=[SuggestionOut.model_validate(item) for item in created],
    )


@router.get("/suggestions", response_model=list[SuggestionOut])
def list_suggestions(
    status_filter: str = Query(default="pending", alias="status"),
    page: Page = Depends(page_viewer),
    db: Session = Depends(get_db),
) -> list[Suggestion]:
    query = db.query(Suggestion).filter(Suggestion.page_id == page.id)
    if status_filter != "all":
        if status_filter not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"status must be 'all' or one of {sorted(VALID_STATUSES)}",
            )
        query = query.filter(Suggestion.status == status_filter)
    return query.order_by(Suggestion.occurrences.desc(), Suggestion.id.desc()).all()


@router.post("/suggestions/{suggestion_id}/approve", response_model=SuggestionOut)
def approve(
    suggestion_id: int,
    payload: ApproveIn,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Suggestion:
    suggestion = _get_suggestion(db, page, suggestion_id)
    if suggestion.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Suggestion is already {suggestion.status}",
        )
    learning.approve_suggestion(
        db, suggestion, user, title=payload.title, answer=payload.answer
    )
    db.refresh(suggestion)
    return suggestion


@router.post("/suggestions/{suggestion_id}/reject", response_model=SuggestionOut)
def reject(
    suggestion_id: int,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Suggestion:
    suggestion = _get_suggestion(db, page, suggestion_id)
    if suggestion.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Suggestion is already {suggestion.status}",
        )
    return learning.reject_suggestion(db, suggestion, user)
```

- [ ] **Step 4: Write `backend/app/routers/testchat.py`**

```python
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
```

- [ ] **Step 5: Register both routers in `backend/app/main.py`**

Change the routers import block to:

```python
from app.routers import (
    auth,
    conversations,
    knowledge,
    learning,
    members,
    pages,
    testchat,
    users,
    webhook,
)
```

and add inside `create_app()`:

```python
    application.include_router(learning.router)
    application.include_router(testchat.router)
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_learning_api.py tests/test_testchat_api.py -v
```

Expected: 11 passed.

- [ ] **Step 7: Run the whole backend suite**

```bash
cd backend && python -m pytest -v
```

Expected: everything passes.

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/learning.py backend/app/routers/testchat.py \
        backend/app/main.py backend/tests/test_learning_api.py \
        backend/tests/test_testchat_api.py
git commit -m "feat: add suggestion review queue and console test-chat endpoints"
```

---

## Task 17: Legacy retirement and seed script

**Files:**
- Create: `backend/scripts/__init__.py`
- Create: `backend/scripts/seed_from_legacy.py`
- Create: `README.md`
- Delete: `main.py`, `chatbot_engine.py`, `lead_manager.py`, `config.py` (repo root)
- Test: `backend/tests/test_seed_from_legacy.py`

**Interfaces:**
- Consumes: `app.db.SessionLocal`, `app.models.KnowledgeItem`, `app.models.Page`, `app.models.User`, `app.security.encrypt_token`, `app.security.hash_password`, `app.services.vector_store.build_index`.
- Produces:
  - `seed_page(db: Session, fb_page_id: str, name: str, access_token: str, data_dir: Path) -> tuple[Page, int]` — returns the page and the number of knowledge items imported; re-running it does not duplicate items.
  - `main(argv: list[str] | None = None) -> int` — CLI entry point.

The legacy root modules are deleted only at this point: every behaviour they carried now
has a tested home (`services/chatbot.py`, `routers/webhook.py`, `app/config.py`) — except
`lead_manager.py`'s document-collection logic, which is deliberately not ported (see spec
§6, Out of scope). The `data/` folder itself stays — it is the seed source.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_seed_from_legacy.py`:

```python
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.db import SessionLocal
from app.models import KnowledgeItem
from app.services import vector_store
from scripts.seed_from_legacy import seed_page


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
def data_dir(tmp_path):
    (tmp_path / "Học phí.txt").write_text("Học phí 15 triệu.", encoding="utf-8")
    (tmp_path / "Ngành nghề.txt").write_text("CNTT, Kế toán.", encoding="utf-8")
    (tmp_path / "notes.md").write_text("ignore me", encoding="utf-8")
    return tmp_path


def test_seeding_imports_every_txt_file(db, data_dir):
    page, count = seed_page(db, "111000111", "Legacy Page", "tok", data_dir)

    titles = {item.title for item in db.query(KnowledgeItem).all()}
    assert count == 2
    assert titles == {"Học phí", "Ngành nghề"}
    assert all(item.page_id == page.id for item in db.query(KnowledgeItem).all())


def test_imported_items_are_marked_with_the_imported_source(db, data_dir):
    seed_page(db, "111000111", "Legacy Page", "tok", data_dir)

    assert {item.source for item in db.query(KnowledgeItem).all()} == {"imported"}


def test_seeding_twice_does_not_duplicate_items(db, data_dir):
    seed_page(db, "111000111", "Legacy Page", "tok", data_dir)

    _, second_count = seed_page(db, "111000111", "Legacy Page", "tok", data_dir)

    assert second_count == 0
    assert db.query(KnowledgeItem).count() == 2


def test_seeded_content_is_searchable(db, data_dir):
    page, _ = seed_page(db, "111000111", "Legacy Page", "tok", data_dir)

    results = vector_store.search(db, page.id, "học phí", k=2)

    assert any("15 triệu" in chunk for chunk in results)


def test_missing_data_directory_imports_nothing(db, tmp_path):
    page, count = seed_page(db, "111000111", "Legacy Page", "tok", tmp_path / "nope")

    assert count == 0
    assert page.id is not None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && python -m pytest tests/test_seed_from_legacy.py -v
```

Expected: collection error — `ModuleNotFoundError: No module named 'scripts'`.

- [ ] **Step 3: Write `backend/scripts/seed_from_legacy.py`**

Create `backend/scripts/__init__.py` as an empty file, then:

```python
"""Import the legacy data/*.txt knowledge base into a page.

Usage:
    python -m scripts.seed_from_legacy \
        --fb-page-id 1234567890 \
        --name "Hateco Tuyen Sinh" \
        --access-token EAAG... \
        [--admin-email boss@hateco.vn --admin-password secret123]
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, Page, PageMembership, User
from app.security import encrypt_token, hash_password
from app.services import vector_store

DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


def seed_page(
    db: Session,
    fb_page_id: str,
    name: str,
    access_token: str,
    data_dir: Path,
) -> tuple[Page, int]:
    """Create the page if needed and import every *.txt file as a knowledge item.

    Returns (page, number of items imported). Files whose title already exists on
    the page are skipped, so re-running the script is safe.
    """
    page = db.query(Page).filter(Page.fb_page_id == fb_page_id).one_or_none()
    if page is None:
        page = Page(
            fb_page_id=fb_page_id,
            name=name,
            access_token_encrypted=encrypt_token(access_token),
        )
        db.add(page)
        db.commit()
        db.refresh(page)

    existing_titles = {
        title
        for (title,) in db.query(KnowledgeItem.title)
        .filter(KnowledgeItem.page_id == page.id)
        .all()
    }

    imported = 0
    if data_dir.is_dir():
        for path in sorted(data_dir.glob("*.txt")):
            title = path.stem
            if title in existing_titles:
                continue
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            db.add(
                KnowledgeItem(
                    page_id=page.id, title=title, content=content, source="imported"
                )
            )
            existing_titles.add(title)
            imported += 1

    if imported:
        db.commit()
    vector_store.build_index(db, page.id)
    return page, imported


def _ensure_admin(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(email=email, password_hash=hash_password(password), role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed a page from the legacy data folder")
    parser.add_argument("--fb-page-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--access-token", default="")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--admin-email", default="")
    parser.add_argument("--admin-password", default="")
    args = parser.parse_args(argv)

    init_db()
    db = SessionLocal()
    try:
        page, imported = seed_page(
            db, args.fb_page_id, args.name, args.access_token, Path(args.data_dir)
        )
        print(f"Page '{page.name}' (id={page.id}): imported {imported} knowledge items")

        if args.admin_email and args.admin_password:
            admin = _ensure_admin(db, args.admin_email, args.admin_password)
            membership = (
                db.query(PageMembership)
                .filter(
                    PageMembership.page_id == page.id,
                    PageMembership.user_id == admin.id,
                )
                .one_or_none()
            )
            if membership is None:
                db.add(
                    PageMembership(page_id=page.id, user_id=admin.id, role="owner")
                )
                db.commit()
            print(f"Admin '{admin.email}' owns page {page.id}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd backend && python -m pytest tests/test_seed_from_legacy.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Delete the superseded root modules**

```bash
git rm main.py chatbot_engine.py lead_manager.py config.py
```

- [ ] **Step 6: Confirm nothing still imports them**

```bash
grep -rn "chatbot_engine\|lead_manager\|^from config import\|^import config" \
  --include=*.py backend/
```

Expected: no output.

- [ ] **Step 7: Write `README.md`**

````markdown
# Hateco Chatbot Console

A multi-page Facebook Messenger chatbot with a web console for managing pages,
per-page knowledge and instructions, conversation history, and a human-reviewed
learning loop.

## Layout

- `backend/` — FastAPI app, SQLite database, FAISS indexes, pytest suite
- `frontend/` — React + Vite admin console
- `data/` — legacy knowledge text files, used once by the seed script

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # .venv/bin/python on macOS/Linux
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# paste that value into TOKEN_ENCRYPTION_KEY in .env, then set SECRET_KEY and OPENROUTER_API_KEY
```

## Run the backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Console: http://localhost:5173

## First run

Open the console and create the first admin account — the login screen offers it
while no user exists. Then add a page with its Facebook Page ID and Page Access
Token.

To import the legacy `data/*.txt` knowledge into a page:

```bash
cd backend
python -m scripts.seed_from_legacy --fb-page-id 1234567890 --name "Hateco Tuyen Sinh" \
  --access-token EAAG... --admin-email you@hateco.vn --admin-password your-password
```

## Facebook webhook

Point the Facebook App webhook at `https://<your-host>/webhook` and use the
`VERIFY_TOKEN` from `.env`. One webhook serves every page: events are routed by the
Facebook Page ID in the payload.

## Tests

```bash
cd backend && python -m pytest       # backend
cd frontend && npm test -- --run     # frontend
```
````

- [ ] **Step 8: Run the whole backend suite**

```bash
cd backend && python -m pytest -v
```

Expected: everything passes.

- [ ] **Step 9: Commit**

```bash
git add backend/scripts README.md backend/tests/test_seed_from_legacy.py
git add -u
git commit -m "feat: add legacy seed script and retire the single-page modules"
```

---

## Task 18: Frontend scaffold, API client and login

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/.env.example`
- Create: `frontend/src/main.tsx`, `frontend/src/index.css`, `frontend/src/App.tsx`
- Create: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`, `frontend/src/lib/auth.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Test: `frontend/src/test/setup.ts`, `frontend/src/lib/api.test.ts`, `frontend/src/pages/LoginPage.test.tsx`

**Interfaces:**
- Consumes: `POST /api/auth/login`, `POST /api/auth/bootstrap`, `GET /api/auth/me`.
- Produces:
  - `lib/types.ts`: `User`, `PageSummary`, `KnowledgeItem`, `ConversationSummary`, `Message`, `ConversationDetail`, `Suggestion`, `Member` — the shapes every later task imports. `PageSummary` carries `closing_message: string`.
  - `lib/api.ts`: `ApiError` (has `status: number`), `getToken()`, `setToken(token: string | null)`, `apiFetch<T>(path: string, options?: RequestInit): Promise<T>`.
  - `lib/auth.tsx`: `AuthProvider`, `useAuth(): { user: User | null; loading: boolean; login(email, password): Promise<void>; bootstrap(email, password): Promise<void>; logout(): void }`.
  - `pages/LoginPage.tsx`: default-exported `LoginPage` — a form that logs in, and creates the first admin when the backend reports bootstrap is still available.

- [ ] **Step 1: Create the project files**

Create `frontend/package.json`:

```json
{
  "name": "hateco-console",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^7.1.1"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.1.0",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.18",
    "@types/react-dom": "^18.3.5",
    "@vitejs/plugin-react": "^4.3.4",
    "jsdom": "^26.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.2",
    "vite": "^6.0.7",
    "vitest": "^3.0.0"
  }
}
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"]
}
```

Create `frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "types": ["node"],
    "skipLibCheck": true,
    "noEmit": true
  },
  "include": ["vite.config.ts"]
}
```

Create `frontend/vite.config.ts`:

```ts
/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
```

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Hateco Chatbot Console</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/.env.example`:

```dotenv
VITE_API_BASE=http://localhost:8000
```

Create `frontend/src/index.css`:

```css
@import 'tailwindcss';

body {
  @apply bg-slate-50 text-slate-900 antialiased;
}
```

Create `frontend/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => {
  cleanup()
  localStorage.clear()
})
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend && npm install
```

- [ ] **Step 3: Write the failing tests**

Create `frontend/src/lib/api.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiFetch, getToken, setToken } from './api'

function mockFetch(status: number, body: unknown) {
  const response = {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  }
  const spy = vi.fn().mockResolvedValue(response)
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('apiFetch', () => {
  it('returns the parsed JSON body', async () => {
    mockFetch(200, { status: 'ok' })

    await expect(apiFetch('/api/health')).resolves.toEqual({ status: 'ok' })
  })

  it('attaches the bearer token when one is stored', async () => {
    setToken('tok-123')
    const spy = mockFetch(200, {})

    await apiFetch('/api/auth/me')

    const headers = spy.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer tok-123')
  })

  it('sends no Authorization header when signed out', async () => {
    const spy = mockFetch(200, {})

    await apiFetch('/api/health')

    const headers = spy.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBeNull()
  })

  it('throws an ApiError carrying the status and the detail', async () => {
    mockFetch(401, { detail: 'Invalid credentials' })

    await expect(apiFetch('/api/auth/login')).rejects.toMatchObject({
      status: 401,
      message: 'Invalid credentials',
    })
  })

  it('resolves to undefined for a 204 response', async () => {
    mockFetch(204, undefined)

    await expect(apiFetch('/api/pages/1')).resolves.toBeUndefined()
  })

  it('keeps ApiError instances recognisable', async () => {
    mockFetch(500, { detail: 'boom' })

    await expect(apiFetch('/api/health')).rejects.toBeInstanceOf(ApiError)
  })
})

describe('token storage', () => {
  it('round-trips and clears the token', () => {
    setToken('tok-123')
    expect(getToken()).toBe('tok-123')

    setToken(null)
    expect(getToken()).toBeNull()
  })
})
```

Create `frontend/src/pages/LoginPage.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider } from '../lib/auth'
import LoginPage from './LoginPage'

type Route = { status: number; body: unknown }

function mockRoutes(routes: Record<string, Route>) {
  const spy = vi.fn(async (url: string) => {
    const path = url.replace('http://localhost:8000', '')
    const route = routes[path] ?? { status: 404, body: { detail: 'not mocked' } }
    return {
      ok: route.status >= 200 && route.status < 300,
      status: route.status,
      text: async () => JSON.stringify(route.body),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

function renderLogin() {
  return render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('LoginPage', () => {
  it('signs in and stores the token', async () => {
    const spy = mockRoutes({
      '/api/auth/bootstrap-available': { status: 200, body: { available: false } },
      '/api/auth/login': {
        status: 200,
        body: {
          access_token: 'tok-abc',
          token_type: 'bearer',
          user: { id: 1, email: 'boss@hateco.vn', role: 'admin', is_active: true },
        },
      },
    })
    renderLogin()

    await userEvent.type(screen.getByLabelText(/email/i), 'boss@hateco.vn')
    await userEvent.type(screen.getByLabelText(/password/i), 'hunter2hunter2')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(localStorage.getItem('hateco.token')).toBe('tok-abc'))
    expect(spy).toHaveBeenCalled()
  })

  it('shows the server error when the credentials are wrong', async () => {
    mockRoutes({
      '/api/auth/bootstrap-available': { status: 200, body: { available: false } },
      '/api/auth/login': { status: 401, body: { detail: 'Invalid credentials' } },
    })
    renderLogin()

    await userEvent.type(screen.getByLabelText(/email/i), 'boss@hateco.vn')
    await userEvent.type(screen.getByLabelText(/password/i), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid credentials')
  })

  it('offers to create the first admin when bootstrap is available', async () => {
    mockRoutes({
      '/api/auth/bootstrap-available': { status: 200, body: { available: true } },
    })
    renderLogin()

    expect(
      await screen.findByRole('button', { name: /create the first admin/i }),
    ).toBeInTheDocument()
  })

  it('hides the bootstrap button once a user exists', async () => {
    mockRoutes({
      '/api/auth/bootstrap-available': { status: 200, body: { available: false } },
    })
    renderLogin()

    await screen.findByRole('button', { name: /sign in/i })
    expect(
      screen.queryByRole('button', { name: /create the first admin/i }),
    ).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run
```

Expected: both files fail to resolve their imports — `Failed to resolve import "./api"`
and `"../lib/auth"`.

- [ ] **Step 5: Add the `bootstrap-available` endpoint to the backend**

The login screen needs to know whether the first admin still has to be created.
In `backend/app/routers/auth.py`, add this response model next to the others:

```python
class BootstrapAvailableOut(BaseModel):
    available: bool
```

and this endpoint after the `bootstrap` handler:

```python
@router.get("/bootstrap-available", response_model=BootstrapAvailableOut)
def bootstrap_available(db: Session = Depends(get_db)) -> BootstrapAvailableOut:
    """Unauthenticated: tells the login screen whether to offer first-admin creation."""
    return BootstrapAvailableOut(available=db.query(User).count() == 0)
```

Add its test to `backend/tests/test_auth.py`:

```python
def test_bootstrap_available_flips_after_the_first_user(client):
    before = client.get("/api/auth/bootstrap-available").json()

    client.post(
        "/api/auth/bootstrap",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )
    after = client.get("/api/auth/bootstrap-available").json()

    assert before == {"available": True}
    assert after == {"available": False}
```

Run it:

```bash
cd backend && python -m pytest tests/test_auth.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Write `frontend/src/lib/types.ts`**

```ts
export interface User {
  id: number
  email: string
  role: string
  is_active: boolean
}

export interface PageSummary {
  id: number
  fb_page_id: string
  name: string
  system_prompt: string
  closing_message: string
  llm_model: string
  is_active: boolean
  has_access_token: boolean
  my_role: string
  knowledge_count: number
  created_at: string
}

export interface KnowledgeItem {
  id: number
  page_id: number
  title: string
  content: string
  source: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ConversationSummary {
  id: number
  psid: string
  started_at: string
  last_message_at: string
  message_count: number
  last_message_preview: string
}

export interface Message {
  id: number
  direction: 'in' | 'out'
  text: string
  attachments: unknown[]
  created_at: string
}

export interface ConversationDetail {
  id: number
  psid: string
  started_at: string
  last_message_at: string
  messages: Message[]
}

export interface Suggestion {
  id: number
  page_id: number
  question: string
  answer: string
  occurrences: number
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
  reviewed_at: string | null
  knowledge_item_id: number | null
}

export interface Member {
  user_id: number
  email: string
  role: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}
```

- [ ] **Step 7: Write `frontend/src/lib/api.ts`**

```ts
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
const TOKEN_KEY = 'hateco.token'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token === null) localStorage.removeItem(TOKEN_KEY)
    else localStorage.setItem(TOKEN_KEY, token)
  } catch {
    /* private mode or blocked storage: the session simply will not persist */
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (response.status === 204) return undefined as T

  const raw = await response.text()
  const data: unknown = raw ? JSON.parse(raw) : null

  if (!response.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail
    const message =
      typeof detail === 'string' ? detail : `Request failed (${response.status})`
    throw new ApiError(response.status, message)
  }
  return data as T
}
```

- [ ] **Step 8: Write `frontend/src/lib/auth.tsx`**

```tsx
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { apiFetch, getToken, setToken } from './api'
import type { TokenResponse, User } from './types'

interface AuthValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  bootstrap: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    apiFetch<User>('/api/auth/me')
      .then(setUser)
      .catch(() => {
        setToken(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const authenticate = useCallback(async (path: string, email: string, password: string) => {
    const result = await apiFetch<TokenResponse>(path, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    setToken(result.access_token)
    setUser(result.user)
  }, [])

  const value = useMemo<AuthValue>(
    () => ({
      user,
      loading,
      login: (email, password) => authenticate('/api/auth/login', email, password),
      bootstrap: (email, password) =>
        authenticate('/api/auth/bootstrap', email, password),
      logout: () => {
        setToken(null)
        setUser(null)
      },
    }),
    [user, loading, authenticate],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (value === null) throw new Error('useAuth must be used inside an AuthProvider')
  return value
}
```

- [ ] **Step 9: Write `frontend/src/pages/LoginPage.tsx`**

```tsx
import { useEffect, useState, type FormEvent } from 'react'

import { apiFetch } from '../lib/api'
import { useAuth } from '../lib/auth'

export default function LoginPage() {
  const { login, bootstrap } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [canBootstrap, setCanBootstrap] = useState(false)

  useEffect(() => {
    apiFetch<{ available: boolean }>('/api/auth/bootstrap-available')
      .then((result) => setCanBootstrap(result.available))
      .catch(() => setCanBootstrap(false))
  }, [])

  async function submit(event: FormEvent, mode: 'login' | 'bootstrap') {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'login') await login(email, password)
      else await bootstrap(email, password)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form
        onSubmit={(event) => submit(event, 'login')}
        className="w-full max-w-sm space-y-4 rounded-xl border border-slate-200 bg-white p-8 shadow-sm"
      >
        <div>
          <h1 className="text-xl font-semibold">Hateco Chatbot Console</h1>
          <p className="mt-1 text-sm text-slate-500">
            {canBootstrap ? 'No account exists yet.' : 'Sign in to manage your pages.'}
          </p>
        </div>

        <div className="space-y-1">
          <label htmlFor="email" className="block text-sm font-medium">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="block text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        {error && (
          <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Sign in
        </button>

        {canBootstrap && (
          <button
            type="button"
            disabled={busy}
            onClick={(event) => submit(event, 'bootstrap')}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-medium disabled:opacity-50"
          >
            Create the first admin
          </button>
        )}
      </form>
    </div>
  )
}
```

- [ ] **Step 10: Write `frontend/src/App.tsx` and `frontend/src/main.tsx`**

`frontend/src/App.tsx` — a placeholder shell; Task 19 replaces it with the router:

```tsx
import { useAuth } from './lib/auth'
import LoginPage from './pages/LoginPage'

export default function App() {
  const { user, loading } = useAuth()

  if (loading) return <p className="p-8 text-sm text-slate-500">Loading…</p>
  if (!user) return <LoginPage />
  return <p className="p-8 text-sm">Signed in as {user.email}</p>
}
```

`frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App'
import './index.css'
import { AuthProvider } from './lib/auth'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)
```

- [ ] **Step 11: Run the tests to verify they pass**

```bash
cd frontend && npm test -- --run
```

Expected: 11 passed (7 in `api.test.ts`, 4 in `LoginPage.test.tsx`).

- [ ] **Step 12: Commit**

```bash
git add frontend .gitignore backend/app/routers/auth.py backend/tests/test_auth.py
git commit -m "feat: scaffold React console with API client, auth context and login"
```

---

## Task 19: App shell, routing and the pages list

**Files:**
- Create: `frontend/src/components/ProtectedRoute.tsx`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/pages/PagesListPage.tsx`
- Modify: `frontend/src/App.tsx` (replace the placeholder with the router)
- Modify: `frontend/src/main.tsx` (wrap in `BrowserRouter`)
- Test: `frontend/src/pages/PagesListPage.test.tsx`

**Interfaces:**
- Consumes: `apiFetch`, `useAuth`, `PageSummary`.
- Produces:
  - `components/ProtectedRoute.tsx` — default-exported `ProtectedRoute`, renders `<Outlet />` when signed in, `<Navigate to="/login" />` otherwise, and `Loading…` while the session is resolving.
  - `components/Layout.tsx` — default-exported `Layout` with the top bar (product name, "Pages" link, "Users" link for admins, the signed-in email, a "Sign out" button) and an `<Outlet />`.
  - `pages/PagesListPage.tsx` — default-exported `PagesListPage`.
  - Routes: `/login`, `/` → `/pages`, `/pages`, `/pages/:pageId`, `/users`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/PagesListPage.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import PagesListPage from './PagesListPage'

const PAGE = {
  id: 1,
  fb_page_id: '100000000000001',
  name: 'Hateco Tuyen Sinh',
  system_prompt: '',
  llm_model: '',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 5,
  created_at: '2026-09-18T00:00:00Z',
}

function mockApi(handler: (path: string, init?: RequestInit) => { status: number; body: unknown }) {
  const spy = vi.fn(async (url: string, init?: RequestInit) => {
    const route = handler(url.replace('http://localhost:8000', ''), init)
    return {
      ok: route.status >= 200 && route.status < 300,
      status: route.status,
      text: async () => JSON.stringify(route.body),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

function renderPage() {
  return render(
    <MemoryRouter>
      <PagesListPage />
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('PagesListPage', () => {
  it('lists the pages returned by the API', async () => {
    mockApi(() => ({ status: 200, body: [PAGE] }))
    renderPage()

    expect(await screen.findByText('Hateco Tuyen Sinh')).toBeInTheDocument()
    expect(screen.getByText('100000000000001')).toBeInTheDocument()
  })

  it('shows an empty state when there are no pages', async () => {
    mockApi(() => ({ status: 200, body: [] }))
    renderPage()

    expect(await screen.findByText(/no pages yet/i)).toBeInTheDocument()
  })

  it('creates a page and shows it in the list', async () => {
    let created = false
    mockApi((path, init) => {
      if (init?.method === 'POST') {
        created = true
        return { status: 201, body: PAGE }
      }
      return { status: 200, body: created ? [PAGE] : [] }
    })
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: /add page/i }))
    await userEvent.type(screen.getByLabelText(/facebook page id/i), '100000000000001')
    await userEvent.type(screen.getByLabelText(/display name/i), 'Hateco Tuyen Sinh')
    await userEvent.type(screen.getByLabelText(/page access token/i), 'EAAG-secret')
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }))

    expect(await screen.findByText('Hateco Tuyen Sinh')).toBeInTheDocument()
  })

  it('shows the server error when creation fails', async () => {
    mockApi((_path, init) =>
      init?.method === 'POST'
        ? { status: 409, body: { detail: 'A page with this Facebook Page ID already exists' } }
        : { status: 200, body: [] },
    )
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: /add page/i }))
    await userEvent.type(screen.getByLabelText(/facebook page id/i), '1')
    await userEvent.type(screen.getByLabelText(/display name/i), 'Dup')
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('already exists')
  })

  it('marks an inactive page', async () => {
    mockApi(() => ({ status: 200, body: [{ ...PAGE, is_active: false }] }))
    renderPage()

    expect(await screen.findByText(/inactive/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/pages/PagesListPage.test.tsx
```

Expected: `Failed to resolve import "./PagesListPage"`.

- [ ] **Step 3: Write `frontend/src/pages/PagesListPage.tsx`**

```tsx
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { apiFetch } from '../lib/api'
import type { PageSummary } from '../lib/types'

export default function PagesListPage() {
  const [pages, setPages] = useState<PageSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState('')
  const [fbPageId, setFbPageId] = useState('')
  const [name, setName] = useState('')
  const [accessToken, setAccessToken] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setPages(await apiFetch<PageSummary[]>('/api/pages'))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load pages')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  async function createPage(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await apiFetch<PageSummary>('/api/pages', {
        method: 'POST',
        body: JSON.stringify({
          fb_page_id: fbPageId,
          name,
          access_token: accessToken,
        }),
      })
      setShowForm(false)
      setFbPageId('')
      setName('')
      setAccessToken('')
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not create the page')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Pages</h1>
        <button
          type="button"
          onClick={() => setShowForm((open) => !open)}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
        >
          Add page
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={createPage}
          className="space-y-3 rounded-xl border border-slate-200 bg-white p-5"
        >
          <div className="space-y-1">
            <label htmlFor="fb-page-id" className="block text-sm font-medium">
              Facebook Page ID
            </label>
            <input
              id="fb-page-id"
              required
              value={fbPageId}
              onChange={(event) => setFbPageId(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="page-name" className="block text-sm font-medium">
              Display name
            </label>
            <input
              id="page-name"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="page-token" className="block text-sm font-medium">
              Page Access Token
            </label>
            <input
              id="page-token"
              type="password"
              value={accessToken}
              onChange={(event) => setAccessToken(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <p className="text-xs text-slate-500">
              Stored encrypted. It is never shown again after saving.
            </p>
          </div>
          <button
            type="submit"
            className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
          >
            Create
          </button>
        </form>
      )}

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : pages.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          No pages yet. Add the first Facebook Page to start.
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {pages.map((page) => (
            <li key={page.id}>
              <Link
                to={`/pages/${page.id}`}
                className="block rounded-xl border border-slate-200 bg-white p-5 hover:border-slate-400"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{page.name}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                    {page.my_role}
                  </span>
                </div>
                <p className="mt-1 font-mono text-xs text-slate-500">{page.fb_page_id}</p>
                <p className="mt-3 text-xs text-slate-500">
                  {page.knowledge_count} knowledge items
                  {!page.is_active && ' · Inactive'}
                  {!page.has_access_token && ' · No access token'}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Write `frontend/src/components/ProtectedRoute.tsx`**

```tsx
import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '../lib/auth'

export default function ProtectedRoute() {
  const { user, loading } = useAuth()

  if (loading) return <p className="p-8 text-sm text-slate-500">Loading…</p>
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}
```

- [ ] **Step 5: Write `frontend/src/components/Layout.tsx`**

```tsx
import { Link, NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../lib/auth'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm ${isActive ? 'font-medium text-slate-900' : 'text-slate-500 hover:text-slate-900'}`

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <Link to="/pages" className="text-sm font-semibold">
            Hateco Console
          </Link>
          <nav className="flex items-center gap-4">
            <NavLink to="/pages" className={linkClass}>
              Pages
            </NavLink>
            {user?.role === 'admin' && (
              <NavLink to="/users" className={linkClass}>
                Users
              </NavLink>
            )}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <span className="text-xs text-slate-500">{user?.email}</span>
            <button
              type="button"
              onClick={logout}
              className="rounded-md border border-slate-300 px-2 py-1 text-xs"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 6: Replace `frontend/src/App.tsx` with the router**

```tsx
import { Navigate, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import PagesListPage from './pages/PagesListPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/pages" replace />} />
          <Route path="/pages" element={<PagesListPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/pages" replace />} />
    </Routes>
  )
}
```

- [ ] **Step 7: Wrap the app in `BrowserRouter` in `frontend/src/main.tsx`**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import './index.css'
import { AuthProvider } from './lib/auth'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
```

- [ ] **Step 8: Run the tests to verify they pass**

```bash
cd frontend && npm test -- --run
```

Expected: 16 passed.

- [ ] **Step 9: Commit**

```bash
git add frontend/src
git commit -m "feat: add console shell, protected routing and the pages list"
```

---

## Task 20: Page detail shell and the Knowledge tab

**Files:**
- Create: `frontend/src/components/Tabs.tsx`
- Create: `frontend/src/pages/PageDetailPage.tsx`
- Create: `frontend/src/pages/tabs/KnowledgeTab.tsx`
- Modify: `frontend/src/App.tsx` (add the `/pages/:pageId` route)
- Test: `frontend/src/pages/tabs/KnowledgeTab.test.tsx`

**Interfaces:**
- Consumes: `apiFetch`, `PageSummary`, `KnowledgeItem`.
- Produces:
  - `components/Tabs.tsx` — named export `Tabs({ tabs, active, onChange })` where `tabs: { id: string; label: string }[]`.
  - `pages/PageDetailPage.tsx` — default-exported `PageDetailPage`; loads the page by `:pageId`, holds the active tab in state, passes `page` and a `reloadPage` callback to each tab.
  - `pages/tabs/KnowledgeTab.tsx` — default-exported `KnowledgeTab({ page }: { page: PageSummary })`.
  - Every later tab takes the same `{ page }` prop (plus `reloadPage` where it edits page fields).

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/tabs/KnowledgeTab.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { KnowledgeItem, PageSummary } from '../../lib/types'
import KnowledgeTab from './KnowledgeTab'

const PAGE: PageSummary = {
  id: 7,
  fb_page_id: '100000000000001',
  name: 'Hateco',
  system_prompt: '',
  closing_message: '',
  llm_model: '',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 1,
  created_at: '2026-09-18T00:00:00Z',
}

const ITEM: KnowledgeItem = {
  id: 3,
  page_id: 7,
  title: 'Hoc phi',
  content: '15 trieu moi ky.',
  source: 'manual',
  is_active: true,
  created_at: '2026-09-18T00:00:00Z',
  updated_at: '2026-09-18T00:00:00Z',
}

function mockApi(
  handler: (path: string, init?: RequestInit) => { status: number; body: unknown },
) {
  const spy = vi.fn(async (url: string, init?: RequestInit) => {
    const route = handler(url.replace('http://localhost:8000', ''), init)
    return {
      ok: route.status >= 200 && route.status < 300,
      status: route.status,
      text: async () => (route.status === 204 ? '' : JSON.stringify(route.body)),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('KnowledgeTab', () => {
  it('lists the page knowledge', async () => {
    mockApi(() => ({ status: 200, body: [ITEM] }))
    render(<KnowledgeTab page={PAGE} />)

    expect(await screen.findByText('Hoc phi')).toBeInTheDocument()
    expect(screen.getByText('15 trieu moi ky.')).toBeInTheDocument()
  })

  it('requests knowledge for the right page', async () => {
    const spy = mockApi(() => ({ status: 200, body: [] }))
    render(<KnowledgeTab page={PAGE} />)

    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(
        'http://localhost:8000/api/pages/7/knowledge',
        expect.anything(),
      ),
    )
  })

  it('creates a knowledge item', async () => {
    let items: KnowledgeItem[] = []
    mockApi((_path, init) => {
      if (init?.method === 'POST') {
        items = [ITEM]
        return { status: 201, body: ITEM }
      }
      return { status: 200, body: items }
    })
    render(<KnowledgeTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /add item/i }))
    await userEvent.type(screen.getByLabelText(/title/i), 'Hoc phi')
    await userEvent.type(screen.getByLabelText(/content/i), '15 trieu moi ky.')
    await userEvent.click(screen.getByRole('button', { name: /^save$/i }))

    expect(await screen.findByText('Hoc phi')).toBeInTheDocument()
  })

  it('deletes a knowledge item', async () => {
    let items: KnowledgeItem[] = [ITEM]
    mockApi((_path, init) => {
      if (init?.method === 'DELETE') {
        items = []
        return { status: 204, body: null }
      }
      return { status: 200, body: items }
    })
    render(<KnowledgeTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /delete/i }))

    await waitFor(() => expect(screen.queryByText('Hoc phi')).not.toBeInTheDocument())
  })

  it('shows the learned badge for mined knowledge', async () => {
    mockApi(() => ({ status: 200, body: [{ ...ITEM, source: 'learned' }] }))
    render(<KnowledgeTab page={PAGE} />)

    expect(await screen.findByText(/learned/i)).toBeInTheDocument()
  })

  it('shows an empty state', async () => {
    mockApi(() => ({ status: 200, body: [] }))
    render(<KnowledgeTab page={PAGE} />)

    expect(await screen.findByText(/no knowledge yet/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/pages/tabs/KnowledgeTab.test.tsx
```

Expected: `Failed to resolve import "./KnowledgeTab"`.

- [ ] **Step 3: Write `frontend/src/pages/tabs/KnowledgeTab.tsx`**

```tsx
import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { apiFetch } from '../../lib/api'
import type { KnowledgeItem, PageSummary } from '../../lib/types'

export default function KnowledgeTab({ page }: { page: PageSummary }) {
  const [items, setItems] = useState<KnowledgeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setItems(await apiFetch<KnowledgeItem[]>(`/api/pages/${page.id}/knowledge`))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load knowledge')
    } finally {
      setLoading(false)
    }
  }, [page.id])

  useEffect(() => {
    void reload()
  }, [reload])

  function startCreate() {
    setEditingId('new')
    setTitle('')
    setContent('')
  }

  function startEdit(item: KnowledgeItem) {
    setEditingId(item.id)
    setTitle(item.title)
    setContent(item.content)
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      if (editingId === 'new') {
        await apiFetch(`/api/pages/${page.id}/knowledge`, {
          method: 'POST',
          body: JSON.stringify({ title, content }),
        })
      } else {
        await apiFetch(`/api/pages/${page.id}/knowledge/${editingId}`, {
          method: 'PATCH',
          body: JSON.stringify({ title, content }),
        })
      }
      setEditingId(null)
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save the item')
    }
  }

  async function remove(item: KnowledgeItem) {
    setError('')
    try {
      await apiFetch(`/api/pages/${page.id}/knowledge/${item.id}`, { method: 'DELETE' })
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not delete the item')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          What this page knows. Saving rebuilds the search index immediately.
        </p>
        <button
          type="button"
          onClick={startCreate}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
        >
          Add item
        </button>
      </div>

      {editingId !== null && (
        <form
          onSubmit={save}
          className="space-y-3 rounded-xl border border-slate-200 bg-white p-5"
        >
          <div className="space-y-1">
            <label htmlFor="knowledge-title" className="block text-sm font-medium">
              Title
            </label>
            <input
              id="knowledge-title"
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="knowledge-content" className="block text-sm font-medium">
              Content
            </label>
            <textarea
              id="knowledge-content"
              required
              rows={6}
              value={content}
              onChange={(event) => setContent(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
            >
              Save
            </button>
            <button
              type="button"
              onClick={() => setEditingId(null)}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          No knowledge yet. Add what this page should be able to answer.
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium">{item.title}</p>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-600">
                    {item.content}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {item.source !== 'manual' && (
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                      {item.source}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => startEdit(item)}
                    className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => remove(item)}
                    className="rounded-md border border-red-300 px-2 py-1 text-xs text-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Write `frontend/src/components/Tabs.tsx`**

```tsx
export interface TabDefinition {
  id: string
  label: string
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: TabDefinition[]
  active: string
  onChange: (id: string) => void
}) {
  return (
    <div role="tablist" className="flex gap-1 border-b border-slate-200">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          type="button"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={`-mb-px border-b-2 px-3 py-2 text-sm ${
            active === tab.id
              ? 'border-slate-900 font-medium text-slate-900'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 5: Write `frontend/src/pages/PageDetailPage.tsx`**

Later tasks add the remaining tabs to `TABS` and to the `switch`. For now only
Knowledge is wired; the other ids are added as their tabs land.

```tsx
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Tabs, type TabDefinition } from '../components/Tabs'
import { apiFetch } from '../lib/api'
import type { PageSummary } from '../lib/types'
import KnowledgeTab from './tabs/KnowledgeTab'

const TABS: TabDefinition[] = [{ id: 'knowledge', label: 'Knowledge' }]

export default function PageDetailPage() {
  const { pageId } = useParams()
  const [page, setPage] = useState<PageSummary | null>(null)
  const [error, setError] = useState('')
  const [active, setActive] = useState('knowledge')

  const reloadPage = useCallback(async () => {
    try {
      setPage(await apiFetch<PageSummary>(`/api/pages/${pageId}`))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load the page')
    }
  }, [pageId])

  useEffect(() => {
    void reloadPage()
  }, [reloadPage])

  if (error) {
    return (
      <div className="space-y-4">
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
        <Link to="/pages" className="text-sm underline">
          Back to pages
        </Link>
      </div>
    )
  }

  if (!page) return <p className="text-sm text-slate-500">Loading…</p>

  return (
    <div className="space-y-6">
      <div>
        <Link to="/pages" className="text-xs text-slate-500 hover:underline">
          ← Pages
        </Link>
        <h1 className="mt-1 text-lg font-semibold">{page.name}</h1>
        <p className="font-mono text-xs text-slate-500">{page.fb_page_id}</p>
      </div>

      <Tabs tabs={TABS} active={active} onChange={setActive} />

      {active === 'knowledge' && <KnowledgeTab page={page} />}
    </div>
  )
}
```

- [ ] **Step 6: Add the route in `frontend/src/App.tsx`**

Add the import:

```tsx
import PageDetailPage from './pages/PageDetailPage'
```

and the route, directly after the `/pages` route:

```tsx
          <Route path="/pages/:pageId" element={<PageDetailPage />} />
```

- [ ] **Step 7: Run the tests to verify they pass**

```bash
cd frontend && npm test -- --run
```

Expected: 22 passed.

- [ ] **Step 8: Commit**

```bash
git add frontend/src
git commit -m "feat: add page detail shell with the knowledge tab"
```

---

## Task 21: Instructions tab and test chat

**Files:**
- Create: `frontend/src/components/TestChatPanel.tsx`
- Create: `frontend/src/pages/tabs/InstructionsTab.tsx`
- Modify: `frontend/src/pages/PageDetailPage.tsx` (add the Instructions tab)
- Test: `frontend/src/pages/tabs/InstructionsTab.test.tsx`
- Test: `frontend/src/components/TestChatPanel.test.tsx`

**Interfaces:**
- Consumes: `apiFetch`, `PageSummary`, `PATCH /api/pages/{id}`, `POST /api/pages/{id}/test-chat`.
- Produces:
  - `components/TestChatPanel.tsx` — default-exported `TestChatPanel({ page }: { page: PageSummary })`.
  - `pages/tabs/InstructionsTab.tsx` — default-exported `InstructionsTab({ page, reloadPage }: { page: PageSummary; reloadPage: () => Promise<void> })`.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/TestChatPanel.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../lib/types'
import TestChatPanel from './TestChatPanel'

const PAGE: PageSummary = {
  id: 7,
  fb_page_id: '1',
  name: 'Hateco',
  system_prompt: '',
  closing_message: '',
  llm_model: '',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 1,
  created_at: '2026-09-18T00:00:00Z',
}

function mockApi(route: { status: number; body: unknown }) {
  const spy = vi.fn(async () => ({
    ok: route.status >= 200 && route.status < 300,
    status: route.status,
    text: async () => JSON.stringify(route.body),
  }))
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('TestChatPanel', () => {
  it('shows the generated answer', async () => {
    mockApi({ status: 200, body: { answer: 'Chao em!', context: ['Hoc phi 15 trieu.'] } })
    render(<TestChatPanel page={PAGE} />)

    await userEvent.type(screen.getByLabelText(/test message/i), 'Hoc phi bao nhieu?')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    expect(await screen.findByText('Chao em!')).toBeInTheDocument()
  })

  it('shows the retrieved context chunks', async () => {
    mockApi({ status: 200, body: { answer: 'Chao em!', context: ['Hoc phi 15 trieu.'] } })
    render(<TestChatPanel page={PAGE} />)

    await userEvent.type(screen.getByLabelText(/test message/i), 'Hoc phi?')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    expect(await screen.findByText('Hoc phi 15 trieu.')).toBeInTheDocument()
  })

  it('surfaces a failure', async () => {
    mockApi({ status: 500, body: { detail: 'LLM provider unavailable' } })
    render(<TestChatPanel page={PAGE} />)

    await userEvent.type(screen.getByLabelText(/test message/i), 'Hoc phi?')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('LLM provider unavailable')
  })
})
```

Create `frontend/src/pages/tabs/InstructionsTab.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../../lib/types'
import InstructionsTab from './InstructionsTab'

const PAGE: PageSummary = {
  id: 7,
  fb_page_id: '1',
  name: 'Hateco',
  system_prompt: 'Ban la tu van vien.',
  closing_message: 'Goi hotline 0123 456 789 de duoc tu van them nhe!',
  llm_model: 'google/gemini-2.5-flash',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 1,
  created_at: '2026-09-18T00:00:00Z',
}

function mockApi(status = 200, body: unknown = PAGE) {
  const spy = vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  }))
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('InstructionsTab', () => {
  it('pre-fills the current instructions', () => {
    mockApi()
    render(<InstructionsTab page={PAGE} reloadPage={async () => {}} />)

    expect(screen.getByLabelText(/instructions/i)).toHaveValue('Ban la tu van vien.')
    expect(screen.getByLabelText(/closing message/i)).toHaveValue(
      'Goi hotline 0123 456 789 de duoc tu van them nhe!',
    )
    expect(screen.getByLabelText(/model/i)).toHaveValue('google/gemini-2.5-flash')
  })

  it('saves the edited instructions', async () => {
    const spy = mockApi()
    const reloadPage = vi.fn(async () => {})
    render(<InstructionsTab page={PAGE} reloadPage={reloadPage} />)

    await userEvent.clear(screen.getByLabelText(/instructions/i))
    await userEvent.type(screen.getByLabelText(/instructions/i), 'Ban la tro ly moi.')
    await userEvent.click(screen.getByRole('button', { name: /save instructions/i }))

    await waitFor(() => expect(reloadPage).toHaveBeenCalled())
    const body = JSON.parse(spy.mock.calls[0][1].body as string)
    expect(body.system_prompt).toBe('Ban la tro ly moi.')
  })

  it('saves the edited closing message', async () => {
    const spy = mockApi()
    render(<InstructionsTab page={PAGE} reloadPage={async () => {}} />)

    await userEvent.clear(screen.getByLabelText(/closing message/i))
    await userEvent.type(
      screen.getByLabelText(/closing message/i),
      'Lien he hotline 0987 654 321 nhe!',
    )
    await userEvent.click(screen.getByRole('button', { name: /save instructions/i }))

    await waitFor(() => {
      const body = JSON.parse(spy.mock.calls[0][1].body as string)
      expect(body.closing_message).toBe('Lien he hotline 0987 654 321 nhe!')
    })
  })

  it('confirms a successful save', async () => {
    mockApi()
    render(<InstructionsTab page={PAGE} reloadPage={async () => {}} />)

    await userEvent.click(screen.getByRole('button', { name: /save instructions/i }))

    expect(await screen.findByText(/saved/i)).toBeInTheDocument()
  })

  it('shows the server error when saving fails', async () => {
    mockApi(403, { detail: "Requires page role 'owner'" })
    render(<InstructionsTab page={PAGE} reloadPage={async () => {}} />)

    await userEvent.click(screen.getByRole('button', { name: /save instructions/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent("Requires page role 'owner'")
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/components/TestChatPanel.test.tsx src/pages/tabs/InstructionsTab.test.tsx
```

Expected: both fail to resolve their imports.

- [ ] **Step 3: Write `frontend/src/components/TestChatPanel.tsx`**

```tsx
import { useState, type FormEvent } from 'react'

import { apiFetch } from '../lib/api'
import type { PageSummary } from '../lib/types'

interface TestChatResult {
  answer: string
  context: string[]
}

export default function TestChatPanel({ page }: { page: PageSummary }) {
  const [message, setMessage] = useState('')
  const [result, setResult] = useState<TestChatResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function send(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      setResult(
        await apiFetch<TestChatResult>(`/api/pages/${page.id}/test-chat`, {
          method: 'POST',
          body: JSON.stringify({ message }),
        }),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not generate an answer')
      setResult(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
      <div>
        <h2 className="text-sm font-medium">Test chat</h2>
        <p className="text-xs text-slate-500">
          Answers exactly as this page would. Nothing is sent to Facebook and nothing is
          logged as a conversation.
        </p>
      </div>

      <form onSubmit={send} className="space-y-2">
        <label htmlFor="test-message" className="block text-sm font-medium">
          Test message
        </label>
        <textarea
          id="test-message"
          required
          rows={3}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {busy ? 'Sending…' : 'Send'}
        </button>
      </form>

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {result && (
        <div className="space-y-3">
          <div className="rounded-md bg-slate-100 p-3">
            <p className="text-xs font-medium text-slate-500">Answer</p>
            <p className="mt-1 whitespace-pre-wrap text-sm">{result.answer}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Retrieved context</p>
            <ul className="mt-1 space-y-1">
              {result.context.map((chunk, index) => (
                <li
                  key={index}
                  className="whitespace-pre-wrap rounded-md border border-slate-200 p-2 text-xs text-slate-600"
                >
                  {chunk}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Write `frontend/src/pages/tabs/InstructionsTab.tsx`**

```tsx
import { useState, type FormEvent } from 'react'

import TestChatPanel from '../../components/TestChatPanel'
import { apiFetch } from '../../lib/api'
import type { PageSummary } from '../../lib/types'

export default function InstructionsTab({
  page,
  reloadPage,
}: {
  page: PageSummary
  reloadPage: () => Promise<void>
}) {
  const [systemPrompt, setSystemPrompt] = useState(page.system_prompt)
  const [closingMessage, setClosingMessage] = useState(page.closing_message)
  const [llmModel, setLlmModel] = useState(page.llm_model)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  async function save(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSaved(false)
    setBusy(true)
    try {
      await apiFetch(`/api/pages/${page.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          system_prompt: systemPrompt,
          closing_message: closingMessage,
          llm_model: llmModel,
        }),
      })
      setSaved(true)
      await reloadPage()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save the instructions')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <form
        onSubmit={save}
        className="space-y-3 rounded-xl border border-slate-200 bg-white p-5"
      >
        <div className="space-y-1">
          <label htmlFor="system-prompt" className="block text-sm font-medium">
            Instructions
          </label>
          <p className="text-xs text-slate-500">
            How this page should answer: tone, persona, rules. Leave empty to use the
            default admissions counsellor persona.
          </p>
          <textarea
            id="system-prompt"
            rows={12}
            value={systemPrompt}
            onChange={(event) => setSystemPrompt(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="llm-model" className="block text-sm font-medium">
            Model override
          </label>
          <input
            id="llm-model"
            value={llmModel}
            onChange={(event) => setLlmModel(event.target.value)}
            placeholder="google/gemini-2.5-flash"
            className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm"
          />
          <p className="text-xs text-slate-500">
            An OpenRouter model id. Leave empty to use the server default.
          </p>
        </div>

        <div className="space-y-1">
          <label htmlFor="closing-message" className="block text-sm font-medium">
            Closing message
          </label>
          <p className="text-xs text-slate-500">
            Appended after every answer to hand the student off to a human — a hotline
            number or "gọi cho trường để được tư vấn thêm nhé!". Leave empty to append
            nothing.
          </p>
          <textarea
            id="closing-message"
            rows={2}
            value={closingMessage}
            onChange={(event) => setClosingMessage(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        {error && (
          <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        {saved && <p className="text-sm text-emerald-700">Saved.</p>}

        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Save instructions
        </button>
      </form>

      <TestChatPanel page={page} />
    </div>
  )
}
```

- [ ] **Step 5: Wire the tab into `frontend/src/pages/PageDetailPage.tsx`**

Add the import:

```tsx
import InstructionsTab from './tabs/InstructionsTab'
```

Extend `TABS`:

```tsx
const TABS: TabDefinition[] = [
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'instructions', label: 'Instructions' },
]
```

and render it below the knowledge line:

```tsx
      {active === 'instructions' && (
        <InstructionsTab page={page} reloadPage={reloadPage} />
      )}
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
cd frontend && npm test -- --run
```

Expected: 30 passed.

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "feat: add per-page instructions editor and console test chat"
```

---

## Task 22: Conversations tab

**Files:**
- Create: `frontend/src/pages/tabs/ConversationsTab.tsx`
- Modify: `frontend/src/pages/PageDetailPage.tsx` (add the Conversations tab)
- Test: `frontend/src/pages/tabs/ConversationsTab.test.tsx`

**Interfaces:**
- Consumes: `apiFetch`, `PageSummary`, `ConversationSummary`, `ConversationDetail`, `GET /api/pages/{id}/conversations`, `GET /api/pages/{id}/conversations/{cid}`.
- Produces: `pages/tabs/ConversationsTab.tsx` — default-exported `ConversationsTab({ page }: { page: PageSummary })`. Master/detail: a searchable list on the left, the selected transcript on the right.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/tabs/ConversationsTab.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../../lib/types'
import ConversationsTab from './ConversationsTab'

const PAGE: PageSummary = {
  id: 7,
  fb_page_id: '1',
  name: 'Hateco',
  system_prompt: '',
  closing_message: '',
  llm_model: '',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 1,
  created_at: '2026-09-18T00:00:00Z',
}

const SUMMARY = {
  id: 11,
  psid: 'psid-a',
  started_at: '2026-09-18T00:00:00Z',
  last_message_at: '2026-09-18T01:00:00Z',
  message_count: 2,
  last_message_preview: '15 trieu em nhe',
}

const DETAIL = {
  id: 11,
  psid: 'psid-a',
  started_at: '2026-09-18T00:00:00Z',
  last_message_at: '2026-09-18T01:00:00Z',
  messages: [
    {
      id: 1,
      direction: 'in',
      text: 'Hoc phi bao nhieu?',
      attachments: [],
      created_at: '2026-09-18T00:00:00Z',
    },
    {
      id: 2,
      direction: 'out',
      text: '15 trieu em nhe',
      attachments: [],
      created_at: '2026-09-18T01:00:00Z',
    },
  ],
}

function mockApi(handler: (path: string) => { status: number; body: unknown }) {
  const spy = vi.fn(async (url: string) => {
    const route = handler(url.replace('http://localhost:8000', ''))
    return {
      ok: route.status >= 200 && route.status < 300,
      status: route.status,
      text: async () => JSON.stringify(route.body),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

const standardApi = (path: string) =>
  path.includes('/conversations/')
    ? { status: 200, body: DETAIL }
    : { status: 200, body: [SUMMARY] }

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ConversationsTab', () => {
  it('lists conversations with their preview', async () => {
    mockApi(standardApi)
    render(<ConversationsTab page={PAGE} />)

    expect(await screen.findByText('psid-a')).toBeInTheDocument()
    expect(screen.getByText('15 trieu em nhe')).toBeInTheDocument()
  })

  it('opens the transcript when a conversation is clicked', async () => {
    mockApi(standardApi)
    render(<ConversationsTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /psid-a/ }))

    expect(await screen.findByText('Hoc phi bao nhieu?')).toBeInTheDocument()
  })

  it('sends the search term to the API', async () => {
    const spy = mockApi(standardApi)
    render(<ConversationsTab page={PAGE} />)
    await screen.findByText('psid-a')

    await userEvent.type(screen.getByLabelText(/search/i), 'hoc phi')
    await userEvent.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() =>
      expect(
        spy.mock.calls.some(([url]) => String(url).includes('q=hoc+phi')),
      ).toBe(true),
    )
  })

  it('shows an empty state when nothing matches', async () => {
    mockApi(() => ({ status: 200, body: [] }))
    render(<ConversationsTab page={PAGE} />)

    expect(await screen.findByText(/no conversations/i)).toBeInTheDocument()
  })

  it('distinguishes inbound from outbound messages', async () => {
    mockApi(standardApi)
    render(<ConversationsTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /psid-a/ }))
    const inbound = await screen.findByText('Hoc phi bao nhieu?')
    const outbound = screen.getByText('15 trieu em nhe', { selector: 'p' })

    expect(inbound.closest('li')).toHaveAttribute('data-direction', 'in')
    expect(outbound.closest('li')).toHaveAttribute('data-direction', 'out')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/pages/tabs/ConversationsTab.test.tsx
```

Expected: `Failed to resolve import "./ConversationsTab"`.

- [ ] **Step 3: Write `frontend/src/pages/tabs/ConversationsTab.tsx`**

```tsx
import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { apiFetch } from '../../lib/api'
import type { ConversationDetail, ConversationSummary, PageSummary } from '../../lib/types'

function formatTime(value: string): string {
  return new Date(value).toLocaleString()
}

export default function ConversationsTab({ page }: { page: PageSummary }) {
  const [summaries, setSummaries] = useState<ConversationSummary[]>([])
  const [detail, setDetail] = useState<ConversationDetail | null>(null)
  const [query, setQuery] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (appliedQuery.trim()) params.set('q', appliedQuery.trim())
      const suffix = params.toString() ? `?${params}` : ''
      setSummaries(
        await apiFetch<ConversationSummary[]>(
          `/api/pages/${page.id}/conversations${suffix}`,
        ),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load conversations')
    } finally {
      setLoading(false)
    }
  }, [page.id, appliedQuery])

  useEffect(() => {
    void reload()
  }, [reload])

  async function open(conversationId: number) {
    setError('')
    try {
      setDetail(
        await apiFetch<ConversationDetail>(
          `/api/pages/${page.id}/conversations/${conversationId}`,
        ),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load the transcript')
    }
  }

  function search(event: FormEvent) {
    event.preventDefault()
    setAppliedQuery(query)
  }

  return (
    <div className="space-y-4">
      <form onSubmit={search} className="flex items-end gap-2">
        <div className="flex-1 space-y-1">
          <label htmlFor="conversation-search" className="block text-sm font-medium">
            Search
          </label>
          <input
            id="conversation-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Message text or PSID"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
        >
          Search
        </button>
      </form>

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <div>
          {loading ? (
            <p className="text-sm text-slate-500">Loading…</p>
          ) : summaries.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
              No conversations found.
            </p>
          ) : (
            <ul className="space-y-2">
              {summaries.map((summary) => (
                <li key={summary.id}>
                  <button
                    type="button"
                    onClick={() => open(summary.id)}
                    className={`w-full rounded-xl border bg-white p-4 text-left ${
                      detail?.id === summary.id
                        ? 'border-slate-900'
                        : 'border-slate-200 hover:border-slate-400'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs">{summary.psid}</span>
                      <span className="text-xs text-slate-500">
                        {summary.message_count} msgs
                      </span>
                    </div>
                    <p className="mt-1 truncate text-sm text-slate-600">
                      {summary.last_message_preview}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {formatTime(summary.last_message_at)}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          {detail === null ? (
            <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
              Select a conversation to read the transcript.
            </p>
          ) : (
            <ul className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
              {detail.messages.map((message) => (
                <li
                  key={message.id}
                  data-direction={message.direction}
                  className={
                    message.direction === 'in'
                      ? 'mr-8 rounded-lg bg-slate-100 p-3'
                      : 'ml-8 rounded-lg bg-slate-900 p-3 text-white'
                  }
                >
                  <p className="whitespace-pre-wrap text-sm">{message.text}</p>
                  {message.attachments.length > 0 && (
                    <p className="mt-1 text-xs opacity-70">
                      {message.attachments.length} attachment(s)
                    </p>
                  )}
                  <p className="mt-1 text-xs opacity-60">{formatTime(message.created_at)}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Wire the tab into `frontend/src/pages/PageDetailPage.tsx`**

Add the import:

```tsx
import ConversationsTab from './tabs/ConversationsTab'
```

Extend `TABS`:

```tsx
const TABS: TabDefinition[] = [
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'instructions', label: 'Instructions' },
  { id: 'conversations', label: 'Conversations' },
]
```

and render it:

```tsx
      {active === 'conversations' && <ConversationsTab page={page} />}
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd frontend && npm test -- --run
```

Expected: 35 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat: add conversation browser with search and transcripts"
```

---

## Task 23: Learning tab — the review queue

**Files:**
- Create: `frontend/src/pages/tabs/LearningTab.tsx`
- Modify: `frontend/src/pages/PageDetailPage.tsx` (add the Learning tab)
- Test: `frontend/src/pages/tabs/LearningTab.test.tsx`

**Interfaces:**
- Consumes: `apiFetch`, `PageSummary`, `Suggestion`, `POST /api/pages/{id}/learning/mine`, `GET /api/pages/{id}/suggestions?status=`, `POST /api/pages/{id}/suggestions/{sid}/approve`, `POST /api/pages/{id}/suggestions/{sid}/reject`.
- Produces: `pages/tabs/LearningTab.tsx` — default-exported `LearningTab({ page }: { page: PageSummary })`. This is the human gate described in spec §4.5: mine on demand, review each draft, edit before approving, approve or reject.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/tabs/LearningTab.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../../lib/types'
import LearningTab from './LearningTab'

const PAGE: PageSummary = {
  id: 7,
  fb_page_id: '1',
  name: 'Hateco',
  system_prompt: '',
  closing_message: '',
  llm_model: '',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 1,
  created_at: '2026-09-18T00:00:00Z',
}

const SUGGESTION = {
  id: 21,
  page_id: 7,
  question: 'Hoc phi bao nhieu?',
  answer: '15 trieu moi ky.',
  occurrences: 14,
  status: 'pending' as const,
  created_at: '2026-09-18T00:00:00Z',
  reviewed_at: null,
  knowledge_item_id: null,
}

function mockApi(
  handler: (path: string, init?: RequestInit) => { status: number; body: unknown },
) {
  const spy = vi.fn(async (url: string, init?: RequestInit) => {
    const route = handler(url.replace('http://localhost:8000', ''), init)
    return {
      ok: route.status >= 200 && route.status < 300,
      status: route.status,
      text: async () => JSON.stringify(route.body),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('LearningTab', () => {
  it('lists pending suggestions with their occurrence count', async () => {
    mockApi(() => ({ status: 200, body: [SUGGESTION] }))
    render(<LearningTab page={PAGE} />)

    expect(await screen.findByText('Hoc phi bao nhieu?')).toBeInTheDocument()
    expect(screen.getByText(/seen 14/i)).toBeInTheDocument()
  })

  it('shows an empty state when the queue is clear', async () => {
    mockApi(() => ({ status: 200, body: [] }))
    render(<LearningTab page={PAGE} />)

    expect(await screen.findByText(/nothing to review/i)).toBeInTheDocument()
  })

  it('mines conversations and shows the new drafts', async () => {
    let mined = false
    mockApi((path) => {
      if (path.includes('/learning/mine')) {
        mined = true
        return { status: 200, body: { created: 1, suggestions: [SUGGESTION] } }
      }
      return { status: 200, body: mined ? [SUGGESTION] : [] }
    })
    render(<LearningTab page={PAGE} />)

    await userEvent.click(
      await screen.findByRole('button', { name: /mine conversations/i }),
    )

    expect(await screen.findByText('Hoc phi bao nhieu?')).toBeInTheDocument()
  })

  it('reports when mining finds nothing new', async () => {
    mockApi((path) =>
      path.includes('/learning/mine')
        ? { status: 200, body: { created: 0, suggestions: [] } }
        : { status: 200, body: [] },
    )
    render(<LearningTab page={PAGE} />)

    await userEvent.click(
      await screen.findByRole('button', { name: /mine conversations/i }),
    )

    expect(await screen.findByText(/no new suggestions/i)).toBeInTheDocument()
  })

  it('approves a suggestion and removes it from the queue', async () => {
    let pending = [SUGGESTION]
    const spy = mockApi((path) => {
      if (path.includes('/approve')) {
        pending = []
        return { status: 200, body: { ...SUGGESTION, status: 'approved' } }
      }
      return { status: 200, body: pending }
    })
    render(<LearningTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /^approve$/i }))

    await waitFor(() =>
      expect(screen.queryByText('Hoc phi bao nhieu?')).not.toBeInTheDocument(),
    )
    expect(
      spy.mock.calls.some(([url]) =>
        String(url).includes('/api/pages/7/suggestions/21/approve'),
      ),
    ).toBe(true)
  })

  it('sends the edited answer when approving after an edit', async () => {
    const spy = mockApi((path) =>
      path.includes('/approve')
        ? { status: 200, body: { ...SUGGESTION, status: 'approved' } }
        : { status: 200, body: [SUGGESTION] },
    )
    render(<LearningTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /^edit$/i }))
    const answerBox = screen.getByLabelText(/answer/i)
    await userEvent.clear(answerBox)
    await userEvent.type(answerBox, '20 trieu moi ky.')
    await userEvent.click(screen.getByRole('button', { name: /approve with edits/i }))

    await waitFor(() => {
      const approveCall = spy.mock.calls.find(([url]) =>
        String(url).includes('/approve'),
      )
      expect(JSON.parse(approveCall![1].body as string).answer).toBe('20 trieu moi ky.')
    })
  })

  it('rejects a suggestion', async () => {
    let pending = [SUGGESTION]
    const spy = mockApi((path) => {
      if (path.includes('/reject')) {
        pending = []
        return { status: 200, body: { ...SUGGESTION, status: 'rejected' } }
      }
      return { status: 200, body: pending }
    })
    render(<LearningTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /^reject$/i }))

    await waitFor(() =>
      expect(
        spy.mock.calls.some(([url]) => String(url).includes('/reject')),
      ).toBe(true),
    )
  })

  it('shows the server error when mining fails', async () => {
    mockApi((path) =>
      path.includes('/learning/mine')
        ? { status: 403, body: { detail: "Requires page role 'editor'" } }
        : { status: 200, body: [] },
    )
    render(<LearningTab page={PAGE} />)

    await userEvent.click(
      await screen.findByRole('button', { name: /mine conversations/i }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent("Requires page role 'editor'")
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/pages/tabs/LearningTab.test.tsx
```

Expected: `Failed to resolve import "./LearningTab"`.

- [ ] **Step 3: Write `frontend/src/pages/tabs/LearningTab.tsx`**

```tsx
import { useCallback, useEffect, useState } from 'react'

import { apiFetch } from '../../lib/api'
import type { PageSummary, Suggestion } from '../../lib/types'

interface MineResult {
  created: number
  suggestions: Suggestion[]
}

export default function LearningTab({ page }: { page: PageSummary }) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [mining, setMining] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [draftQuestion, setDraftQuestion] = useState('')
  const [draftAnswer, setDraftAnswer] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setSuggestions(
        await apiFetch<Suggestion[]>(`/api/pages/${page.id}/suggestions?status=pending`),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load suggestions')
    } finally {
      setLoading(false)
    }
  }, [page.id])

  useEffect(() => {
    void reload()
  }, [reload])

  async function mine() {
    setError('')
    setNotice('')
    setMining(true)
    try {
      const result = await apiFetch<MineResult>(`/api/pages/${page.id}/learning/mine`, {
        method: 'POST',
      })
      setNotice(
        result.created === 0
          ? 'No new suggestions — everything recurring is already covered.'
          : `${result.created} new suggestion(s) ready for review.`,
      )
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Mining failed')
    } finally {
      setMining(false)
    }
  }

  function startEdit(suggestion: Suggestion) {
    setEditingId(suggestion.id)
    setDraftQuestion(suggestion.question)
    setDraftAnswer(suggestion.answer)
  }

  async function approve(suggestion: Suggestion, withEdits: boolean) {
    setError('')
    setNotice('')
    try {
      await apiFetch(`/api/pages/${page.id}/suggestions/${suggestion.id}/approve`, {
        method: 'POST',
        body: JSON.stringify(
          withEdits ? { title: draftQuestion, answer: draftAnswer } : {},
        ),
      })
      setEditingId(null)
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not approve')
    }
  }

  async function reject(suggestion: Suggestion) {
    setError('')
    setNotice('')
    try {
      await apiFetch(`/api/pages/${page.id}/suggestions/${suggestion.id}/reject`, {
        method: 'POST',
      })
      setEditingId(null)
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not reject')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm text-slate-500">
          Mining reads this page's past messages and drafts answers for the questions that
          keep coming back. Nothing reaches the knowledge base until you approve it.
        </p>
        <button
          type="button"
          onClick={mine}
          disabled={mining}
          className="shrink-0 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {mining ? 'Mining…' : 'Mine conversations'}
        </button>
      </div>

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {notice && (
        <p className="rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700">{notice}</p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : suggestions.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          Nothing to review. Run mining after the page has collected some conversations.
        </p>
      ) : (
        <ul className="space-y-3">
          {suggestions.map((suggestion) => (
            <li
              key={suggestion.id}
              className="space-y-3 rounded-xl border border-slate-200 bg-white p-5"
            >
              {editingId === suggestion.id ? (
                <div className="space-y-3">
                  <div className="space-y-1">
                    <label
                      htmlFor={`question-${suggestion.id}`}
                      className="block text-sm font-medium"
                    >
                      Question
                    </label>
                    <input
                      id={`question-${suggestion.id}`}
                      value={draftQuestion}
                      onChange={(event) => setDraftQuestion(event.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div className="space-y-1">
                    <label
                      htmlFor={`answer-${suggestion.id}`}
                      className="block text-sm font-medium"
                    >
                      Answer
                    </label>
                    <textarea
                      id={`answer-${suggestion.id}`}
                      rows={5}
                      value={draftAnswer}
                      onChange={(event) => setDraftAnswer(event.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => approve(suggestion, true)}
                      className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white"
                    >
                      Approve with edits
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingId(null)}
                      className="rounded-md border border-slate-300 px-3 py-2 text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between gap-4">
                    <p className="font-medium">{suggestion.question}</p>
                    <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                      seen {suggestion.occurrences}×
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm text-slate-600">
                    {suggestion.answer}
                  </p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => approve(suggestion, false)}
                      className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => startEdit(suggestion)}
                      className="rounded-md border border-slate-300 px-3 py-2 text-sm"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => reject(suggestion)}
                      className="rounded-md border border-red-300 px-3 py-2 text-sm text-red-700"
                    >
                      Reject
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Wire the tab into `frontend/src/pages/PageDetailPage.tsx`**

Add the import:

```tsx
import LearningTab from './tabs/LearningTab'
```

Extend `TABS`:

```tsx
const TABS: TabDefinition[] = [
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'instructions', label: 'Instructions' },
  { id: 'conversations', label: 'Conversations' },
  { id: 'learning', label: 'Learning' },
]
```

and render it:

```tsx
      {active === 'learning' && <LearningTab page={page} />}
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd frontend && npm test -- --run
```

Expected: 43 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat: add the learning review queue with mine, edit, approve and reject"
```

---

## Task 24: Members tab and user administration

**Files:**
- Create: `frontend/src/pages/tabs/MembersTab.tsx`
- Create: `frontend/src/pages/UsersPage.tsx`
- Modify: `frontend/src/pages/PageDetailPage.tsx` (add the Members tab)
- Modify: `frontend/src/App.tsx` (add the `/users` route)
- Test: `frontend/src/pages/tabs/MembersTab.test.tsx`
- Test: `frontend/src/pages/UsersPage.test.tsx`

**Interfaces:**
- Consumes: `apiFetch`, `PageSummary`, `Member`, `User`, `GET/PUT/DELETE /api/pages/{id}/members`, `GET/POST/DELETE /api/users`.
- Produces:
  - `pages/tabs/MembersTab.tsx` — default-exported `MembersTab({ page }: { page: PageSummary })`.
  - `pages/UsersPage.tsx` — default-exported `UsersPage`.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/pages/tabs/MembersTab.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../../lib/types'
import MembersTab from './MembersTab'

const PAGE: PageSummary = {
  id: 7,
  fb_page_id: '1',
  name: 'Hateco',
  system_prompt: '',
  closing_message: '',
  llm_model: '',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 1,
  created_at: '2026-09-18T00:00:00Z',
}

const MEMBER = { user_id: 2, email: 'editor@hateco.vn', role: 'editor' }
const USERS = [
  { id: 1, email: 'boss@hateco.vn', role: 'admin', is_active: true },
  { id: 2, email: 'editor@hateco.vn', role: 'member', is_active: true },
]

function mockApi(
  handler: (path: string, init?: RequestInit) => { status: number; body: unknown },
) {
  const spy = vi.fn(async (url: string, init?: RequestInit) => {
    const route = handler(url.replace('http://localhost:8000', ''), init)
    return {
      ok: route.status >= 200 && route.status < 300,
      status: route.status,
      text: async () => (route.status === 204 ? '' : JSON.stringify(route.body)),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

const standardApi = (path: string) =>
  path.startsWith('/api/users')
    ? { status: 200, body: USERS }
    : { status: 200, body: [MEMBER] }

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('MembersTab', () => {
  it('lists the current members with their role', async () => {
    mockApi(standardApi)
    render(<MembersTab page={PAGE} />)

    expect(await screen.findByText('editor@hateco.vn')).toBeInTheDocument()
    expect(screen.getByDisplayValue('editor')).toBeInTheDocument()
  })

  it('adds a member with the chosen role', async () => {
    const spy = mockApi(standardApi)
    render(<MembersTab page={PAGE} />)
    await screen.findByText('editor@hateco.vn')

    await userEvent.selectOptions(screen.getByLabelText(/add user/i), '1')
    await userEvent.selectOptions(screen.getByLabelText(/new member role/i), 'viewer')
    await userEvent.click(screen.getByRole('button', { name: /^add$/i }))

    await waitFor(() => {
      const put = spy.mock.calls.find(([, init]) => (init as RequestInit)?.method === 'PUT')
      expect(JSON.parse(put![1].body as string)).toEqual({ user_id: 1, role: 'viewer' })
    })
  })

  it('changes an existing member role', async () => {
    const spy = mockApi(standardApi)
    render(<MembersTab page={PAGE} />)

    await userEvent.selectOptions(await screen.findByDisplayValue('editor'), 'owner')

    await waitFor(() => {
      const put = spy.mock.calls.find(([, init]) => (init as RequestInit)?.method === 'PUT')
      expect(JSON.parse(put![1].body as string)).toEqual({ user_id: 2, role: 'owner' })
    })
  })

  it('removes a member', async () => {
    const spy = mockApi(standardApi)
    render(<MembersTab page={PAGE} />)

    await userEvent.click(await screen.findByRole('button', { name: /remove/i }))

    await waitFor(() =>
      expect(
        spy.mock.calls.some(
          ([url, init]) =>
            String(url).includes('/members/2') &&
            (init as RequestInit)?.method === 'DELETE',
        ),
      ).toBe(true),
    )
  })

  it('shows the server error when the change is refused', async () => {
    mockApi((path, init) =>
      init?.method === 'PUT'
        ? { status: 403, body: { detail: "Requires page role 'owner'" } }
        : standardApi(path),
    )
    render(<MembersTab page={PAGE} />)

    await userEvent.selectOptions(await screen.findByDisplayValue('editor'), 'viewer')

    expect(await screen.findByRole('alert')).toHaveTextContent("Requires page role 'owner'")
  })
})
```

Create `frontend/src/pages/UsersPage.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import UsersPage from './UsersPage'

const USERS = [
  { id: 1, email: 'boss@hateco.vn', role: 'admin', is_active: true },
  { id: 2, email: 'editor@hateco.vn', role: 'member', is_active: true },
]

function mockApi(
  handler: (path: string, init?: RequestInit) => { status: number; body: unknown },
) {
  const spy = vi.fn(async (url: string, init?: RequestInit) => {
    const route = handler(url.replace('http://localhost:8000', ''), init)
    return {
      ok: route.status >= 200 && route.status < 300,
      status: route.status,
      text: async () => JSON.stringify(route.body),
    }
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('UsersPage', () => {
  it('lists the users', async () => {
    mockApi(() => ({ status: 200, body: USERS }))
    render(<UsersPage />)

    expect(await screen.findByText('boss@hateco.vn')).toBeInTheDocument()
    expect(screen.getByText('editor@hateco.vn')).toBeInTheDocument()
  })

  it('creates a user', async () => {
    const spy = mockApi((_path, init) =>
      init?.method === 'POST'
        ? { status: 201, body: USERS[1] }
        : { status: 200, body: USERS },
    )
    render(<UsersPage />)
    await screen.findByText('boss@hateco.vn')

    await userEvent.type(screen.getByLabelText(/^email$/i), 'new@hateco.vn')
    await userEvent.type(screen.getByLabelText(/^password$/i), 'another-pass-1')
    await userEvent.click(screen.getByRole('button', { name: /create user/i }))

    await waitFor(() => {
      const post = spy.mock.calls.find(([, init]) => (init as RequestInit)?.method === 'POST')
      expect(JSON.parse(post![1].body as string)).toEqual({
        email: 'new@hateco.vn',
        password: 'another-pass-1',
        role: 'member',
      })
    })
  })

  it('shows the server error when the email is taken', async () => {
    mockApi((_path, init) =>
      init?.method === 'POST'
        ? { status: 409, body: { detail: 'Email already registered' } }
        : { status: 200, body: USERS },
    )
    render(<UsersPage />)
    await screen.findByText('boss@hateco.vn')

    await userEvent.type(screen.getByLabelText(/^email$/i), 'boss@hateco.vn')
    await userEvent.type(screen.getByLabelText(/^password$/i), 'another-pass-1')
    await userEvent.click(screen.getByRole('button', { name: /create user/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Email already registered')
  })

  it('deactivates a user', async () => {
    const spy = mockApi((_path, init) =>
      init?.method === 'DELETE'
        ? { status: 200, body: { ...USERS[1], is_active: false } }
        : { status: 200, body: USERS },
    )
    render(<UsersPage />)

    const rows = await screen.findAllByRole('button', { name: /deactivate/i })
    await userEvent.click(rows[0])

    await waitFor(() =>
      expect(
        spy.mock.calls.some(([, init]) => (init as RequestInit)?.method === 'DELETE'),
      ).toBe(true),
    )
  })

  it('marks deactivated users', async () => {
    mockApi(() => ({ status: 200, body: [{ ...USERS[1], is_active: false }] }))
    render(<UsersPage />)

    expect(await screen.findByText(/deactivated/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/pages/tabs/MembersTab.test.tsx src/pages/UsersPage.test.tsx
```

Expected: both fail to resolve their imports.

- [ ] **Step 3: Write `frontend/src/pages/tabs/MembersTab.tsx`**

```tsx
import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { apiFetch } from '../../lib/api'
import type { Member, PageSummary, User } from '../../lib/types'

const ROLES = ['viewer', 'editor', 'owner'] as const

export default function MembersTab({ page }: { page: PageSummary }) {
  const [members, setMembers] = useState<Member[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [selectedUserId, setSelectedUserId] = useState('')
  const [newRole, setNewRole] = useState<string>('viewer')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setMembers(await apiFetch<Member[]>(`/api/pages/${page.id}/members`))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load members')
    } finally {
      setLoading(false)
    }
  }, [page.id])

  useEffect(() => {
    void reload()
    // Only admins may list users; members simply get no picker.
    apiFetch<User[]>('/api/users')
      .then(setUsers)
      .catch(() => setUsers([]))
  }, [reload])

  async function setRole(userId: number, role: string) {
    setError('')
    try {
      await apiFetch(`/api/pages/${page.id}/members`, {
        method: 'PUT',
        body: JSON.stringify({ user_id: userId, role }),
      })
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not update the member')
    }
  }

  async function add(event: FormEvent) {
    event.preventDefault()
    if (!selectedUserId) return
    await setRole(Number(selectedUserId), newRole)
    setSelectedUserId('')
  }

  async function remove(userId: number) {
    setError('')
    try {
      await apiFetch(`/api/pages/${page.id}/members/${userId}`, { method: 'DELETE' })
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not remove the member')
    }
  }

  const candidates = users.filter(
    (user) => !members.some((member) => member.user_id === user.id),
  )

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        Viewers read. Editors change knowledge, instructions and the review queue. Owners
        also manage page settings and members.
      </p>

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <form
        onSubmit={add}
        className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-5"
      >
        <div className="space-y-1">
          <label htmlFor="add-user" className="block text-sm font-medium">
            Add user
          </label>
          <select
            id="add-user"
            value={selectedUserId}
            onChange={(event) => setSelectedUserId(event.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Select a user…</option>
            {candidates.map((user) => (
              <option key={user.id} value={user.id}>
                {user.email}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="new-member-role" className="block text-sm font-medium">
            New member role
          </label>
          <select
            id="new-member-role"
            value={newRole}
            onChange={(event) => setNewRole(event.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            {ROLES.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
        >
          Add
        </button>
      </form>

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : (
        <ul className="space-y-2">
          {members.map((member) => (
            <li
              key={member.user_id}
              className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4"
            >
              <span className="text-sm">{member.email}</span>
              <div className="flex items-center gap-2">
                <label className="sr-only" htmlFor={`role-${member.user_id}`}>
                  Role for {member.email}
                </label>
                <select
                  id={`role-${member.user_id}`}
                  value={member.role}
                  onChange={(event) => setRole(member.user_id, event.target.value)}
                  className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                >
                  {ROLES.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => remove(member.user_id)}
                  className="rounded-md border border-red-300 px-2 py-1 text-xs text-red-700"
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Write `frontend/src/pages/UsersPage.tsx`**

```tsx
import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { apiFetch } from '../lib/api'
import type { User } from '../lib/types'

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('member')

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setUsers(await apiFetch<User[]>('/api/users'))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load users')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  async function create(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await apiFetch('/api/users', {
        method: 'POST',
        body: JSON.stringify({ email, password, role }),
      })
      setEmail('')
      setPassword('')
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not create the user')
    }
  }

  async function deactivate(user: User) {
    setError('')
    try {
      await apiFetch(`/api/users/${user.id}`, { method: 'DELETE' })
      await reload()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not deactivate the user')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Users</h1>

      <form
        onSubmit={create}
        className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-5"
      >
        <div className="space-y-1">
          <label htmlFor="user-email" className="block text-sm font-medium">
            Email
          </label>
          <input
            id="user-email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="user-password" className="block text-sm font-medium">
            Password
          </label>
          <input
            id="user-password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="user-role" className="block text-sm font-medium">
            Global role
          </label>
          <select
            id="user-role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="member">member</option>
            <option value="admin">admin</option>
          </select>
        </div>
        <button
          type="submit"
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
        >
          Create user
        </button>
      </form>

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : (
        <ul className="space-y-2">
          {users.map((user) => (
            <li
              key={user.id}
              className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4"
            >
              <div>
                <p className="text-sm">{user.email}</p>
                <p className="text-xs text-slate-500">
                  {user.role}
                  {!user.is_active && ' · deactivated'}
                </p>
              </div>
              {user.is_active && (
                <button
                  type="button"
                  onClick={() => deactivate(user)}
                  className="rounded-md border border-red-300 px-2 py-1 text-xs text-red-700"
                >
                  Deactivate
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Wire the tab and the route**

In `frontend/src/pages/PageDetailPage.tsx`, add the import:

```tsx
import MembersTab from './tabs/MembersTab'
```

Extend `TABS`:

```tsx
const TABS: TabDefinition[] = [
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'instructions', label: 'Instructions' },
  { id: 'conversations', label: 'Conversations' },
  { id: 'learning', label: 'Learning' },
  { id: 'members', label: 'Members' },
]
```

and render it:

```tsx
      {active === 'members' && <MembersTab page={page} />}
```

In `frontend/src/App.tsx`, add the import:

```tsx
import UsersPage from './pages/UsersPage'
```

and the route, after `/pages/:pageId`:

```tsx
          <Route path="/users" element={<UsersPage />} />
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
cd frontend && npm test -- --run
```

Expected: 53 passed.

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "feat: add page membership management and user administration"
```

---

## Task 25: Page settings

The bot collects no personal information (spec §6), so there is no leads view — this task
is just the page's settings: rename, rotate the access token, toggle active, delete.

**Files:**
- Create: `frontend/src/pages/tabs/SettingsTab.tsx`
- Modify: `frontend/src/pages/PageDetailPage.tsx` (add the Settings tab)
- Test: `frontend/src/pages/tabs/SettingsTab.test.tsx`

**Interfaces:**
- Consumes: `apiFetch`, `PageSummary`, `PATCH /api/pages/{id}`, `DELETE /api/pages/{id}`.
- Produces: `pages/tabs/SettingsTab.tsx` — default-exported `SettingsTab({ page, reloadPage }: { page: PageSummary; reloadPage: () => Promise<void> })`; rename, rotate the access token, toggle `is_active`, and delete the page (behind a typed confirmation, so no browser dialog is used).

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/tabs/SettingsTab.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PageSummary } from '../../lib/types'
import SettingsTab from './SettingsTab'

const PAGE: PageSummary = {
  id: 7,
  fb_page_id: '100000000000001',
  name: 'Hateco',
  system_prompt: '',
  closing_message: '',
  llm_model: '',
  is_active: true,
  has_access_token: true,
  my_role: 'owner',
  knowledge_count: 1,
  created_at: '2026-09-18T00:00:00Z',
}

function mockApi(status = 200, body: unknown = PAGE) {
  const spy = vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => (status === 204 ? '' : JSON.stringify(body)),
  }))
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('SettingsTab', () => {
  it('renames the page', async () => {
    const spy = mockApi()
    render(<SettingsTab page={PAGE} reloadPage={async () => {}} />)

    await userEvent.clear(screen.getByLabelText(/display name/i))
    await userEvent.type(screen.getByLabelText(/display name/i), 'Renamed')
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() =>
      expect(JSON.parse(spy.mock.calls[0][1].body as string).name).toBe('Renamed'),
    )
  })

  it('sends the new token only when one was typed', async () => {
    const spy = mockApi()
    render(<SettingsTab page={PAGE} reloadPage={async () => {}} />)

    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    const body = JSON.parse(spy.mock.calls[0][1].body as string)
    expect(body).not.toHaveProperty('access_token')
  })

  it('rotates the access token when one is typed', async () => {
    const spy = mockApi()
    render(<SettingsTab page={PAGE} reloadPage={async () => {}} />)

    await userEvent.type(screen.getByLabelText(/new page access token/i), 'EAAG-new')
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() =>
      expect(JSON.parse(spy.mock.calls[0][1].body as string).access_token).toBe('EAAG-new'),
    )
  })

  it('toggles the active flag', async () => {
    const spy = mockApi()
    render(<SettingsTab page={PAGE} reloadPage={async () => {}} />)

    await userEvent.click(screen.getByLabelText(/page is active/i))
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() =>
      expect(JSON.parse(spy.mock.calls[0][1].body as string).is_active).toBe(false),
    )
  })

  it('only enables delete after the page id is typed', async () => {
    mockApi(204, null)
    render(<SettingsTab page={PAGE} reloadPage={async () => {}} />)

    const deleteButton = screen.getByRole('button', { name: /delete this page/i })
    expect(deleteButton).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/type the facebook page id/i), '100000000000001')

    expect(deleteButton).toBeEnabled()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/pages/tabs/SettingsTab.test.tsx
```

Expected: fails to resolve its import — `Failed to resolve import "./SettingsTab"`.

- [ ] **Step 3: Write `frontend/src/pages/tabs/SettingsTab.tsx`**

```tsx
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { apiFetch } from '../../lib/api'
import type { PageSummary } from '../../lib/types'

export default function SettingsTab({
  page,
  reloadPage,
}: {
  page: PageSummary
  reloadPage: () => Promise<void>
}) {
  const navigate = useNavigate()
  const [name, setName] = useState(page.name)
  const [accessToken, setAccessToken] = useState('')
  const [isActive, setIsActive] = useState(page.is_active)
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  async function save(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSaved(false)
    const payload: Record<string, unknown> = { name, is_active: isActive }
    if (accessToken) payload.access_token = accessToken
    try {
      await apiFetch(`/api/pages/${page.id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
      setAccessToken('')
      setSaved(true)
      await reloadPage()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save the settings')
    }
  }

  async function remove() {
    setError('')
    try {
      await apiFetch(`/api/pages/${page.id}`, { method: 'DELETE' })
      navigate('/pages')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not delete the page')
    }
  }

  return (
    <div className="space-y-6">
      <form
        onSubmit={save}
        className="space-y-3 rounded-xl border border-slate-200 bg-white p-5"
      >
        <div className="space-y-1">
          <label htmlFor="settings-name" className="block text-sm font-medium">
            Display name
          </label>
          <input
            id="settings-name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="settings-token" className="block text-sm font-medium">
            New Page Access Token
          </label>
          <input
            id="settings-token"
            type="password"
            value={accessToken}
            onChange={(event) => setAccessToken(event.target.value)}
            placeholder={page.has_access_token ? 'A token is stored' : 'No token stored'}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <p className="text-xs text-slate-500">
            Leave empty to keep the current token. Tokens are stored encrypted and never
            shown again.
          </p>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(event) => setIsActive(event.target.checked)}
          />
          Page is active
        </label>
        <p className="text-xs text-slate-500">
          An inactive page still logs incoming messages but never replies.
        </p>

        {error && (
          <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        {saved && <p className="text-sm text-emerald-700">Saved.</p>}

        <button
          type="submit"
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
        >
          Save settings
        </button>
      </form>

      <div className="space-y-3 rounded-xl border border-red-200 bg-white p-5">
        <div>
          <h2 className="text-sm font-medium text-red-700">Delete this page</h2>
          <p className="text-xs text-slate-500">
            Removes the page with its knowledge, conversations and suggestions. This
            cannot be undone.
          </p>
        </div>
        <div className="space-y-1">
          <label htmlFor="delete-confirm" className="block text-sm font-medium">
            Type the Facebook Page ID to confirm
          </label>
          <input
            id="delete-confirm"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm"
          />
        </div>
        <button
          type="button"
          onClick={remove}
          disabled={confirmation !== page.fb_page_id}
          className="rounded-md bg-red-700 px-3 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Delete this page
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Wire the tab into `frontend/src/pages/PageDetailPage.tsx`**

Add the import:

```tsx
import SettingsTab from './tabs/SettingsTab'
```

Replace `TABS` with the final list:

```tsx
const TABS: TabDefinition[] = [
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'instructions', label: 'Instructions' },
  { id: 'conversations', label: 'Conversations' },
  { id: 'learning', label: 'Learning' },
  { id: 'members', label: 'Members' },
  { id: 'settings', label: 'Settings' },
]
```

and render it:

```tsx
      {active === 'settings' && <SettingsTab page={page} reloadPage={reloadPage} />}
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd frontend && npm test -- --run
```

Expected: 58 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat: add page settings with token rotation and delete confirmation"
```

---

## Task 26: End-to-end verification

**Files:**
- Modify: `README.md` (add the smoke-test walkthrough)
- No source changes expected; fix whatever this task uncovers.

**Interfaces:**
- Consumes: everything built so far.
- Produces: a verified running system and a documented smoke test.

- [ ] **Step 1: Run the whole backend suite**

```bash
cd backend && python -m pytest -v
```

Expected: every test passes. If anything fails, fix it before continuing.

- [ ] **Step 2: Run the whole frontend suite and the type check**

```bash
cd frontend && npm test -- --run && npm run build
```

Expected: 58 tests pass and `tsc -b && vite build` completes with no errors.

- [ ] **Step 3: Start both servers**

Terminal one:

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

Terminal two:

```bash
cd frontend && npm run dev
```

- [ ] **Step 4: Walk the smoke test**

Open http://localhost:5173 and confirm each step:

1. The login screen offers **Create the first admin**. Create one. You land on Pages.
2. **Add page** with any Facebook Page ID (e.g. `100000000000001`), a name, and any
   token string. The card appears with role `owner`.
3. Open the page → **Knowledge** → **Add item**: title `Học phí`, content
   `Học phí 15 triệu mỗi kỳ.` It appears in the list.
4. **Instructions** → type a short persona, and in **Closing message** type
   `Gọi hotline 0123 456 789 để được tư vấn thêm nhé!` → **Save instructions** →
   "Saved." appears.
5. In the same tab's **Test chat**, send `Học phí bao nhiêu?`. An answer appears ending
   with the closing message, with the knowledge item listed under "Retrieved context".
   (This calls OpenRouter — it needs a valid `OPENROUTER_API_KEY`.)
6. Simulate an inbound message so there is something to mine:

   ```bash
   curl -X POST http://localhost:8000/webhook \
     -H "Content-Type: application/json" \
     -d '{"object":"page","entry":[{"id":"100000000000001","messaging":[{"sender":{"id":"psid-smoke"},"message":{"text":"Học phí bao nhiêu ạ?"}}]}]}'
   ```

   Sending to Facebook fails (the token is fake) and that is fine — the point is the log.
7. **Conversations** → the `psid-smoke` thread is listed; open it and read the transcript.
8. **Learning** → **Mine conversations** → a draft appears → **Edit** the answer →
   **Approve with edits**.
9. **Knowledge** → the approved entry is there with the `learned` badge.
10. **Members** → add a user (create one under **Users** first) as `viewer`, change the
    role to `editor`, then remove them.
11. **Settings** → uncheck **Page is active**, save, and confirm the card on the Pages
    list shows `Inactive`. Re-activate it.

- [ ] **Step 5: Confirm no token ever reaches the browser**

With the page detail screen open, in the browser devtools Network tab, inspect the
`GET /api/pages/{id}` response. It must contain `has_access_token: true` and no field
holding the token itself.

- [ ] **Step 6: Append the smoke test to `README.md`**

Add this section at the end of `README.md`:

```markdown
## Smoke test

After a fresh setup, walk these steps to confirm the whole system works:

1. Create the first admin from the login screen.
2. Add a page (Facebook Page ID, name, Page Access Token).
3. Knowledge → add an item.
4. Instructions → set the persona and closing message, save, and try the Test chat.
5. Post a fake webhook event to create a conversation:
   `curl -X POST http://localhost:8000/webhook -H "Content-Type: application/json" -d '{"object":"page","entry":[{"id":"<fb-page-id>","messaging":[{"sender":{"id":"psid-smoke"},"message":{"text":"Học phí bao nhiêu ạ?"}}]}]}'`
6. Conversations → open the transcript.
7. Learning → Mine conversations → edit → approve.
8. Knowledge → the approved entry appears with the `learned` badge.
```

- [ ] **Step 7: Commit**

```bash
git add README.md
git commit -m "docs: add the end-to-end smoke test walkthrough"
```

---

## Self-Review

**1. Spec coverage**

| Spec section | Task |
|---|---|
| §3 Users and roles | 2 (models), 3 (hashing), 4 (auth), 5 (users API), 6 (`authorize_page`), 7 (memberships), 24 (UI) |
| §4.1 Page management | 6 (CRUD, encrypted token, `has_access_token`), 19 (list/create UI), 25 (settings, rotation, deactivate, delete) |
| §4.2 Content per page | 2, 8 (index), 9 (CRUD + reindex on every mutation), 20 (UI) |
| §4.3 Instructions per page | 10 (`DEFAULT_SYSTEM_PROMPT` fallback, model override), 6 (PATCH), 12 (`closing_message` appended in `generate_answer`), 21 (UI) |
| §4.4 Conversation logging | 11 (service), 13 (webhook writes both directions), 14 (list/search/transcript), 22 (UI) |
| §4.5 Learning loop | 15 (mine, dedupe, approve, reject), 16 (API), 23 (review queue UI) |
| §4.6 Webhook | 13 (verification, routing by `entry[].id`, inactive pages, echo, typing delay; no personal-data extraction) |
| §4.7 Test chat | 16 (endpoint, no conversation logged), 21 (panel) |
| §5 Non-functional | 1 (stack, config), 2 (SQLAlchemy 2.x), 8 (FAISS rebuilt from DB), 18 (React/Vite/Tailwind v4), every task (no-network tests) |
| §6 Out of scope | No `Lead` model, no `services/leads.py`, no leads UI, no document-collection prompting anywhere in Tasks 1–26 |
| §7 Global constraints | Plan header "Global Constraints"; token secrecy asserted in Task 6 and Task 26 Step 5 |

No gaps found.

**2. Placeholder scan**

Every step carries the literal file content or the exact command to run. No "TBD",
no "add error handling", no "similar to Task N", no test written as prose.

**3. Type consistency**

- `generate_answer` returns `tuple[str, list[str]]` in Task 10 and stays that shape after
  Task 12 adds the closing-message append; it is consumed that way in Task 13
  (`answer, _context = ...`) and Task 16 (`answer, context = ...`).
- `Page.closing_message` is added in Task 2, exposed by `PageCreateIn`/`PageUpdateIn`/
  `PageOut` in Task 6, read by `generate_answer` in Task 12, and edited in
  `InstructionsTab` in Task 21 — the same field name end to end.
- `vector_store.build_index(db, page_id)` is called with the same signature in Tasks 9, 15
  and 17; `search(db, page_id, query, k)` in Tasks 10 and 15.
- `build_llm(model, temperature)` is defined in Task 10 and reused by
  `learning.build_miner` (Task 15).
- `PageOut` from Task 6 is the frontend's `PageSummary` (Task 18) field for field,
  including `closing_message`, `my_role`, `has_access_token` and `knowledge_count`.
- `SuggestionOut` (Task 16) matches the frontend `Suggestion` type (Task 18).
- Tab components all take `{ page }`, plus `reloadPage` for the two that edit page fields
  (`InstructionsTab`, `SettingsTab`).
- `clear_cache()` is defined in Task 8 and used by every test fixture that stubs
  embeddings (Tasks 9, 15, 16, 17).
- Role strings are `viewer`/`editor`/`owner` everywhere (`ROLE_ORDER`, `page_*`
  dependencies, `MembersTab.ROLES`); global roles are `admin`/`member` everywhere.
