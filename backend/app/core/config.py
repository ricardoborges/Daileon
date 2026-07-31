import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Daileon API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./daileon.db"

    # GitLab API Configuration
    GITLAB_URL: str = os.getenv("GITLAB_URL", "https://gitlab.com")
    GITLAB_READ_TOKEN: str = os.getenv("GITLAB_READ_TOKEN", os.getenv("GITLAB_TOKEN", ""))
    GITLAB_GROUP_ID: str = os.getenv("GITLAB_GROUP_ID", "")
    SYNC_INTERVAL_MINUTES: int = 30

    class Config:
        case_sensitive = True

settings = Settings()
