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
