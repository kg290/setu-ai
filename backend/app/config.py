import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    ocr_languages: str = os.getenv("OCR_LANGUAGES", "en,hi")
    default_language: str = os.getenv("DEFAULT_LANGUAGE", "hi")
    offline_mode: bool = os.getenv("OFFLINE_MODE", "true").lower() == "true"
    database_path: str = os.getenv("DATABASE_PATH", "app/data/setu.db")
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
