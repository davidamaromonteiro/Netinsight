"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "NetInsight API"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # MongoDB
    MONGODB_URL: str = "mongodb://mongodb:27017"
    MONGODB_DB_NAME: str = "netinsight"

    # Redis (for Celery)
    REDIS_URL: str = "redis://redis:6379/0"

    # NVD API
    NVD_API_KEY: str = ""
    NVD_API_BASE_URL: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    # MITRE ATT&CK
    MITRE_ENTERPRISE_URL: str = (
        "https://raw.githubusercontent.com/mitre-attack/"
        "attack-stix-data/master/enterprise-attack/enterprise-attack.json"
    )

    # Scan defaults
    SCAN_RATE_LIMIT: int = 100  # packets per second
    SCAN_TIMEOUT_SECONDS: int = 300

    # Auth test defaults
    AUTH_TEST_MAX_ATTEMPTS: int = 5
    AUTH_TEST_DELAY_SECONDS: float = 1.0

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:80"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
