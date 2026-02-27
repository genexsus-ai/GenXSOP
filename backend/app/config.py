from pydantic_settings import BaseSettings
from typing import List
from pydantic import model_validator


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./genxsop.db"
    ENVIRONMENT: str = "development"
    AUTO_CREATE_TABLES: bool = True
    SECRET_KEY: str = "genxsop-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    DEBUG: bool = True
    APP_NAME: str = "GenXSOP"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    ENABLE_REQUEST_ID: bool = True
    ENABLE_REQUEST_LOGGING: bool = True
    ENABLE_SECURITY_HEADERS: bool = True
    STRICT_TRANSPORT_SECURITY_SECONDS: int = 31536000
    READINESS_CHECK_DATABASE: bool = True
    FORECAST_JOB_RETENTION_DAYS: int = 30
    OPENAI_API_KEY: str = ""
    GENXAI_LLM_MODEL: str = "gpt-4o-mini"
    GENXAI_LLM_TEMPERATURE: float = 0.2
    GENXAI_MAX_EXECUTION_TIME_SECONDS: float = 20.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"prod", "production"}

    @model_validator(mode="after")
    def validate_production_safety(self):
        if not self.is_production:
            return self

        if "sqlite" in self.DATABASE_URL.lower():
            raise ValueError("SQLite is not allowed when ENVIRONMENT is production.")

        if self.SECRET_KEY == "genxsop-super-secret-key-change-in-production":
            raise ValueError("Default SECRET_KEY is not allowed in production.")

        if self.AUTO_CREATE_TABLES:
            raise ValueError("AUTO_CREATE_TABLES must be false in production; use Alembic migrations.")

        return self


settings = Settings()
