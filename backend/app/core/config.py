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

    # Jenkins API Configuration
    JENKINS_URL: str = os.getenv("JENKINS_URL", "https://jenkins.example.com")
    JENKINS_USER: str = os.getenv("JENKINS_USER", "")
    JENKINS_API_TOKEN: str = os.getenv("JENKINS_API_TOKEN", "")
    # Break-Glass Admin Configuration
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    SECRET_KEY: str = "daileon-breakglass-secret-key-change-in-prod"

    # LDAP Configuration
    LDAP_ENABLED: bool = False
    LDAP_SERVER_HOST: str = ""
    LDAP_SERVER_PORT: int = 389
    LDAP_USE_SSL: bool = False
    LDAP_BIND_DN: str = ""
    LDAP_BIND_PASSWORD: str = ""
    LDAP_BASE_DN: str = ""
    LDAP_USER_ATTRIBUTE: str = "uid"

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()

