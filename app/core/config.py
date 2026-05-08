from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/healthcare_db"

    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Gemini AI
    GEMINI_API_KEY: str = ""

    # OTP
    OTP_EXPIRY_MINUTES: int = 10
    USE_MOCK_OTP: bool = True

    # File Storage
    UPLOAD_DIR: str = "./uploads"

    # App
    APP_NAME: str = "Healthcare Memory System"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
