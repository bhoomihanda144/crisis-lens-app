"""
CrisisLens Configuration Management
Loads environment variables from .env using Pydantic Settings
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Supabase Credentials
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_SERVICE_ROLE_KEY: str = "your_supabase_service_role_key"

    # AI Engine URL (Member 3)
    AI_ENGINE_URL: str = "http://127.0.0.1:8001"

    # Application Settings
    APP_ENV: str = "development"
    API_PORT: int = 8000
    API_HOST: str = "127.0.0.1"

    # Allowed CORS Origins matching API Contract v1.0
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
