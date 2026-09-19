import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

class Config:
    PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "hateco_secret_verify_token_123")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-2.5-flash")
    
    # Directories
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    REPORTS_DIR = BASE_DIR / "reports"
    
    @classmethod
    def setup_directories(cls):
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.REPORTS_DIR.mkdir(exist_ok=True)

# Ensure directories exist
Config.setup_directories()
