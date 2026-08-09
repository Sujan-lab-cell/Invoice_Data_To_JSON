from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OCR_LANGUAGES: list[str] = ["en"]
    OCR_GPU: bool = False
    GEMINI_API_KEY: str | None = None
    API_BEARER_TOKEN: str | None = None
    MAX_UPLOAD_SIZE_MB: int = 25
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"]
    CORS_ALLOW_CREDENTIALS: bool = True
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    class Config:
        env_file = [
            Path(__file__).resolve().parent.parent.parent.parent / ".env",
            Path.cwd() / ".env",
            ".env",
        ]
        extra = "ignore"


settings = Settings()

