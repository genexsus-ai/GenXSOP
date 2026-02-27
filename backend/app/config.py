from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./genxsop.db"
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

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
