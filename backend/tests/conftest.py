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
