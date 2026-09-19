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
