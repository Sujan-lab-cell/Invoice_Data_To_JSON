from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OCR_LANGUAGES: list[str] = ["en"]
    OCR_GPU: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
