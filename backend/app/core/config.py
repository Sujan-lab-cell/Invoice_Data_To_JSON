from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OCR_LANGUAGES: list[str] = ["en"]
    OCR_GPU: bool = False
    GEMINI_API_KEY: str | None = None

    class Config:
        env_file = Path(__file__).resolve().parent.parent.parent.parent / ".env"


settings = Settings()
